from datetime import datetime


class Validity:
    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end

    @property
    def duration(self):
        return self.end - self.start

    def fraction(self, fraction: float) -> datetime:
        return self.start + self.duration * fraction
