from eduvpn.util import get_prefix
from typing import Tuple

prefix = get_prefix()

eduvpn_main_logo = prefix + "/share/icons/hicolor/" \
                            "128x128/apps/eduvpn-client.png"  # type: str
eduvpn_name = "eduVPN"  # type: str
lets_connect_main_logo = prefix + "/share/icons/hicolor/128x128" \
                                  "/apps/lets-connect-client.png"  # type: str
lets_connect_name = "Let's Connect!"  # type: str


def get_brand(lets_connect):  # type: (bool) -> Tuple[str, str]
    """
    args:	
        lets_connect (bool): Let's connect mode?	
    returns:	
        (str, str): logo, name	
    """
    if lets_connect:
        return lets_connect_main_logo, lets_connect_name
    else:
        return eduvpn_main_logo, eduvpn_name
