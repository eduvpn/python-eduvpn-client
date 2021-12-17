from unittest import TestCase, skip
from unittest.mock import patch
from .utils import (
    remove_existing_config, create_test_app,
    skip_if_network_manager_not_supported,
)
from .state_utils import StateTestCaseMixin


PROFILE_NAME_1 = 'Test Profile A'
PROFILE_NAME_2 = 'Test Profile B'


class TestOAuthSession:
    def refresh_token(self, token_url):
        pass

    def get(self, url):
        return TestOAuthResponse()


class TestOAuthResponse:
    status_code = 200

    def json(self):
        return dict(
            profile_list={'data': [
                dict(
                    profile_id='t1',
                    display_name=PROFILE_NAME_1,
                    two_factor=False,
                ),
                dict(
                    profile_id='t2',
                    display_name=PROFILE_NAME_2,
                    two_factor=False,
                ),
            ]},
        )


class FlowTests(StateTestCaseMixin, TestCase):
    @skip("disabled until someone mocks the network calls")
    @skip_if_network_manager_not_supported
    def test_first_start(self):
        from eduvpn.interface import state as interface_state
        from eduvpn import network as network_state

        remove_existing_config()
        with create_test_app() as app:
            self.assertReachesInterfaceState(app, interface_state.ConfigurePredefinedServer)
            self.assertIsNone(app.interface_state.results)
            self.assertReachesNetworkState(app, network_state.UnconnectedState)

            # search for a server called 'demo'
            app.interface_transition('enter_search_query', 'demo')
            self.assertReachesInterfaceState(app, interface_state.ConfigurePredefinedServer)
            self.assertEqual(
                list(map(str, app.interface_state.results)),
                ['Demo'],
            )
            server = app.interface_state.results[0]

            # perform the oauth login
            with patch('eduvpn.oauth2.run_challenge_in_background') as oauth_func:
                with patch('webbrowser.open') as webbrowser_open:
                    url = 'test-url'
                    webserver = object()
                    callback = None

                    def oauth_challenge(token_endpoint, auth_endpoint, app_variant, cb):
                        nonlocal callback
                        callback = cb
                        return webserver, url

                    oauth_func.side_effect = oauth_challenge
                    app.interface_transition('connect_to_server', server)
                    self.assertReachesInterfaceState(app, interface_state.OAuthSetup)
                    self.assertIs(app.interface_state.oauth_web_server, webserver)
                    webbrowser_open.assert_called_once_with(url)

            self.assertIsNotNone(callback)
            oauth_session = TestOAuthSession()
            callback(oauth_session)
            self.assertReachesInterfaceState(app, interface_state.ChooseProfile)

            self.assertEqual(
                list(map(str, app.interface_state.profiles)),
                [PROFILE_NAME_1, PROFILE_NAME_2],
            )
