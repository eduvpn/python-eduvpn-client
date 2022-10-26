import gettext
import json
import locale
import logging
import os

from eduvpn.settings import COUNTRY, COUNTRY_MAP, LANGUAGE
from eduvpn.utils import get_prefix
from eduvpn.variants import ApplicationVariant

logger = logging.getLogger(__name__)

country_mapping = None


def initialize(app_variant: ApplicationVariant):
    prefix = get_prefix()
    try:
        setup(app_variant, prefix)
        logger.debug("i18n successfully initialized")
    except Exception as e:
        logger.error(f"i18n initialization failed: {e}")


def setup(app_variant: ApplicationVariant, prefix: str):
    """
    Init locale and gettext, returns text domain
    """
    domain = app_variant.translation_domain
    directory = os.path.join(prefix, "share/locale")

    locale.setlocale(locale.LC_ALL, "")
    locale.bindtextdomain(domain, directory)  # type: ignore
    locale.textdomain(domain)  # type: ignore
    gettext.bindtextdomain(domain, directory)
    gettext.textdomain(domain)

    return domain


def country() -> str:
    try:
        locale_setting = locale.getlocale()[0]
        if not locale_setting:
            return COUNTRY
        return locale_setting.replace("_", "-")
    except Exception:
        return COUNTRY


def language() -> str:
    try:
        locale_setting = locale.getlocale()[0]
        if not locale_setting:
            return LANGUAGE
        return locale_setting.split("_")[0]
    except Exception:
        return LANGUAGE


def retrieve_country_name(country_code: str) -> str:
    country_map = _read_country_map()
    loc = locale.getlocale()
    if loc[0] is None:
        prefix = "en"
    else:
        prefix = loc[0][:2]
    if country_code in country_map:
        code = country_map[country_code]
        if prefix in code:
            return code[prefix]
    return country_code


def _read_country_map() -> dict:
    """
    Read the storage from disk, returns an empty dict in case of failure.
    """
    global country_mapping

    if country_mapping is not None:
        return country_mapping

    if COUNTRY_MAP.exists():
        try:
            with open(COUNTRY_MAP, "r") as f:
                country_mapping = json.load(f)
                return country_mapping
        except Exception as e:
            logger.error(f"Error reading country map: {e}")
    return {}
