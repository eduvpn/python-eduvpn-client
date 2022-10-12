from eduvpn import settings
from eduvpn.config import Configuration
from eduvpn.settings import (CLIENT_ID, CONFIG_PREFIX, LETSCONNECT_CLIENT_ID,
                        LETSCONNECT_CONFIG_PREFIX)
from typing import Optional, Tuple


class ApplicationVariant:
    def __init__(
        self,
        app_id: str,
        name: str,
        icon: str,
        translation_domain: str,
        logo: Optional[str] = None,
        server_image: Optional[str] = None,
        use_predefined_servers: bool = True,
        use_configured_servers: bool = True,
    ) -> None:
        self.app_id = app_id
        self.name = name
        self.icon = icon
        self.logo = logo
        self.server_image = server_image
        self.translation_domain = translation_domain
        self.use_predefined_servers = use_predefined_servers
        self.use_configured_servers = use_configured_servers


EDUVPN = ApplicationVariant(
    app_id="org.eduvpn.client",
    name=settings.EDUVPN_NAME,
    icon=settings.EDUVPN_ICON,
    translation_domain="eduVPN",
)

LETS_CONNECT = ApplicationVariant(
    app_id="org.letsconnect-vpn.client",
    name=settings.LETS_CONNECT_NAME,
    icon=settings.LETS_CONNECT_ICON,
    logo=settings.LETS_CONNECT_LOGO,
    server_image=settings.SERVER_ILLUSTRATION,
    translation_domain="LetsConnect",
    use_predefined_servers=False,
    use_configured_servers=False,
)


def get_variant_settings(variant: ApplicationVariant) -> Tuple[str, str, str]:
    if variant == EDUVPN:
        return CLIENT_ID, str(CONFIG_PREFIX)
    return LETSCONNECT_CLIENT_ID, str(LETSCONNECT_CONFIG_PREFIX)


def get_variant_config(variant: ApplicationVariant) -> Configuration:
    directory = get_variant_settings(variant)[1]
    return Configuration.load(directory)


def get_variant_vpn_name(variant: ApplicationVariant) -> str:
    return variant.translation_domain.lower()
