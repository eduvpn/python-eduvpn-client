============
Introduction
============

This is the GNU/Linux desktop client and Python API for eduVPN. The Desktop client only works on Linux, but most parts
of the API are usable on other platforms also. Python 3.6+ is required.

Installation
============

It is recommended to use a package to install the eduVPN client, but you can also install using pip from py or directly
from github. We distribute RPM packages for Fedora, and Deb packages for Debian and Ubuntu.

The eduVPN client has been tested with:

 * Debian 10 (Buster)
 * Ubuntu 20.04 LTS & 18.04 LTS
 * CentOS 8
 * Fedora 32

.. note::

    If you target is not supported the client might still work with limited functionality. You need to have
    `Network Manager <https://wiki.gnome.org/Projects/NetworkManager>`_ and `OpenVPN 2.4.0+ <https://openvpn.net/>`_
    installed.


Debian and Ubuntu
-----------------

You can install the latest release on Debian or Ubuntu using the eduVPN packaging repository by running these commands
as root or using sudo:

.. code-block:: bash

    $ apt install apt-transport-https curl
    $ curl -L https://repo.eduvpn.org/debian/eduvpn.key | apt-key add -
    $ echo "deb https://repo.eduvpn.org/debian/ stretch main" > /etc/apt/sources.list.d/eduvpn.list
    $ apt update
    $ apt install eduvpn-client

.. note::

    For Debian Stretch you need to enable the backports repository and manually update network manager.
    `network-manager-openvpn` >= 1.2.10 is required for `tls-crypt` support. To enable the backports repository add
    this line to your `/etc/apt/sources.list`::

        deb http://deb.debian.org/debian stretch-backports main contrib non-free

    And then update network-manager::

        $ sudo apt-get update
        $ sudo apt-get -t stretch-backports install network-manager-openvpn-gnome

Fedora
------

You can install the latest release of the eduVPN client on Fedora by running these commands as root or using sudo:

.. code-block:: bash

    $ dnf install dnf-plugins-core
    $ dnf copr enable gijzelaerr/eduvpn-client
    $ dnf install eduvpn-client

More information is available at `fedora copr <https://copr.fedorainfracloud.org/coprs/gijzelaerr/eduvpn-client/>`_.


Centos
------

You can install the latest release of the eduVPN client on Centos 8 by running these commands as root or using sudo:

.. code-block:: bash

    $ yum install yum-plugin-copr
    $ yum copr enable gijzelaerr/eduvpn-client
    $ yum install eduvpn-client

More information is available at `fedora copr <https://copr.fedorainfracloud.org/coprs/gijzelaerr/eduvpn-client/>`_.


Pip
---

You can install the client API from pypi:

.. code-block:: bash

    $ pip install eduvpn


Or if you want to try out the bleading edge development version:

.. code-block:: bash

    $ pip install git+https://github.com/eduvpn/python-eduvpn.git

You can install the dependencies for the user interface:

.. code-block:: bash

    $ pip install -e ".[gui]"

If you use eduVPN this way you need to make sure all non-Python dependies are installed. For Debian or Ubuntu:

.. code-block:: bash

    $ apt install gir1.2-gtk-3.0 gir1.2-notify-0.7 libdbus-1-dev libnotify4 python3-dateutil \
        python3-dbus python3-nacl python3-requests-oauthlib python3-gi network-manager-openvpn \
        python3-pip git

For fedora:

.. code-block:: bash

    $ dnf install -y gtk3 libnotify python3-dateutil python3-networkmanager python3-pydbus \
        python3-pynacl python3-requests-oauthlib python3-gobject python3-pip \
        python3-future git NetworkManager-openvpn NetworkManager-openvpn-gnome

Issues
======

If you experience any issues you could and should report them at our
`issue tracker <https://github.com/eduvpn/python-eduvpn-client/issues>`_. Please don't forget to mention your OS,
method of installation, eduVPN client version and instructions on how to reproduce the problem. If you have a problem
enabling your VPN connection please also examine the `journalctl -u NetworkManager` logs.

Source code
-----------

Development of this project takes place on `github <https://github.com/eduvpn/python-eduvpn-client>`_.  You
can find the source code and all releases there.

Contributing
============

Contributions are more than welcome! If you experience any problems let us know in the bug tracker. We accept patches
in the form of github pull requests. Please make sure your code works with python3 and is pep8 compatible.
Also make sure the test suite actually passes all tests. 
