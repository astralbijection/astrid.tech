from collections import namedtuple

import httplib2
from django.http import HttpRequest
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ParseError
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.google import get_authorization_url, get_authorization_session, get_secrets
from accounts.models import GoogleIdentity, GoogleToken, GoogleAuthAttempt
from accounts.models.serializers import CreateUserForm

PrefillUserData = namedtuple('PrefillUserData', 'name email')
http = httplib2.Http(cache=".cache")


@api_view()
@permission_classes([AllowAny])
def google_link(request: Request):
    attempt = GoogleAuthAttempt.objects.filter(state=request.query_params['state'])
    if not attempt.exists():
        raise ParseError(
            detail="Invalid state"
        )
    attempt.delete()

    session = get_authorization_session()
    token = session.fetch_token(
        "https://www.googleapis.com/oauth2/v4/token",
        client_secret=get_secrets()['web']['client_secret'],
        code=request.query_params['code']
    )
    google_token = GoogleToken.from_token(token)
    google_token.save()
    profile, identity = GoogleIdentity.create(google_token)
    identity.save()

    return Response({
        'name': profile['name'],
        'email': identity.email,
        'integration': {
            'type': 'google',
            'id': identity.google_id
        }
    })


def google_redirect_authorize(request: HttpRequest):
    url, state = get_authorization_url()
    GoogleAuthAttempt(state=state).save()
    return redirect(url)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_account_from_integration(request: Request):
    form = CreateUserForm(data=request.data)
    if form.is_valid():
        return Response(form.save())
