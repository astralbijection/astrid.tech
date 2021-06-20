from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import pytz
from django.contrib.auth.decorators import login_required
from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from oauth2_provider.models import Application
from oauth2_provider.views import AuthorizationView
from rest_framework.status import *
from structlog import get_logger

from .models import ConsentRequest, ClientSite

logger = get_logger(__name__)


# http://127.0.0.1:8001/o/authorize?me=https://astrid.tech/&client_id=https://webapp.example.org/&redirect_uri=https://webapp.example.org/auth/callback&state=1234567890&response_type=code
class IndieAuthView(AuthorizationView):
    def setup_indieauth(self, client_id, redirect_uri):
        """
        Set up the IndieAuth application with the given parameters, or does nothing if it is given an
        invalid combination of parameters.

        :return if they are valid parameters
        """
        # defer to AuthorizationView handler
        if redirect_uri is None or client_id is None:
            return False

        # ensure redirect URI is on the same domain
        if urlparse(client_id).netloc != urlparse(redirect_uri).netloc:
            # TODO check whitelist
            return False

        logger.debug('Ensuring IndieAuth app exists', client_id=client_id)

        with transaction.atomic():
            # Create the app if it doesn't exist and populate fields
            try:
                app = Application.objects.get(client_id=client_id)
            except Application.DoesNotExist:
                app = Application.objects.create(client_id=client_id)
            app.name = f'IndieAuth for {client_id}'
            app.authorization_grant_type = Application.GRANT_AUTHORIZATION_CODE

            # Whitelist this redirect URI if it's not on the list
            if redirect_uri not in app.redirect_uris:
                app.redirect_uris += redirect_uri

            app.save()

            # Create the site if it doesn't exist and populate fields
            try:
                site = ClientSite.objects.get(client_id=client_id)
            except ClientSite.DoesNotExist:
                site = ClientSite.objects.create(client_id=client_id, application=app)

        return True

    def get(self, request, *args, **kwargs):
        client_id = request.GET.get('client_id')
        redirect_uri = request.GET.get('redirect_uri')
        me = request.GET.get('me')
        if me is not None:
            self.setup_indieauth(client_id, redirect_uri)
        return super().get(request, *args, **kwargs)


@login_required
def _ask_for_consent(request):
    me = request.GET.get('me')
    client_id = request.GET.get('client_id')
    redirect_uri = request.GET.get('redirect_uri')
    state = request.GET.get('state')
    response_type = request.GET.get('response_type', 'id')
    scope = request.GET.get('scope', '')

    logger_ = logger.bind(me=me, client_id=client_id, redirect_uri=redirect_uri, state=state,
                          response_type=response_type)

    if me not in ['https://astrid.tech', 'https://astrid.tech/']:
        logger_.warn('Unsupported me param')
        return HttpResponse(f'cannot authorize {me}', status=HTTP_400_BAD_REQUEST)

    # required fields
    for field in [client_id, redirect_uri, state]:
        if field is None:
            return HttpResponse('missing fields from query', status=HTTP_400_BAD_REQUEST)

    if response_type == 'id':
        pass

    ConsentRequest.objects.filter(client_id=client_id).delete()

    perm_rq = ConsentRequest.objects.create(
        client_id=client_id,
        me=me,
        state=state,
        response_type=response_type,
        redirect_uri=redirect_uri,
        scope=scope,
        expires_at=datetime.now(pytz.utc) + timedelta(minutes=5),
        confirmed=False
    )
    logger_.info('Rendering form', perm_rq=perm_rq)

    return render(request, 'indieauth/authorize.html', {
        'perm_rq': perm_rq
    })


def _authorize_indieauth(request):
    redirect_uri = request.POST.get('redirect_uri')
    code = request.POST.get('code')
    client_id = request.POST.get('client_id')
    try:
        obj = ConsentRequest.objects.get(client_id=client_id, redirect_uri=redirect_uri, auth_code=code)
    except ConsentRequest.DoesNotExist:
        return HttpResponse('request expired', status=HTTP_401_UNAUTHORIZED)

    if obj.has_expired:
        obj.delete()
        return HttpResponse('request expired', status=HTTP_401_UNAUTHORIZED)

    # TODO create authorization

    obj.delete()

    response = {'me': obj.me}
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse(response, status=HTTP_200_OK)
    else:
        return HttpResponse(urlencode(response), status=HTTP_200_OK)


@require_http_methods(['GET', 'POST'])
def auth_consent(request):
    if request.method == 'GET':
        return _ask_for_consent(request)

    if request.method == 'POST':
        return _authorize_indieauth(request)


@login_required
@require_http_methods(['POST'])
@transaction.atomic
def auth_confirm(request):
    pk = request.POST.get('request_id')
    obj = ConsentRequest.objects.get(pk=pk)
    logger_ = logger.bind(request=obj)

    if obj.expires_at <= datetime.now(pytz.utc):
        obj.delete()
        return HttpResponse('request expired', status=HTTP_401_UNAUTHORIZED)

    obj.confirm()
    obj.save()

    params = {'code': obj.auth_code, 'state': obj.state}
    logger_.info('Adding params to redirect', params=params, redirect_uri=obj.redirect_uri)

    # https://stackoverflow.com/a/2506477 to add state to a query
    parts = urlparse(obj.redirect_uri)
    query = dict(parse_qsl(parts.query))
    query.update(params)
    # noinspection PyProtectedMember
    parts = parts._replace(query=urlencode(query))
    redirect_to = urlunparse(parts)

    return redirect(redirect_to)
