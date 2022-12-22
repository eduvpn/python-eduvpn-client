import os

from unittest import TestCase
from unittest.mock import patch, PropertyMock
from eduvpn.nm import NMManager
from eduvpn.variants import EDUVPN

from eduvpn.ui import stats
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TextIO


MOCK_IFACE = "mock"


def write_temp_stats_file(filepath: Path, total_bytes: int):
    f = open(filepath, "w")
    f.write(str(total_bytes))
    f.close()


def try_open(path: Path):
    if not path.is_file():
        return None
    return open(path, "r")


@patch("eduvpn.nm.NMManager.iface", new_callable=PropertyMock, return_value=MOCK_IFACE)
class TestStats(TestCase):
    def test_stat_bytes(self, _):
        nm_manager = NMManager(EDUVPN)
        with TemporaryDirectory() as tempdir:
            # Create test data in the wanted files
            # Use the tempdir so it is cleaned up later
            values = [0, 37, 6166746255814, -43]
            # For the expected values we want the human readable string
            # The last two are special
            #   - 0 B because the value has decreased
            #   - default text because the file does not exist
            expected_values = ["0 B", "37 B", "5.61 TB", "0 B"]

            # Create the statistics path
            stat_path = Path(tempdir) / MOCK_IFACE / "statistics"
            os.makedirs(stat_path)

            # Create the download and upload files
            download_file = stat_path / "rx_bytes"
            write_temp_stats_file(download_file, "0")
            download_filehandler = try_open(download_file)

            upload_file = stat_path / "tx_bytes"
            write_temp_stats_file(upload_file, "0")
            upload_filehandler = try_open(upload_file)

            def check_expected(_property: str, _file: TextIO):
                # Create the class instance
                class_ = stats.NetworkStats(nm_manager)

                # Loop over the files,
                # patch it and check if the expected value holds
                class_ = stats.NetworkStats(nm_manager)
                for i, expected in enumerate(expected_values):
                    write_temp_stats_file(Path(_file.name), values[i])
                    self.assertEqual(getattr(class_, _property), expected)
                _file.close()

            # Mock the files and check the expected values
            with patch(
                "eduvpn.ui.stats.NetworkStats.upload_file",
                new_callable=PropertyMock,
                return_value=upload_filehandler,
            ):
                check_expected("upload", upload_filehandler)
            with patch(
                "eduvpn.ui.stats.NetworkStats.download_file",
                new_callable=PropertyMock,
                return_value=download_filehandler,
            ):
                check_expected("download", download_filehandler)
