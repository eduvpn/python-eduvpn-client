from unittest import TestCase
from unittest.mock import patch
from time import sleep
from eduvpn.interface import state as interface_state
from eduvpn import network as network_state
from .utils import remove_existing_config, create_test_app
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
                    default_gateway=True,
                ),
                dict(
                    profile_id='t2',
                    display_name=PROFILE_NAME_2,
                    two_factor=False,
                    default_gateway=True,
                ),
            ]},
        )


class FlowTests(StateTestCaseMixin, TestCase):
    def test_first_start(self):
        remove_existing_config()
        app = create_test_app()
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
        with patch('eduvpn.oauth2.get_oauth_at_port') as oauth_func:
            oauth_session = TestOAuthSession()

            def oauth_login(*args, **kwargs):
                sleep(.01)
                return oauth_session

            oauth_func.side_effect = oauth_login
            app.interface_transition('connect_to_server', server)
            self.assertReachesInterfaceState(app, interface_state.ChooseProfile)

        self.assertEqual(
            list(map(str, app.interface_state.profiles)),
            [PROFILE_NAME_1, PROFILE_NAME_2],
        )
