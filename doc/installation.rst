============
Installation
============

The Desktop client only works on Linux, but the command-line interface and most parts of the API are usable on other
platforms also. Python 3.6+ is required. It is recommended to use a deb or rpm package to install the eduVPN client.
You can also install using pip from pypi or directly from Github. We distribute RPM packages for Fedora, and deb
packages for Debian and Ubuntu.

The eduVPN client has been tested with:

 * Debian 10 (Buster)
 * Ubuntu 20.04 LTS and 18.04 LTS
 * CentOS 8
 * Fedora 34 and 35

.. note::

    If you target is not supported the client might still work with limited functionality. You need to have
    `Network Manager <https://wiki.gnome.org/Projects/NetworkManager>`_ and `OpenVPN 2.4.0+ <https://openvpn.net/>`_
    installed.


Debian and Ubuntu
=================

You can install the latest release on Debian or Ubuntu using the eduVPN packaging repository by running these commands:

.. code-block:: console

    $ sudo apt install apt-transport-https curl
    $ curl -L https://app.eduvpn.org/linux/deb/eduvpn.key | sudo apt-key add -
    $ echo "deb https://app.eduvpn.org/linux/deb/ stable main" | sudo tee -a /etc/apt/sources.list.d/eduvpn.list
    $ sudo apt update
    $ sudo apt install eduvpn-client


Fedora and CentOS
=================

You can install the latest release of the eduVPN client on Fedora or CentOS by running these commands :

.. code-block:: console

    $ sudo dnf install dnf-plugins-core
    $ sudo dnf copr enable @eduvpn/eduvpn-client
    $ sudo dnf install eduvpn-client

More information is available at `fedora copr <https://copr.fedorainfracloud.org/coprs/g/eduvpn/eduvpn-client/>`_.


Manual source installation
==========================

Dependencies
------------

To manually install the eduVPN package you first need to satisfy the build requirements.

For Debian or Ubuntu:

.. code-block:: console

    $ sudo apt install build-essential git make

For fedora:

.. code-block:: console

    $ sudo dnf install git make

For Debian or Ubuntu we made a make target to install the required debian packages:

.. code-block:: console

    $ sudo make deb

For fedora we did the same:

.. code-block:: console

    $ sudo make dnf

Pip
---

You can install the client API from pypi:

.. code-block:: console

    $ pip install "eduvpn-client[gui]"

Or, if you want to try out the bleeding edge development version:

.. code-block:: console

    $ pip install git+https://github.com/eduvpn/python-eduvpn-client.git

.. note::

    This requires the installation of system packages
    using your distributions package manager.
    Consult the `Makefile`_ for the complete list.


Development version
-------------------

You first need to obtain the code:

.. code-block:: console

    $ git clone https://github.com/eduvpn/python-eduvpn-client.git
    $ cd python-eduvpn-client


We've made various Makefile targets to quickly get started. For example to start the eduVPN GUI:

.. code-block:: console

    $ make eduvpn-gui

Please have a look in the `Makefile`_ to find out the available targets.


Issues
======

If you experience any issues you could and should report them at our
`issue tracker <https://github.com/eduvpn/python-eduvpn-client/issues>`_. Please don't forget to mention your OS,
method of installation, eduVPN client version and instructions on how to reproduce the problem. If you have a problem
enabling your VPN connection please also examine the `journalctl -u NetworkManager` logs.


Source code
===========


Development of this project takes place on `github <https://github.com/eduvpn/python-eduvpn-client>`_.  You
can find the source code and all releases there.

Contributing
============

Contributions are more than welcome! If you experience any problems let us know in the bug tracker. We accept patches
in the form of github pull requests. Please make sure your code works with python3 and is pycodestyle (formerly pep8) compatible.
Also make sure the test suite actually passes all tests. Translations are also welcome!


.. _Makefile: https://github.com/eduvpn/python-eduvpn-client/blob/master/Makefile
