#
# note: this file is intended for development only and not to actually
#       install the client.


.PHONY: deb fedora doc test test3 run dockers



# install all required binary packages on a debian based system
deb:
	apt update
	apt install -y \
		gir1.2-gtk-3.0 \
		gir1.2-notify-0.7 \
		libnotify4 \
		python-gi \
		python-dbus \
		python-nacl \
		python-requests-oauthlib \
		python-configparser \
		python-future \
		python-dateutil \
		python-mock \
		python-pytest \
		python3-dateutil \
		python3-dbus \
		python3-nacl \
		python3-requests-oauthlib \
		python3-gi 


# install all required binary packages on a rpm based system
fedora:
	sudo dnf install -y \
		gtk3 \
		libnotify \
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
		python2-dateutil \
		python3-dateutil \
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


.virtualenv/bin/eduvpn-client: .virtualenv/
	.virtualenv/bin/pip install -e ".[client]"


.virtualenv3/:
	virtualenv --system-site-packages -p python3 .virtualenv3


.virtualenv3/bin/eduvpn-client: .virtualenv3/
	.virtualenv3/bin/pip install -e ".[client]"


doc:  .virtualenv/
	.virtualenv/bin/pip install -r doc/requirements.txt
	.virtualenv/bin/python -msphinx doc doc/_build


test: .virtualenv/bin/eduvpn-client
	.virtualenv/bin/python setup.py test


test3: .virtualenv3/bin/eduvpn-client
	.virtualenv3/bin/python setup.py test


run: .virtualenv3/bin/eduvpn-client
	.virtualenv3/bin/eduvpn-client


dockers:
	for i in `ls docker/Dockerfile*`; do echo "*** $$i"; docker build . -f $$i; done

srpm:
	docker build -t srpm -f docker/Dockerfile.fedora_26_rpm .
	mkdir tmp || true
	docker run -v `pwd`/tmp:/tmp:rw srpm sh -c "cp /root/rpmbuild/SRPMS/* /tmp"

