from eduvpn.variants import ApplicationVariant
import gi

gi.require_version("Notify", "0.7")  # noqa: E402
from gi.repository import GdkPixbuf  # noqa: E402
from gi.repository import Notify  # type: ignore[attr-defined] # noqa: E402


def initialize(app_variant: ApplicationVariant) -> None:
    Notify.init(app_variant.name)


class Notification:
    def __init__(self, app_variant: ApplicationVariant) -> None:
        self.app_variant = app_variant
        self.notification = None

    def _build(self):
        icon = GdkPixbuf.Pixbuf.new_from_file(self.app_variant.icon)
        notification = Notify.Notification.new(self.app_variant.name)
        notification.set_icon_from_pixbuf(icon)
        notification.set_app_name(self.app_variant.name)
        return notification

    def show(self, title: str, message: str):
        if self.notification is None:
            self.notification = self._build()
        assert self.notification is not None
        self.notification.update(title, message)
        self.notification.show()

    def hide(self) -> None:
        if self.notification is not None:
            self.notification.close()
            self.notification = None
