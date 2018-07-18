Developer notes
===============

use ``eduvpn.util.thread_helper(lambda: func(arg='arg')`` to schedule long running actions on a thread.


use ``GLib.idle_add(lambda: func(arg='arg')`` to schedule UI updates back on the main thread.

Never call GTK functions directly from the background thread.