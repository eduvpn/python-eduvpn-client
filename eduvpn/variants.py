from pathlib import Path
from typing import Optional, Tuple

from eduvpn import __version__, settings
from eduvpn.config import Configuration
from eduvpn.settings import (CLIENT_ID, CONFIG_PREFIX, LETSCONNECT_CLIENT_ID,
                             LETSCONNECT_CONFIG_PREFIX)


class ApplicationVariant:
    def __init__(
        self,
        app_id: str,
        client_id: str,
        config_prefix: Path,
        name: str,
        icon: str,
        translation_domain: str,
        logo: Optional[str] = None,
        logo_dark: Optional[str] = None,
        server_image: Optional[str] = None,
        use_predefined_servers: bool = True,
        use_configured_servers: bool = True,
    ) -> None:
        self.app_id = app_id
        self.client_id = client_id
        self.config_prefix = config_prefix
        self.name = name
        self.icon = icon
        self.logo = logo
        self.logo_dark = logo_dark
        self.server_image = server_image
        self.translation_domain = translation_domain
        self.use_predefined_servers = use_predefined_servers
        self.use_configured_servers = use_configured_servers

    @property
    def settings(self) -> Tuple[str, str, str]:
        return self.client_id, str(__version__), str(self.config_prefix)

    @property
    def config(self) -> Configuration:
        return Configuration.load(self.config_prefix)

    @property
    def logfile(self) -> Path:
        return self.config_prefix / "log"


EDUVPN = ApplicationVariant(
    app_id="org.eduvpn.client",
    client_id=CLIENT_ID,
    config_prefix=CONFIG_PREFIX,
    name=settings.EDUVPN_NAME,
    icon=settings.EDUVPN_ICON,
    logo=settings.EDUVPN_LOGO,
    logo_dark=settings.EDUVPN_LOGO_DARK,
    translation_domain="eduVPN",
)

LETS_CONNECT = ApplicationVariant(
    app_id="org.letsconnect-vpn.client",
    client_id=LETSCONNECT_CLIENT_ID,
    config_prefix=LETSCONNECT_CONFIG_PREFIX,
    name=settings.LETS_CONNECT_NAME,
    icon=settings.LETS_CONNECT_ICON,
    logo=settings.LETS_CONNECT_LOGO,
    logo_dark=settings.LETS_CONNECT_LOGO,
    server_image=settings.SERVER_ILLUSTRATION,
    translation_domain="LetsConnect",
    use_predefined_servers=False,
    use_configured_servers=False,
)
