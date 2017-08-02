
.PHONY: deb fedora doc

deb:
	sudo apt install -y \
		python-networkmanager \
		network-manager-openvpn-gnome \
		python-dbus \
		python-nacl \
		python-requests-oauthlib \
		python-gi

fedora:
	sudo install \
		python2 \
		python2-requests-oauthlib \
		python2-networkmanager \
		python2-pynacl

.virtualenv/:
	virtualenv --system-site-packages -p python2 .virtualenv
	.virtualenv/bin/pip install -e .

.virtualenv3/:
	virtualenv --system-site-packages -p python3 .virtualenv3
	.virtualenv3/bin/pip install -e .

doc: 
	.virtualenv/bin/pip install -r doc/requirements.txt
	.virtualenv/bin/python -msphinx doc doc/_build
