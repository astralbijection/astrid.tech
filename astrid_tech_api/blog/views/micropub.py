import json
from datetime import datetime
from typing import Iterable, Union, Dict, List
from urllib.parse import urlunparse

import pytz
from django.contrib.auth import get_user_model
from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.http import HttpResponse, JsonResponse, QueryDict
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from oauth2_provider.models import AccessToken
from rest_framework.status import *
from result import Ok, Err, Result
from structlog import get_logger

from blog.models import SyndicationTarget, Entry, Syndication, Tag, UploadedFile, Attachment

logger = get_logger(__name__)
_EMPTY = ['']


class InvalidMicropubException(Exception):
    pass


def create_syndications(entry: Entry, syndications: Iterable[str]):
    for url in syndications:
        Syndication.objects.create(
            location=url,
            status=Syndication.Status.SYNDICATED,
            entry_id=entry.pk
        )


def create_mp_syndicate_to(entry: Entry, targets: Iterable[str]):
    for uid in targets:
        try:
            target = SyndicationTarget.objects.filter(enabled=True).get(id=uid)
        except SyndicationTarget.DoesNotExist:
            raise InvalidMicropubException(f'invalid syndication target {uid}')

        Syndication.objects.create(
            target=target,
            status=Syndication.Status.SCHEDULED,
            entry_id=entry.pk
        )


def create_categories(entry: Entry, categories: Iterable[str]):
    for category in categories:
        tag, _ = Tag.objects.get_or_create(id=category)
        entry.tags.add(tag)


def create_images(entry: Entry, objs: Iterable[Union[str, Dict[str, str]]]):
    for i, obj in enumerate(objs):
        if isinstance(obj, str):
            url = obj
            caption = None
        else:
            url = obj['value']
            caption = obj.get('alt')

        spoiler = caption is not None and '#spoiler' in caption

        Attachment.objects.create(
            entry=entry,
            index=i,
            url=url,
            caption=caption,
            spoiler=spoiler,
            content_type='photo'
        )


def get_dates(query: Dict):
    published = query.get('published', datetime.now(pytz.utc))
    if isinstance(published, list):
        [published] = published
    if isinstance(published, str):
        published = datetime.fromisoformat(published)

    created = query.get('created', published)
    if isinstance(created, list):
        [created] = created
    if isinstance(created, str):
        created = datetime.fromisoformat(created)
    return published, created


def get_microformat_str(d: Dict[str, List[str]], key):
    objs = d.get(key, [])
    if not isinstance(objs, list):
        raise InvalidMicropubException(f'key {repr(key)} is not a list')

    if len(objs) == 0:
        return None
    if len(objs) != 1:
        raise InvalidMicropubException(f'too many values for key {repr(key)}')
    [v] = objs
    return v



@transaction.atomic
def create_entry_from_query(query: QueryDict):
    published, created = get_dates(query)

    entry = Entry.objects.create(
        title=query.get('name', ''),
        description=query.get('summary', ''),

        created_date=created,
        published_date=published,

        date=created,
        ordinal=Entry.get_next_ordinal(created),

        reply_to=query.get('in-reply-to', ''),
        location=query.get('location', ''),
        repost_of=query.get('repost-of', ''),

        content=query.get('content', ''),
        content_type='text/plain'
    )

    create_syndications(entry, query.getlist('syndication'))
    create_mp_syndicate_to(entry, query.getlist('mp-syndicate-to'))
    create_categories(entry, query.getlist('category'))
    return entry


def parse_mf2_content(content_obj):
    [child] = content_obj
    if isinstance(child, str):  # Plaintext
        return 'text/plain', child
    elif isinstance(child, dict):  # An object, indicating non-plaintext
        [key] = child  # Extract the (hopefully only) key in there
        if key == 'html':
            return 'text/html', child[key]
    raise ValueError(f'Could not parse {repr(content_obj)}')


@transaction.atomic
def create_entry_from_json(properties: dict):
    content_obj = properties.get('content', _EMPTY)
    content_type, content = parse_mf2_content(content_obj)

    published, created = get_dates(properties)

    entry = Entry.objects.create(
        title=get_microformat_str(properties, 'name'),
        description=get_microformat_str(properties, 'summary'),

        created_date=published,
        published_date=created,

        date=created,
        ordinal=Entry.get_next_ordinal(created),

        reply_to=get_microformat_str(properties, 'in-reply-to'),
        location=get_microformat_str(properties, 'location'),
        repost_of=get_microformat_str(properties, 'repost-of'),

        content=content,
        content_type=content_type
    )

    create_syndications(entry, properties.get('syndication', []))
    create_mp_syndicate_to(entry, properties.get('mp-syndicate-to', []))
    create_categories(entry, properties.get('category', []))
    create_images(entry, properties.get('photo', []))
    return entry


JSON = 'application/json'
FORM = ['application/x-www-form-urlencoded', 'multipart/form-data']


def _invalid_request(info):
    """See https://micropub.spec.indieweb.org/#error-response]"""
    return JsonResponse(
        status=400,
        data={
            'error': 'invalid_request',
            'info': info
        }
    )


