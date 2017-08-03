
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
