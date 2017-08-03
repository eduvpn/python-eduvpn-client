
.PHONY: deb fedora doc

deb:
	sudo apt update
	sudo apt install -y \
		network-manager-openvpn-gnome \
		python-networkmanager \
		python-dbus \
		python-nacl \
		python-requests-oauthlib \
		python-gi \
		python3-dbus \
		python3-nacl \
		python3-requests-oauthlib \
		python3-gi \



fedora:
	sudo dnf install -y \
		python-gobject \
		python2-networkmanager \
		python2-pydbus \
		python2-pynacl \
		python2-requests-oauthlib \
		python2-pip \
		python2-configparser \
		python2-future \
		python2-nose \
		python2-mock \
		python2-virtualenv \
		python3-networkmanager \
		python3-pydbus \
		python3-pynacl \
		python3-requests-oauthlib \
		python3-gobject \
		python3-pip \
		python3-configparser \
		python3-future \
		python3-nose \
		python3-mock

.virtualenv/:
	virtualenv --system-site-packages -p python2 .virtualenv
	.virtualenv/bin/pip install -e .

.virtualenv3/:
	virtualenv --system-site-packages -p python3 .virtualenv3
	.virtualenv3/bin/pip install -e .

doc:  .virtualenv/
	.virtualenv/bin/pip install -r doc/requirements.txt
	.virtualenv/bin/python -msphinx doc doc/_build

test: .virtualenv/
	.virtualenv/bin/pip install -r tests/requirements.txt
	.virtualenv/bin/nosetests

test3: .virtualenv3/
	.virtualenv3/bin/pip install -r tests/requirements.txt
	.virtualenv3/bin/nosenosetests

dockers:
	for i in `ls docker/Dockerfile*`; do docker build . -f $$i; done
