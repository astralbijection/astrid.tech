from datetime import datetime, timedelta
from urllib.parse import urlencode

import pytz
from django.contrib.auth import get_user_model
from django.test import TestCase
from freezegun import freeze_time
from oauth2_provider.models import Application

from indieauth.models import ClientSite
from indieauth.util import get_uri_params

working_id_params = dict(
    me='https://astrid.tech/',
    client_id='https://webapp.example.org/',
    redirect_uri='https://webapp.example.org/auth/callback?some=param',
    state='1234567890',
    response_type='code'
)

allow = [
    *{**working_id_params}.items(),
    ('scope', 'create'),
    ('scope', 'update'),
    ('allow', True)
]

working_id_params['scope'] = 'create update'

confirm_time = datetime(2021, 6, 20, 11, 2, 15, tzinfo=pytz.utc)
expired_time = confirm_time + timedelta(minutes=12)

auth_endpoint = '/auth/indieauth'
token_endpoint = '/auth/indieauth/token'


class TestIndieAuthFlow(TestCase):
    """
    Tests functionality following https://indieweb.org/authorization-endpoint#Creating_an_Authorization_Endpoint
    """

    def setUp(self):
        self.disallowed_user = get_user_model().objects.create_user(username='stranger', password='7812')
        self.allowed_user = get_user_model().objects.create_user(username='myself', password='12345')

    def post_allow_form(self):
        return self.client.post(auth_endpoint, urlencode(allow),
                                content_type='application/x-www-form-urlencoded')

    def post_oauth_consent(self, code):
        return self.client.post(token_endpoint, urlencode({
            'code': code,
            'grant_type': 'authorization_code',
            'client_id': working_id_params['client_id'],
            'redirect_uri': working_id_params['redirect_uri'],
            'me': working_id_params['me']
        }), content_type='application/x-www-form-urlencoded')

    def setup_allowed_user_logged_in(self):
        self.client.force_login(self.allowed_user)

    @freeze_time(confirm_time)
    def setup_confirmed_application_and_logout(self):
        self.setup_allowed_user_logged_in()
        self.client.get(auth_endpoint, working_id_params)
        response = self.post_allow_form()
        qs = get_uri_params(response.headers['Location'])
        return qs['code']

    @freeze_time(confirm_time)
    def setup_confirmed_application_and_logout(self):
        self.setup_allowed_user_logged_in()
        self.client.get(auth_endpoint, working_id_params)
        response = self.post_allow_form()
        qs = get_uri_params(response.headers['Location'])
        return qs['code']

    def authorize_with_code(self, code, accept='application/json'):
        response = self.client.post(
            auth_endpoint,
            {
                'code': code,
                'redirect_uri': working_id_params['redirect_uri'],
                'client_id': working_id_params['client_id']
            },
            HTTP_ACCEPT=accept
        )
        return response

    @freeze_time(confirm_time)
    def test_anonymous_get_endpoint_is_redirected(self):
        self.client.logout()

        response = self.client.get(auth_endpoint, working_id_params)

        self.assertEqual(302, response.status_code, msg=response.content)

    @freeze_time(confirm_time)
    def test_get_endpoint_creates_application(self):
        self.setup_allowed_user_logged_in()

        response = self.client.get(auth_endpoint, working_id_params)

        self.assertEqual(200, response.status_code, msg=response.content)
        app = Application.objects.get(client_id=working_id_params['client_id'])
        site = ClientSite.objects.get(client_id=working_id_params['client_id'])
        self.assertEqual(app, site.application)

    @freeze_time(confirm_time)
    def test_post_confirms_consent_request(self):
        self.setup_allowed_user_logged_in()
        self.client.get(auth_endpoint, working_id_params)

        response = self.post_allow_form()

        self.assertEqual(302, response.status_code, msg=response.content)
        qs = get_uri_params(response.headers['Location'])
        self.assertEqual('param', qs['some'])
        self.assertEqual(working_id_params['state'], qs['state'])
        self.assertIn('code', qs)

    @freeze_time(confirm_time)
    def test_post_to_token_retrieves_token(self):
        code = self.setup_confirmed_application_and_logout()

        response = self.post_oauth_consent(code)

        self.assertEqual(200, response.status_code, msg=response.content)
        data = response.json()
        self.assertIn('access_token', data)
        self.assertEqual('https://astrid.tech/', data['me'])

    @freeze_time(confirm_time)
    def test_post_to_authorization_retrieves_profile(self):
        code = self.setup_confirmed_application_and_logout()

        response = self.client.post(auth_endpoint, urlencode({
            'code': code,
            'grant_type': 'authorization_code',
            'client_id': working_id_params['client_id'],
            'redirect_uri': working_id_params['redirect_uri']
        }), content_type='application/x-www-form-urlencoded')

        self.assertEqual(200, response.status_code, msg=response.content)
        data = response.json()
        self.assertEqual('https://astrid.tech/', data['me'])
