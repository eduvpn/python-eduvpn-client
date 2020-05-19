from functools import lru_cache
from sys import prefix
from os import path

from logging import getLogger


def get_logger(name_space: str):
    return getLogger(name_space)


logger = get_logger(__file__)


@lru_cache(maxsize=1)
def get_prefix() -> str:
    """
    Returns the Python prefix where eduVPN is installed

    returns:
        path to Python installation prefix
    """
    target = 'share/eduvpn/eduvpn.png'
    local = path.dirname(path.dirname(path.abspath(__file__)))
    options = [local, path.expanduser('~/.local'), '/usr/local', prefix]
    for option in options:
        logger.debug(u"looking for '{}' in '{}'".format(target, option))
        if path.isfile(path.join(option, target)):
            return option
    raise Exception("Can't find eduVPN installation")
