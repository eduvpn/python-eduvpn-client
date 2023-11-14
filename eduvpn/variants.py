from pathlib import Path
from typing import Optional, Tuple

from eduvpn import __version__
from eduvpn.config import Configuration
from eduvpn.utils import get_config_dir, get_prefix


class ApplicationVariant:
    def __init__(
        self,
        app_id: str,
        client_id: str,
        config_name: str,
        name: str,
        logo: Optional[str] = None,
        logo_dark: Optional[str] = None,
        uses_discovery: bool = True,
    ) -> None:
        self.app_id = app_id
        self.client_id = client_id
        self.config_prefix = (Path(get_config_dir()).expanduser() / config_name).resolve()
        self.config_name = config_name
        self.name = name
        prefix = get_prefix()
        self.icon = prefix + f"/share/icons/hicolor/128x128/apps/{app_id}.png"
        self.image_prefix = prefix + f"/share/{config_name}/images/"
        self.logo = self.image_prefix + "logo.png"
        self.logo_dark = self.image_prefix + "logo-dark.png"

        # fallback if dark logo does not exist
        if not Path(self.logo_dark).is_file():
            self.logo_dark = self.logo
        self.search_image = self.image_prefix + "search-icon.png"
        self.uses_discovery = uses_discovery
        self.country_map = None
        self.flag_prefix = None
        if uses_discovery:
            # TODO: do not hard code eduvpn here?
            self.country_map = Path(prefix + "/share/eduvpn/country_codes.json")
            self.flag_prefix = prefix + "/share/eduvpn/images/flags/png/"

    @property
    def settings(self) -> Tuple[str, str, str]:
        return self.client_id, str(__version__), str(self.config_prefix)

    @property
    def translation_domain(self) -> str:
        return self.config_name

    @property
    def config(self) -> Configuration:
        return Configuration.load(self.config_prefix)

    @property
    def logfile(self) -> Path:
        return self.config_prefix / "log"


EDUVPN = ApplicationVariant(
    app_id="org.eduvpn.client",
    client_id="org.eduvpn.app.linux",
    config_name="eduvpn",
    name="eduVPN",
)

LETS_CONNECT = ApplicationVariant(
    app_id="org.letsconnect-vpn.client",
    client_id="org.letsconnect-vpn.app.linux",
    config_name="letsconnect",
    name="Let's Connect!",
    uses_discovery=False,
)
