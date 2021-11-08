from typing import TypeVar, Generic, Any, Dict
import logging
import json
from .settings import CONFIG_PREFIX


T = TypeVar('T')


CONFIG_FILE_NAME = 'config.json'

CONFIG_PATH = CONFIG_PREFIX / CONFIG_FILE_NAME

DEFAULT_SETTINGS = dict(
    force_tcp=False,
)


logger = logging.getLogger(__name__)


class SettingDescriptor(Generic[T]):
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner=None) -> T:
        return instance.get_setting(self.name)

    def __set__(self, instance, value: T):
        instance.set_setting(self.name, value)


class Configuration:
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings

    @classmethod
    def load(cls):
        if not CONFIG_PATH.exists():
            return cls(dict(DEFAULT_SETTINGS))
        with open(CONFIG_PATH, 'r') as f:
            try:
                settings = json.load(f)
            except Exception:
                logger.exception("error loading settings")
                settings = {}
            else:
                logger.debug(f"loaded settings: {settings}")
        settings = {**DEFAULT_SETTINGS, **settings}
        return cls(settings)

    def save(self):
        logger.debug(f"saving settings: {self.settings}")
        with open(CONFIG_PATH, 'w') as f:
            json.dump(self.settings, f)

    def get_setting(self, name: str):
        return self.settings[name]

    def set_setting(self, name: str, value: Any):
        if value != self.settings[name]:
            self.settings[name] = value
            self.save()

    force_tcp = SettingDescriptor[bool]()
