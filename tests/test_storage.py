from unittest import TestCase
from datetime import datetime, timezone
from eduvpn.storage import serialize_datetime, deserialize_datetime


utc = timezone.utc


class DateTimeSerializationTests(TestCase):
    def test_serialize_datetime(self):
        self.assertEqual(
            serialize_datetime(datetime(2022, 1, 3, 13, 46, 29, 0, utc)),
            '2022-01-03T13:46:29+00:00',
        )

    def test_deserialize_datetime(self):
        self.assertEqual(
            deserialize_datetime('2022-01-03T13:46:29'),
            datetime(2022, 1, 3, 13, 46, 29, 0, utc),
        )
        self.assertEqual(
            deserialize_datetime('2022-01-03T13:46:29.123456'),
            datetime(2022, 1, 3, 13, 46, 29, 123456, utc),
        )

        self.assertEqual(
            deserialize_datetime('2022-01-03T13:46:29+00:00'),
            datetime(2022, 1, 3, 13, 46, 29, 0, utc),
        )
        self.assertEqual(
            deserialize_datetime('2022-01-03T13:46:29-00:00'),
            datetime(2022, 1, 3, 13, 46, 29, 0, utc),
        )

    def test_serialize_roundtrip(self):
        dt = datetime.now(timezone.utc)
        self.assertEqual(
            deserialize_datetime(serialize_datetime(dt)),
            dt,
        )
