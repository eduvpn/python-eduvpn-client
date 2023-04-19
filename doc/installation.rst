============
Installation
============

The Desktop client only works on Linux. Python 3.6+ is required. It is
recommended to use a deb or rpm package to install the eduVPN client.
You can also install using pip from pypi or directly from Github. We
distribute RPM packages for Fedora, and deb packages for Debian and
Ubuntu.

The eduVPN client has been tested with:

 * Debian 11 (Bullseye)
 * Ubuntu 22.04 LTS
 * Fedora 36 and 37

.. note::

    If your target is not supported you can make an issue on the `GitHub <https://github.com/eduvpn/python-eduvpn-client>`_ and we will see if we can provide it. Right now we only provide `x86_64` packages (we use a compiled dependency), if you want an ARM package for a certain target you can also make an issue.


Debian (11) and Ubuntu (22.04 & 22.10)
======================================

.. code-block:: console

    $ sudo apt install apt-transport-https lsb-release wget
    $ wget -O- https://app.eduvpn.org/linux/v4/deb/app+linux@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4.gpg >/dev/null
    $ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4.gpg] https://app.eduvpn.org/linux/v4/deb/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4.list
    $ sudo apt update
    $ sudo apt install eduvpn-client

Fedora (36, 37 & 38)
====================

.. code-block:: console

    $ curl -O https://app.eduvpn.org/linux/v4/rpm/app+linux@eduvpn.org.asc
    $ sudo rpm --import app+linux@eduvpn.org.asc
    $ cat << 'EOF' | sudo tee /etc/yum.repos.d/python-eduvpn-client_v4.repo
    [python-eduvpn-client_v4]
    name=eduVPN for Linux 4.x (Fedora $releasever)
    baseurl=https://app.eduvpn.org/linux/v4/rpm/fedora-$releasever-$basearch
    gpgcheck=1
    EOF
    $ sudo dnf install eduvpn-client

CentOS (Stream 9)
=================

.. code-block:: console

    $ curl -O https://app.eduvpn.org/linux/v4/rpm/app+linux@eduvpn.org.asc
    $ sudo rpm --import app+linux@eduvpn.org.asc
    $ cat << 'EOF' | sudo tee /etc/yum.repos.d/python-eduvpn-client_v4.repo
    [python-eduvpn-client_v4]
    name=eduVPN for Linux 4.x (CentOS Stream 9)
    baseurl=https://app.eduvpn.org/linux/v4/rpm/centos-stream+epel-next-9-$basearch
    gpgcheck=1
    EOF
    $ sudo dnf install eduvpn-client

Arch (Unofficial)
=================

There is an unofficial package in the `Arch User Repository (AUR) <https://aur.archlinux.org/packages/python-eduvpn-client/>`_.


Pip installation
==========================
We also provide pip packages. These are useful if your distro is not officially supported in our packaging (yet).

Dependencies
------------

To manually install the eduVPN package via Pip you first need to satisfy the dependencies.

For Debian or Ubuntu:

.. code-block:: console

    $ sudo apt update
    $ sudo apt install \
		gir1.2-nm-1.0 \
		gir1.2-secret-1 \
		gir1.2-gtk-3.0 \
		gir1.2-notify-0.7 \
		libgirepository1.0-dev \
		libdbus-glib-1-dev \
		python3-gi \
		python3-setuptools \
		python3-pytest \
		python3-wheel \
		python3-dbus \
		network-manager-openvpn-gnome

For Fedora:

.. code-block:: console

    $ sudo dnf install \
		libnotify \
		libsecret \
		gtk3 \
		python3-dbus \
		python3-gobject \
		python3-pytest \
		python3-cairo-devel \
		gobject-introspection-devel \
		cairo-gobject-devel \
		dbus-python-devel

Pip commands
------------

You can then continue with installing via Pip:

.. code-block:: console

    $ pip install "eduvpn-client[gui]"

Or, if you want to try out the bleeding edge development version:

.. code-block:: console

    $ pip install git+https://github.com/eduvpn/python-eduvpn-client.git


Issues
======

If you experience any issues you could and should report them at our
`issue tracker <https://github.com/eduvpn/python-eduvpn-client/issues>`_. Please don't forget to mention your OS,
method of installation, eduVPN client version and instructions on how to reproduce the problem. If you have a problem
enabling your VPN connection please also examine the `journalctl -u NetworkManager` logs. The log file of the eduVPN app
can also help us figure out the problem, running the gui or cli in debug mode (-d) flag will print debug logging to the log file
located at: ~/.config/eduvpn/log or ~/.config/letsconnect/log for Let's Connect!.


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
