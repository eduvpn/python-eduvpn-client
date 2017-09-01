import os
import sys


if sys.platform.startswith('darwin'):
    from .osx import *
else:
    from .dbus import *