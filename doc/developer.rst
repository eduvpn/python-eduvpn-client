Developer notes
===============

Notes about code
----------------

Use the decorator ``eduvpn.utils.run_in_background_thread`` to schedule long running action
in the background to avoid blocking the main thread.

Never call GTK functions directly from a background thread,
use ``eduvpn.utils.run_in_main_gtk_thread`` to decorate functions
that must run on the main thread (eg. UI updates).


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

* Determine version number (for example 4.1.0)

* Compose a list of changes (check issue tracker)

* Make sure the test suite runs with python3

* Set version number in ``setup.py``, and ``eduvpn.spec``

* add changes to CHANGES.md

* Commit

* Press release button on github. List all changes here also

* Check if github actions builds.

* The release will trigger a build on readthedocs, but the active version still needs to be set manually here:
  https://readthedocs.org/projects/python-eduvpn-client/versions/

Upload to pypi
^^^^^^^^^^^^^^

do a manual wheel upload using `twine <https://github.com/pypa/twine>`_:

.. code-block:: console

    $ rm dist/*
    $ python setup.py bdist_wheel sdist
    $ twine upload dist/*
    
There is also a make shortcut:

.. code-block:: console

    $ make twine-upload
    
Building RPMs
^^^^^^^^^^^^^^^^^^^^^^
We use `builder.rpm <https://git.sr.ht/~fkooman/builder.rpm>`_, to build the RPM packages.

Build Debian packages
^^^^^^^^^^^^^^^^^^^^^
We use `nbuilder.deb <https://git.sr.ht/~fkooman/builder.deb>`_, to build the DEB packages.
