import gi
gi.require_version('Notify', '0.7')
from gi.repository import GdkPixbuf, Notify  # type: ignore
from .variants import ApplicationVariant


def initialize(app_variant: ApplicationVariant):
    Notify.init(app_variant.name)


class Notification:
    def __init__(self, app_variant: ApplicationVariant):
        icon = GdkPixbuf.Pixbuf.new_from_file(app_variant.icon)  # type: ignore
        self.notification = Notify.Notification.new(app_variant.name)
        self.notification.set_icon_from_pixbuf(icon)
        self.notification.set_app_name(app_variant.name)
        self.is_shown = False

    def show(self, title: str, message: str):
        if not self.is_shown:
            self.notification.update(title, message)
            self.notification.show()
            self.is_shown = True

    def hide(self):
        if self.is_shown:
            self.notification.close()
            self.is_shown = False
