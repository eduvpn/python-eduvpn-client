============
Introduction
============

This is the GNU/Linux desktop client and Python API for eduVPN. The Desktop client only works on Linux, but most parts
of the API are usable on other platforms also. For the API Python 2.7, 3.4+ and pypy are supported.

Installation
============

It is recommended to use a package to install the eduVPN client. We currently support various Fedora, Debian and Ubuntu
versions.

Debian and Ubuntu
-----------------

You can install the latest release on Debian or Ubuntu using the eduVPN packaging repository by running these commands
as root or using sudo::

    - apt install apt-transport-https curl
    - curl -L https://repo.eduvpn.org/debian/eduvpn.key | apt-key add -
    - echo "deb https://repo.eduvpn.org/debian/ stretch main" > /etc/apt/sources.list.d/eduvpn.list
    - apt update
    - apt install eduvpn-client

This has been tested on Ubuntu 17.04 (Zesty) and Debian 9 (stretch). Unfortunatly Ubuntu 16.04 LTS  (Xenial) is **not**
supported. Ubuntu Xenial and older are bundled with an outdated and unsupporten OpenVPN.

Fedora
------

You can install the latest release of the eduVPN client on Fedora by running these commands as root or using sudo::

    - dnf install dnf-plugins-core
    - dnf copr enable gijzelaerr/eduvpn-client
    - dnf install eduvpn-client

More information is available at `fedora copr <https://copr.fedorainfracloud.org/coprs/gijzelaerr/eduvpn-client/>`_.


Pip
---

You can install the client API from pypi::

    $ pip install python-eduvpn-client


Or directly from a source checkout in the project root folder::


    $ pip install -e .

You can install the dependencies for the user interface::

    $ pip install -e ".[client]"


Note that the project depends on the ``python-gi`` package, which for now doesn't properly install in a virtualenv.
If you do install ``python-eduvpn-client`` in a virtualenv it is recommended you create the virtualenv using the
``--system-site-packages`` flag and install the python-gi package using your operating system package manager. Read
more about this on the `pygobject website <https://pygobject.readthedocs.io/>`_.

Issues
======

If you experience any issues you could and should report them at our
`issue tracker <https://github.com/eduvpn/python-eduvpn-client/issues>`_. Please don't forget to mention your OS,
method of installation, eduVPN client version and problem reproduction instructions.

Source code
-----------

Development of this project takes place on `github <https://github.com/gijzelaerr/python-eduvpn-client>`_.  You
can find the source code and all releases there.

Contributing
============

Contributions are more than welcome! If you experience any problems let us know in the bug tracker. We accept patches
in the form of github pull requests. Please make sure your code works with python 2 and python3, and is pep8 compatible.
Also make sure the test suit actually passes all tests. 
