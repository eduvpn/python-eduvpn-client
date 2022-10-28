from unittest import TestCase
from unittest.mock import patch
from eduvpn.nm import NMManager
from eduvpn.variants import EDUVPN

from eduvpn.ui import stats
from pathlib import Path
from tempfile import TemporaryDirectory


MOCK_IFACE = "mock"


def write_temp_stats_file(directory: Path, filename: str, total_bytes: int):
    f = open(directory / filename, "w")
    f.write(str(total_bytes))
    f.close()


def try_open(path: Path):
    if not path.is_file():
        return None
    return open(path, "r")


class TestStats(TestCase):
    @patch("eduvpn.ui.stats.NetworkStats.iface", MOCK_IFACE)
    def test_download(self):
        nm_manager = NMManager(EDUVPN)
        with TemporaryDirectory() as tempdir:
            # Create test data in the wanted files
            # Use the tempdir so it is cleaned up later
            values = [0, 37, 6166746255814, -43]
            filenames = [
                "rx_bytes",
                "rx_bytes_increased",
                "rx_bytes_increased_big",
                "rx_bytes_decreased",
            ]
            for index, value in enumerate(values):
                write_temp_stats_file(Path(tempdir), filenames[index], value)

            # Create the class instance
            class_ = stats.NetworkStats(nm_manager)

            # Add a file that does not exist
            filenames += ["idonotexist"]

            # For the expected values we want the human readable string
            # The last two are special
            #   - 0 B because the value has decreased
            #   - default text because the file does not exist
            expected_values = ["0 B", "37 B", "5.61 TB", "0 B", class_.default_text]

            # Loop over the files,
            # patch it and check if the expected value holds
            class_ = stats.NetworkStats(nm_manager)
            for index, filename in enumerate(filenames):
                location = Path(tempdir) / filename
                file_ = try_open(location)
                with patch("eduvpn.ui.stats.NetworkStats.download_file", file_):
                    self.assertEqual(class_.download, expected_values[index])
                    class_.cleanup()

    @patch("eduvpn.ui.stats.NetworkStats.iface", MOCK_IFACE)
    def test_upload(self):
        nm_manager = NMManager(EDUVPN)
        with TemporaryDirectory() as tempdir:
            # Create test data in the wanted files
            # Use the tempdir so it is cleaned up later
            values = [0, 1024, 237823782378, -47]
            filenames = [
                "tx_bytes",
                "tx_bytes_increased",
                "tx_bytes_increased_big",
                "tx_bytes_decreased",
            ]
            for index, value in enumerate(values):
                write_temp_stats_file(Path(tempdir), filenames[index], value)

            # Create the class instance
            class_ = stats.NetworkStats(nm_manager)

            # Add a file that does not exist
            filenames += ["idonotexist"]

            # For the expected values we want the human readable string
            # The last two are special
            #   - 0 B because the value has decreased
            #   - default text because the file does not exist
            expected_values = [
                "0 B",
                "1.00 kB",
                "221.49 GB",
                "0 B",
                class_.default_text,
            ]

            # Loop over the files,
            # patch it and check if the expected value holds
            for index, filename in enumerate(filenames):
                location = Path(tempdir) / filename
                file_ = try_open(location)
                with patch("eduvpn.ui.stats.NetworkStats.upload_file", file_):
                    self.assertEqual(class_.upload, expected_values[index])
                    class_.cleanup()
