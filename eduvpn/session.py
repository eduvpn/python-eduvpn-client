from datetime import datetime, timedelta
from . import settings
from .state_machine import BaseState
from .app import Application
from .server import ConfiguredServer as Server


class Validity:
    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end

    @property
    def duration(self) -> timedelta:
        """
        Return the duration of this validity.
        """
        return self.end - self.start

    def fraction(self, fraction: float) -> datetime:
        return self.start + self.duration * fraction

    @property
    def pending_expiry_time(self) -> datetime:
        """
        Determine the moment when the user should be notified
        of the sessions expiry.
        """
        return max(
            self.fraction(settings.SESSION_PENDING_EXPIRY_FRACTION),
            self.end - timedelta(minutes=settings.SESSION_PENDING_EXPIRY_MINUTES)
        )

    @property
    def is_pending_expiry(self) -> bool:
        """
        Return True if the validity is pending expiry or has already expired.
        """
        return datetime.utcnow() >= self.pending_expiry_time

    @property
    def is_expired(self) -> bool:
        """
        Return True if the validity has expired.
        """
        return datetime.utcnow() >= self.end


class SessionState(BaseState):
    """
    Base class for all session states.
    """

    def new_session(self, app: Application, server: Server, validity: Validity) -> 'SessionState':
        if validity.is_expired:
            return SessionExpiredState(server, validity)
        elif validity.is_pending_expiry:
            return SessionPendingExpiryState(server, validity)
        else:
            return SessionActiveState(server, validity)


class InitialSessionState(SessionState):
    """
    The state of the session when the app starts.

    This is a transient state until
    the actual session state is obtained.
    """

    is_active = False

    def found_active_session(self, app: Application, server: Server, validity: Validity) -> SessionState:
        """
        An already active session was found.
        """
        app.network_transition('found_previous_connection')
        return self.new_session(app, server, validity)

    def no_previous_session_found(self, app: Application) -> SessionState:
        """
        No previously established session was found.
        """
        app.network_transition('no_previous_connection_found')
        return NoSessionState()


class NoSessionState(SessionState):
    """
    No session is currently active.
    """

    is_active = False


class SessionActiveState(SessionState):
    """
    A session is currently active.
    """

    is_active = True

    def __init__(self, server: Server, validity: Validity):
        self.server = server
        self.validity = validity

    def pending_expiry(self, app: Application) -> SessionState:
        return SessionPendingExpiryState(self.server, self.validity)


class SessionPendingExpiryState(SessionState):
    """
    The session is about to expire.
    """

    is_active = True

    def __init__(self, server: Server, validity: Validity):
        self.server = server
        self.validity = validity

    def has_expired(self, app: Application) -> SessionState:
        return SessionExpiredState(self.server, self.validity)

    def renew(self, app: Application) -> SessionState:
        app.interface_transition('renew_session', self.server)
        return self


class SessionExpiredState(SessionState):
    """
    The session has expired.
    """

    is_active = False

    def __init__(self, server: Server, validity: Validity):
        self.server = server
        self.validity = validity

    def renew(self, app: Application) -> SessionState:
        app.interface_transition('renew_session', self.server)
        return self
