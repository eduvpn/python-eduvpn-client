#!/bin/bash -ve

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get upgrade -y 

apt-get install -y python-pip python-setuptools network-manager-openvpn-gnome python-dbus python-nacl python-requests-oauthlib python-gi python-sphinx-rtd-theme python-sphinx python-mock python-pytest python-gi python-dbus gir1.2-gtk-3.0 gir1.2-notify-0.7 network-manager-openvpn network-manager-openvpn-gnome

pip install -e /vagrant
