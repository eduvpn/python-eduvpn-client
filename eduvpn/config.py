import json
import logging
from pathlib import Path
from typing import Any, Dict, Generic, Type, TypeVar

T = TypeVar("T")


CONFIG_FILE_NAME = "config.json"

DEFAULT_SETTINGS = dict(
    ignore_keyring_warning=False,
)


logger = logging.getLogger(__name__)


class SettingDescriptor(Generic[T]):
    def __set_name__(self, owner: Type["Configuration"], name: str) -> None:
        self.name = name

    def __get__(
        self, instance: Type["Configuration"], owner: Type["Configuration"]
    ) -> bool:
        return instance.get_setting(self.name)  # type: ignore

    def __set__(self, instance: Type["Configuration"], value: T) -> None:
        instance.set_setting(self.name, value)  # type: ignore


class Configuration:
    def __init__(self, config_path: Path, settings: Dict[str, Any]) -> None:
        self.config_path = config_path
        self.settings = settings

    @classmethod
    def load(cls, config_dir: Path) -> "Configuration":
        config_path = config_dir / CONFIG_FILE_NAME
        if not config_path.exists():
            return cls(config_path, dict(DEFAULT_SETTINGS))
        with open(config_path, "r") as f:
            try:
                settings = json.load(f)
            except Exception:
                logger.exception("error loading settings")
                settings = {}
            else:
                logger.debug(f"loaded settings: {settings}")
        settings = {**DEFAULT_SETTINGS, **settings}
        return cls(config_path, settings)

    def save(self) -> None:
        logger.debug(f"saving settings: {self.settings}")
        with open(self.config_path, "w") as f:
            json.dump(self.settings, f)

    def get_setting(self, name: str) -> bool:
        return self.settings[name]

    def set_setting(self, name: str, value: Any) -> None:
        if value != self.settings[name]:
            self.settings[name] = value
            self.save()

    ignore_keyring_warning = SettingDescriptor[bool]()
