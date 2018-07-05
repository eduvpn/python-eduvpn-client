
Linux eduVPN client and Python API
==================================

This is the GNU/Linux desktop client for eduVPN. It also is a Python client API.

Read more about eduVPN on the eduVPN website http://eduvpn.org/.

Installation
============

Read the installation instructions [here](http://python-eduvpn-client.readthedocs.io/en/latest/introduction.html#installation).

## From Git
$ sudo apt install -y gir1.2-gtk-3.0 gir1.2-notify-0.7 libdbus-1-dev libnotify4 python-gi python-dbus python-nacl python-requests-oauthlib python-configparser python-future python-dateutil python-mock python-pytest python3-dateutil python3-dbus python3-nacl python3-requests-oauthlib python3-gi network-manager-openvpn git python3-pip

    $ pip3 install --user --upgrade git+https://github.com/eduvpn/python-eduvpn-client.git
    $ ~/.local/bin/eduvpn-client

It may give errors about missing dependencies, you can install them using `dnf` 
or `apt`.

Documentation
=============

You can find the documentation on [http://python-eduvpn-client.readthedocs.io](http://python-eduvpn-client.readthedocs.io).

Development
===========

[![Build Status](https://travis-ci.org/eduvpn/python-eduvpn-client.svg?branch=master)](https://travis-ci.org/eduvpn/python-eduvpn-client)
