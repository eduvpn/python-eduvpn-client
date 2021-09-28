from typing import Optional
from . import settings


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
    ):
        self.app_id = app_id
        self.name = name
        self.icon = icon
        self.logo = logo
        self.server_image = server_image
        self.translation_domain = translation_domain
        self.use_predefined_servers = use_predefined_servers
        self.use_configured_servers = use_configured_servers


EDUVPN = ApplicationVariant(
    app_id='org.eduvpn.client',
    name=settings.EDUVPN_NAME,
    icon=settings.EDUVPN_ICON,
    translation_domain='eduVPN',
)

LETS_CONNECT = ApplicationVariant(
    app_id='org.letsconnect-vpn.client',
    name=settings.LETS_CONNECT_NAME,
    icon=settings.LETS_CONNECT_ICON,
    logo=settings.LETS_CONNECT_LOGO,
    server_image=settings.SERVER_ILLUSTRATION,
    translation_domain='LetConnect',
    use_predefined_servers=False,
    use_configured_servers=False,
)
