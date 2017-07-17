
.PHONEY: deb fedora

deb:
	sudo apt install -y \
		python-networkmanager \
		network-manager-openvpn-gnome \
		python-dbus \
		python-nacl \
		python-requests-oauthlib

fedora:
	sudo install \
		python2 \
		python2-requests-oauthlib \
		python2-networkmanager \
		python2-pynacl

.virtualenv/:
	virtualenv -p python2 .virtualenv
	.virtualenv/bin/pip install -e .

