import json
import logging
from typing import Optional, Type, Any, Dict, Generic, TypeVar

from eduvpn.settings import CONFIG_PREFIX

T = TypeVar("T")


CONFIG_FILE_NAME = "org.eduvpn.app.linux_additional.json"

CONFIG_PATH = CONFIG_PREFIX / CONFIG_FILE_NAME

DEFAULT_SETTINGS = dict(
    autoconnect=False,
    prefer_tcp=False,
    nm_system_wide=False,
)


logger = logging.getLogger(__name__)


class SettingDescriptor(Generic[T]):
    def __set_name__(self, owner: "Configuration", name: str) -> None:
        self.name = name

    def __get__(self, instance: "Configuration", owner: "Configuration") -> T:
        return instance.get_setting(self.name)

    def __set__(self, instance: "Configuration", value: T) -> None:
        instance.set_setting(self.name, value)


class Configuration:
    def __init__(self, settings: Dict[str, Any]) -> None:
        self.settings = settings

    @classmethod
    def load(cls) -> "Configuration":
        if not CONFIG_PATH.exists():
            return cls(dict(DEFAULT_SETTINGS))
        with open(CONFIG_PATH, "r") as f:
            try:
                settings = json.load(f)
            except Exception:
                logger.exception("error loading settings")
                settings = {}
            else:
                logger.debug(f"loaded settings: {settings}")
        settings = {**DEFAULT_SETTINGS, **settings}
        return cls(settings)

    def save(self) -> None:
        logger.debug(f"saving settings: {self.settings}")
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.settings, f)

    def get_setting(self, name: str) -> bool:
        return self.settings[name]

    def set_setting(self, name: str, value: Any) -> None:
        if value != self.settings[name]:
            self.settings[name] = value
            self.save()

    autoconnect = SettingDescriptor[bool]()
    prefer_tcp = SettingDescriptor[bool]()
    nm_system_wide = SettingDescriptor[bool]()
