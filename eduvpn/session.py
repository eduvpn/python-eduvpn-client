from datetime import datetime, timedelta
from . import settings


class Validity:
    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end

    @property
    def duration(self):
        return self.end - self.start

    def fraction(self, fraction: float) -> datetime:
        return self.start + self.duration * fraction


def pending_expiry_time(validity: Validity) -> datetime:
    """
    Determine the moment when the user should be notified
    of the sessions expiry.
    """
    return max(
        validity.fraction(settings.SESSION_PENDING_EXPIRY_FRACTION),
        validity.end - timedelta(minutes=settings.SESSION_PENDING_EXPIRY_MINUTES)
    )
