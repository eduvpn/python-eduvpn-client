import unittest
from unittest.mock import patch
import urllib.parse
import os
import re
import requests
from eduvpn.server import CustomServer
from .utils import (
    remove_existing_config, create_test_app,
    skip_if_network_manager_not_supported,
)
from .state_utils import StateTestCaseMixin


TEST_SERVER_ENV_VAR = 'TEST_SERVER'


def replace_url_path(url, path):
    parsed = urllib.parse.urlparse(url)
    parsed = parsed._replace(path=path, query=None)
    return urllib.parse.urlunparse(parsed)


def get_form_action(html):
    action_match = re.search(r'<form ([^>/]* )?action="(?P<action>[^"]+)"', html)
    if action_match is None:
        return action_match
    else:
        return action_match.group('action')


class ConnectTests(StateTestCaseMixin, unittest.TestCase):
    @skip_if_network_manager_not_supported
    @unittest.skipUnless(
        TEST_SERVER_ENV_VAR in os.environ,
        f"No test server given in environment variable {TEST_SERVER_ENV_VAR}",
    )
    def test_connect(self):
        from eduvpn.interface import state as interface_state
        from eduvpn import network as network_state

        if not os.environ[TEST_SERVER_ENV_VAR]:
            self.fail(f'empty value for {TEST_SERVER_ENV_VAR}')
        test_server = re.match(
            r'(?P<username>.+):(?P<password>.+)@(?P<address>.+)',
            os.environ[TEST_SERVER_ENV_VAR])
        if not test_server:
            self.fail(f'invalid value for {TEST_SERVER_ENV_VAR}')

        remove_existing_config()
        with create_test_app() as app:
            self.assertReachesInterfaceState(app, interface_state.ConfigurePredefinedServer)
            self.assertIsNone(app.interface_state.results)
            self.assertReachesNetworkState(app, network_state.UnconnectedState)

            # enter the server address
            app.interface_transition('enter_custom_address', test_server['address'])
            self.assertReachesInterfaceState(app, interface_state.ConfigureCustomServer)
            self.assertEqual(app.interface_state.address, test_server['address'])

            # perform the oauth login
            server = CustomServer(test_server['address'])
            with patch('webbrowser.open') as webbrowser_open:
                app.interface_transition('connect_to_server', server)
                self.assertReachesInterfaceState(app, interface_state.OAuthSetup)
                webbrowser_open.assert_called_once()
                url = webbrowser_open.call_args[0][0]

            # get the login form so we know where to post the data
            session = requests.Session()
            response = session.get(url)
            self.assertIn('<h1>Sign In</h1>', response.text)
            self.assertIn('name="userName"', response.text)
            self.assertIn('name="userPass"', response.text)
            self.assertIn('name="_form_auth_redirect_to"', response.text)
            action = get_form_action(response.text)
            self.assertIsNotNone(action)
            self.assertTrue(action.startswith('/'))
            auth_url = replace_url_path(response.url, action)

            # post the login credentials
            response = session.post(auth_url, data=dict(
                userName=test_server['username'],
                userPass=test_server['password'],
                _form_auth_redirect_to=url,
            ))
            if 'The credentials you provided were not correct.' in response.text:
                self.fail("invalid credentials for test server")
            self.assertIn('<h1>Approve Application</h1>', response.text)

            # post the approval for the eduvpn app
            response = session.post(response.url, data=dict(approve='yes'))
            self.assertIn('You can now close this window', response.text)

            # now wait for the connection to be established
            self.assertReachesInterfaceState(app, interface_state.ConnectionStatus)
            self.assertReachesNetworkState(app, network_state.ConnectedState)

            app.network_transition('disconnect')
            self.assertReachesNetworkState(app, network_state.DisconnectedState)
