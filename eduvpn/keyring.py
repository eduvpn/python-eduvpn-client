import json
import logging
import os
from abc import ABC, abstractmethod

import gi

secureKeyring = True
try:
    gi.require_version("Secret", "1")
    from gi.repository import Secret  # type: ignore
except (ValueError, ImportError):
    secureKeyring = False


logger = logging.getLogger(__name__)


class TokenKeyring(ABC):
    def __init__(self, variant):
        self.variant = variant

    @property
    def available(self) -> bool:
        return True

    @property
    def secure(self) -> bool:
        return False

    @abstractmethod
    def clear(self, attributes) -> bool:
        pass

    @abstractmethod
    def save(self, label, attributes, secret):
        pass

    @abstractmethod
    def load(self, attributes):
        pass


class DBusKeyring(TokenKeyring):
    """A keyring using libsecret with DBus"""

    def __init__(self, variant):
        super().__init__(variant)
        # None is the default collection
        self.collection = None

    # This keyring is secure
    def secure(self):
        return True

    @property
    def available(self):
        # If import was not successful, this is definitely not available
        if not secureKeyring:
            logger.warning("keyring not available due to import not available")
            return False

        # Libs available, do a test run
        try:
            attributes = {"test": "test"}
            secret = "eduVPN test"
            self.save("eduVPN testing run", attributes, secret)
            assert self.load(attributes) == secret
            self.clear(attributes)
        except (gi.repository.GLib.Error, AssertionError) as e:
            logger.warning(f"error when checking if keyring is available: {e}")
            return False
        return True

    def create_schema(self, attributes):
        return Secret.Schema.new(
            self.variant.name,
            Secret.SchemaFlags.NONE,
            {k: Secret.SchemaAttributeType.STRING for k in attributes},
        )

    def clear(self, attributes) -> bool:
        schema = self.create_schema(attributes)
        return Secret.password_clear_sync(schema, attributes, None)

    def save(self, label, attributes, secret):
        # Prefix the label with the client name
        label = f"{self.variant.name} - {label}"
        schema = self.create_schema(attributes)
        return Secret.password_store_sync(
            schema, attributes, self.collection, label, str(secret), None
        )

    def load(self, attributes):
        """Load a password in the secret service, return None when found nothing"""
        schema = self.create_schema(attributes)
        return Secret.password_lookup_sync(schema, attributes, None)


JSON_VERSION = "v1"


class InsecureFileKeyring(TokenKeyring):
    def __init__(self, variant):
        super().__init__(variant)

    @property
    def filename(self):
        return self.variant.config_prefix / "keys"

    def unique_key(self, attributes):
        return ",".join(list(attributes.values()))

    def load_previous(self):
        with open(self.filename, "r") as f:
            try:
                c = json.load(f)
            except Exception as e:
                logger.debug(f"failed to load JSON: {str(e)}")
                c = {}
            return c.get(JSON_VERSION, {})

    def write(self, vals):
        towrite = {JSON_VERSION: vals}
        with open(self.filename, "w+") as f:
            json.dump(towrite, f)

    def clear(self, attributes) -> bool:
        # Get previous entries
        new = {}
        if os.path.exists(self.filename):
            new = self.load_previous()
        key = self.unique_key(attributes)
        new.pop(key, None)
        self.write(new)
        return True

    def save(self, label, attributes, secret):
        new = {}

        # Get previous entries
        if os.path.exists(self.filename):
            new = self.load_previous()

        # add/overwrite new entry
        key = self.unique_key(attributes)
        new[key] = secret

        # Write new values
        self.write(new)

    def load(self, attributes):
        if not os.path.exists(self.filename):
            return None
        previous = self.load_previous()
        key = self.unique_key(attributes)
        return previous.get(key, None)
