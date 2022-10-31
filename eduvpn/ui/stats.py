import functools
import logging
from pathlib import Path
from typing import Optional, TextIO

from eduvpn.utils import get_human_readable_bytes, translated_property

logger = logging.getLogger(__name__)

LINUX_NET_FOLDER = Path("/sys/class/net")


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
    def upload_file(self) -> Optional[TextIO]:
        return self.open_file("tx_bytes")

    @cached_stats_property
    def download_file(self) -> Optional[TextIO]:
        return self.open_file("rx_bytes")

    @cached_stats_property
    def start_bytes_upload(self) -> Optional[int]:
        return self.get_file_bytes(self.upload_file)  # type: ignore

    @cached_stats_property
    def start_bytes_download(self) -> Optional[int]:
        return self.get_file_bytes(self.download_file)  # type: ignore

    @cached_stats_property
    def iface(self) -> Optional[str]:
        return self.manager.iface

    @property
    def download(self) -> str:
        """
        Get the download as a human readable string
        """
        file_bytes_download = self.get_file_bytes(self.download_file)  # type: ignore
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
        file_bytes_upload = self.get_file_bytes(self.upload_file)  # type: ignore
        if file_bytes_upload is None:
            return self.default_text
        if file_bytes_upload <= self.start_bytes_upload:  # type: ignore
            return get_human_readable_bytes(0)
        return get_human_readable_bytes(
            file_bytes_upload - self.start_bytes_upload
        )  # type:ignore

    def open_file(self, filename: str) -> Optional[TextIO]:
        """
        Helper function to open a statistics network file
        """
        if not self.iface:
            logger.warning(f"Network Stats: {filename}, failed to get interface")
            return None
        filepath = LINUX_NET_FOLDER / self.iface / "statistics" / filename  # type: ignore
        if not filepath.is_file():
            logger.warning(f"Network Stats: {filepath} is not a file")
            return None
        return open(filepath, "r")

    def get_file_bytes(self, filehandler: Optional[TextIO]) -> Optional[int]:
        """
        Helper function to get a statistics file to calculate the total data transfer
        """
        # If the interface is not set
        # or the file is not present, we cannot get the stat
        if not self.iface:
            # Warning was already shown
            return None
        if not filehandler:
            # Warning was already shown
            return None

        # Get the statistic from the file
        # and go to the beginning
        try:
            stat = int(filehandler.readline())
        except ValueError:
            stat = 0
        filehandler.seek(0)
        return stat

    def cleanup(self) -> None:
        """
        Cleanup the network stats by closing the files
        """
        if self.download_file:
            self.download_file.close()
        if self.upload_file:
            self.upload_file.close()
