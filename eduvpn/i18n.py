from typing import Union, Dict
from eduvpn.settings import COUNTRY, LANGUAGE


def extract_translation(d: Union[str, Dict[str, str]]):
    if isinstance(d, dict):
        for m in [COUNTRY, LANGUAGE, 'en-US', 'en']:
            try:
                return d[m]
            except KeyError:
                continue
        return list(d.values())[0]  # otherwise just return first in list
    else:
        return d