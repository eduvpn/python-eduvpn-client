Developer notes
===============

Notes about code
----------------

Use the decorator ``eduvpn.utils.run_in_background_thread`` to schedule long running action
in the background to avoid blocking the main thread.

Never call GTK functions directly from a background thread,
use ``eduvpn.utils.run_in_main_gtk_thread`` to decorate functions
that must run on the main thread (eg. UI updates).

This library closely follows eduvpn-common. To see the API for that,
`see here
<https://eduvpn.github.io/eduvpn-common/api/python/rtd/index.html>`_

Most of the interaction with this library is in ``eduvpn.app``, the ui
is in ``eduvpn.ui.ui`` and the cli in ``eduvpn.cli``. In these files
you can see lots of state transitions defined. The state transitions
that are used are closely in line with the Finite State machine from
the eduvpn-common library. A figure for this state machine can be
`found here
<https://eduvpn.github.io/eduvpn-common/gettingstarted/debugging/fsm.html>`_.


Running the tests
-----------------

To run the automated tests,
use the following command from the root of the project.

.. code-block:: console

    $ pytest

How to make a release
---------------------

Prepare the code
^^^^^^^^^^^^^^^^

* Determine version number (for example 4.1.1)

* Compose a list of changes (check issue tracker)

* Make sure the test suite runs with python3

* Set version number in ``setup.py``, and ``eduvpn.spec`` and ensure eduvpn-common has the targeted version set

* add changes to CHANGES.md

* Commit

* Press release button on github. List all changes here also

* Check if GitHub Actions builds.

* The release will trigger a build on readthedocs, but the active version still needs to be set manually here:
  https://readthedocs.org/projects/python-eduvpn-client/versions/

Upload to PyPi
^^^^^^^^^^^^^^

do a manual wheel upload using `twine <https://github.com/pypa/twine>`_:

.. code-block:: console

    $ rm dist/*
    $ python setup.py bdist_wheel sdist
    $ twine upload dist/*
    
There is also a make shortcut:

.. code-block:: console

    $ make twine-upload

You should also make sure that eduvpn-common is updated in PyPi!
    
Building RPMs
^^^^^^^^^^^^^^^^^^^^^^
We use `builder.rpm <https://git.sr.ht/~fkooman/builder.rpm>`_, to build the RPM packages.

Build Debian packages
^^^^^^^^^^^^^^^^^^^^^
We use `nbuilder.deb <https://git.sr.ht/~fkooman/builder.deb>`_, to build the DEB packages.