def _forbidden():
    """See https://micropub.spec.indieweb.org/#error-response"""
    return JsonResponse(
        status=403,
        data={
            'error': 'forbidden'
        }
    )


def _unauthorized():
    """See https://micropub.spec.indieweb.org/#error-response"""
    return JsonResponse(
        status=401,
        data={
            'error': 'unauthorized'
        }
    )


def _syndication_targets():
    targets = SyndicationTarget.objects.filter(enabled=True)
    return {
        'syndicate-to': [
            target.micropub_syndication_target
            for target in targets
        ]
    }


def _created(entry: Entry):
    return HttpResponse(
        status=HTTP_201_CREATED,
        headers={'Location': 'https://astrid.tech' + entry.slug}
    )


def _media_endpoint(host):
    location = urlunparse(('https', host, reverse('micropub-media-endpoint'), None, None, None))
    return {'media-endpoint': location}


def handle_create_json(logger_, request: WSGIRequest):
    data = json.loads(request.body)

    h_type = get_microformat_str(data, 'type')

    logger_.debug('Decoded type', h_type=h_type)

    if h_type == 'h-entry':
        try:
            entry = create_entry_from_json(data.get('properties', {}))
            entry.refresh_from_db()
        except SyndicationTarget.DoesNotExist:
            return _invalid_request('Invalid syndication targets')

        logger_.info('Successfully created entry', entry=entry)

        return _created(entry)

    return _invalid_request(f'unsupported type {h_type}')


def handle_create_form(logger_, request: WSGIRequest):
    h_type = request.POST.get('h')
    if h_type is None:
        return _invalid_request('must specify "h"')

    logger_.debug('Decoded h-type', h_type=h_type)

    if request.POST['h'] == 'entry':
        logger_ = logger.bind(form=dict(request.POST))
        logger_.debug('Validating')

        try:
            entry = create_entry_from_query(request.POST)
            entry.refresh_from_db()
        except SyndicationTarget.DoesNotExist:
            return _invalid_request('Invalid syndication targets')

        logger_.info('Successfully created entry', entry=entry)

        return _created(entry)

    return _invalid_request(f'unsupported h-type {h_type}')


UserModel = get_user_model()


def get_auth_token(request: WSGIRequest) -> Result[AccessToken, HttpResponse]:
    # Find the access token in the different places it might be
    auth_header = request.headers.get('Authorization')
    if auth_header is not None:
        return Ok(auth_header.removeprefix('Bearer '))

    auth_param = request.POST.get('access_token')
    if auth_param is not None:
        return Ok(auth_param)

    return Err(_unauthorized())


def authenticate_request(access_token: str) -> Result[AccessToken, HttpResponse]:
    # Verify that the token exists
    try:
        token = AccessToken.objects.get(token=access_token)
    except AccessToken.DoesNotExist:
        return Err(_forbidden())

    # Verify that the token is still valid
    if token.is_expired():
        return Err(_forbidden())

    return Ok(token)


@require_http_methods(["GET", "POST"])
def micropub(request: WSGIRequest) -> HttpResponse:
    logger_ = logger.bind()

    if request.method == 'GET':
        # See https://micropub.spec.indieweb.org/#querying
        q = request.GET.get('q')
        if q is None:
            return _invalid_request('must specify "q"')

        if q == 'syndicate-to':
            return JsonResponse(_syndication_targets())

        host = request.headers.get('Host')

        if q == 'config':
            return JsonResponse({**_media_endpoint(host), **_syndication_targets()})

        return _invalid_request(f'unsupported q {q}')

    if request.method == 'POST':
        token_result = get_auth_token(request)
        if isinstance(token_result, Err):
            return token_result.value

        auth_result = authenticate_request(token_result.value)
        if isinstance(auth_result, Err):
            return auth_result.value

        access_token = auth_result.value

        logger_ = logger_.bind(form=dict(request.POST))
        action = request.POST.get('action')

        # No "action" supplied means a create action
        if action is None:
            if not access_token.is_valid(['create']):
                return _forbidden()

            try:
                if request.content_type == JSON:
                    return handle_create_json(logger_, request)
                if request.content_type in FORM:
                    return handle_create_form(logger_, request)
            except InvalidMicropubException as e:
                return _invalid_request(e.args)

            return _invalid_request(f'unsupported content-type {request.content_type}')

        return _invalid_request(f'unsupported action {action}')

    raise RuntimeError(f"Got unsupported method {request.method}")


@require_http_methods(['POST'])
def upload_media(request: WSGIRequest) -> HttpResponse:
    file = request.FILES.get('file')
    if file is None:
        return HttpResponse(status=HTTP_400_BAD_REQUEST)
    obj = UploadedFile.objects.create(name=file.name, content_type=file.content_type, file=file)

    host = request.headers.get('Host')
    location = urlunparse(('https', host, obj.file.url, None, None, None))
    return HttpResponse(status=HTTP_201_CREATED, headers={'Location': location})
