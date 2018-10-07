Developer notes
===============

Notes about code
----------------

Use ``eduvpn.util.thread_helper(lambda: func(arg='arg')`` to schedule long running actions from the UI (main) thread.


Use ``GLib.idle_add(lambda: func(arg='arg')`` to schedule UI updates back on the main thread.

Never call GTK functions directly from the background thread.


``eduvpn.actions`` are the entrypoints to the application and are triggered from the main menu or a VPN status
change.

``eduvpn.steps`` contains all the various steps in the application flow.

``eduvpn.remote`` contains all remote requests.

```eduvpn.other_nm`` is a fork of the python NetworkManager wrapper.


Flow schema
-----------

.. image:: flow.png
   :target: _images/flow.png
   :alt: The application flow


How to make a release
---------------------

* Determine version number (for example 1.0.2)

* Compose a list of changes (check issue tracker)

* Make sure the test suite runs with python2 and python3

* Set version number in ``setup.py``, ``setup_letsconnect.py`` and ``rpm/\*.spec``

* add changes to CHANGES.md

* Commit

* Press release button on github. List all changes here also

* Check if travis builds. If so, it will upload to pypi.

* If it doesn't build fix and do a manual upload using `twine <https://github.com/pypa/twine>`_

* For now you need to manually create the Let's connect! wheel and upload using twine.

* Make a SRPM and upload to the `COPR repository <https://copr.fedorainfracloud.org/coprs/gijzelaerr/eduvpn-client/>`_

.. note::

   ``$ make srpm`` will use docker to build a srpm and put it in tmp/


* Update the debian package using the `eduVPN Debian meta files <https://github.com/eduvpn-debian/packaging>`_.
