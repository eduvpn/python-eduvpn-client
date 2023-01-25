import functools
import logging
from typing import Optional, TextIO

from eduvpn.utils import get_human_readable_bytes, translated_property

logger = logging.getLogger(__name__)


def cached_stats_property(f):
    @functools.wraps(f)
    def wrapped(self):
        try:
            property_name = f"_{f.__name__}"
            # check for _value
            value = getattr(self, property_name)

            # value is not valid, recompute
            if value is None or value is self.default_text:
                value = f(self)
        # value does not exists, recompute
        except Exception:
            value = f(self)
        setattr(self, property_name, value)
        return value

    return property(wrapped)


class NetworkStats:
    def __init__(self, manager):
        self.manager = manager

    default_text = translated_property("N/A")

    # These properties define an LRU cache
    # This cache is used so that we do not query these every second
    @cached_stats_property
    def ipv4(self) -> str:
        _ipv4 = self.manager.ipv4
        if _ipv4 is None:
            _ipv4 = self.default_text
        return _ipv4

    @cached_stats_property
    def ipv6(self) -> str:
        _ipv6 = self.manager.ipv6
        if _ipv6 is None:
            _ipv6 = self.default_text
        return _ipv6

    @cached_stats_property
    def protocol(self) -> str:
        _protocol = self.manager.protocol
        if _protocol is None:
            _protocol = self.default_text
        return _protocol

    @cached_stats_property
    def upload_file(self) -> Optional[TextIO]:
        return self.manager.open_stats_file("tx_bytes")

    @cached_stats_property
    def download_file(self) -> Optional[TextIO]:
        return self.manager.open_stats_file("rx_bytes")

    @cached_stats_property
    def start_bytes_upload(self) -> Optional[int]:
        return self.manager.get_stats_bytes(self.upload_file)  # type: ignore

    @cached_stats_property
    def start_bytes_download(self) -> Optional[int]:
        return self.manager.get_stats_bytes(self.download_file)  # type: ignore

    @property
    def download(self) -> str:
        """
        Get the download as a human readable string
        """
        file_bytes_download = self.manager.get_stats_bytes(self.download_file)  # type: ignore
        if file_bytes_download is None:
            return self.default_text
        if file_bytes_download <= self.start_bytes_download:  # type: ignore
            return get_human_readable_bytes(0)
        return get_human_readable_bytes(file_bytes_download - self.start_bytes_download)  # type: ignore

    @property
    def upload(self) -> str:
        """
        Get the upload as a human readable string
        """
        file_bytes_upload = self.manager.get_stats_bytes(self.upload_file)  # type: ignore
        if file_bytes_upload is None:
            return self.default_text
        if file_bytes_upload <= self.start_bytes_upload:  # type: ignore
            return get_human_readable_bytes(0)
        return get_human_readable_bytes(
            file_bytes_upload - self.start_bytes_upload
        )  # type:ignore

    def cleanup(self) -> None:
        """
        Cleanup the network stats by closing the files
        """
        if self.download_file:
            self.download_file.close()
        if self.upload_file:
            self.upload_file.close()
