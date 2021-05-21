import webbrowser
from typing import Optional, Callable, Tuple
from requests_oauthlib import OAuth2Session
from ..settings import CLIENT_ID, SCOPE, CODE_CHALLENGE_METHOD
from ..variants import ApplicationVariant
from ..crypto import gen_code_verifier, gen_code_challenge
from .http import OAuthWebServer


class OAuthChallenge:
    def __init__(self, session: OAuth2Session, token_endpoint: str, verifier: str, url: str, state: str):
        self.session = session
        self.token_endpoint = token_endpoint
        self.verifier = verifier
        self.url = url
        self.state = state


def create_challenge(
    redirect_uri: str,
    token_endpoint: str,
    authorization_endpoint: str,
) -> OAuthChallenge:
    session = OAuth2Session(
        CLIENT_ID,
        redirect_uri=redirect_uri,
        auto_refresh_url=token_endpoint,
        scope=SCOPE,
    )
    code_verifier = gen_code_verifier()
    code_challenge = gen_code_challenge(code_verifier)
    authorization_url, state = session.authorization_url(
        url=authorization_endpoint,
        code_challenge_method=CODE_CHALLENGE_METHOD,
        code_challenge=code_challenge,
    )
    return OAuthChallenge(session, token_endpoint, code_verifier, authorization_url, state)


def setup_challenge(
    token_endpoint: str,
    authorization_endpoint: str,
    app_variant: ApplicationVariant,
) -> Tuple[OAuthChallenge, OAuthWebServer]:
    webserver = OAuthWebServer(app_variant)
    challenge = create_challenge(
        webserver.success_url,
        token_endpoint,
        authorization_endpoint,
    )
    return challenge, webserver


def perform_challenge(
    challenge: OAuthChallenge,
    webserver: OAuthWebServer,
) -> Optional[OAuth2Session]:
    data = webserver.run()
    if data is None:
        # The operation was cancelled by the user.
        return None
    fetch_token(challenge, data)
    return challenge.session


def run_challenge(
    token_endpoint: str,
    authorization_endpoint: str,
    app_variant: ApplicationVariant,
) -> Optional[OAuth2Session]:
    challenge, webserver = setup_challenge(
        token_endpoint, authorization_endpoint, app_variant)
    webbrowser.open(challenge.url)
    return perform_challenge(challenge, webserver)


def perform_challenge_in_background(
    challenge: OAuthChallenge,
    webserver: OAuthWebServer,
    callback: Callable[[Optional[OAuth2Session]], None],
):
    def complete_callback(data: dict):
        if data is None:
            # The operation was cancelled by the user.
            callback(None)
        else:
            fetch_token(challenge, data)
            callback(challenge.session)

    webserver.run_in_background(complete_callback)


def run_challenge_in_background(
    token_endpoint: str,
    authorization_endpoint: str,
    app_variant: ApplicationVariant,
    callback: Callable[[Optional[OAuth2Session]], None],
):
    challenge, webserver = setup_challenge(
        token_endpoint, authorization_endpoint, app_variant)
    perform_challenge_in_background(challenge, webserver, callback)
    return webserver, challenge.url


def fetch_token(challenge: OAuthChallenge, response: dict):
    assert challenge.state == response['state'][0]
    challenge.session.fetch_token(
        token_url=challenge.token_endpoint,
        code=response['code'][0],
        code_verifier=challenge.verifier,
        client_id=challenge.session.client_id,
        include_client_id=True,
    )
