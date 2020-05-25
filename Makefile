#
## note: this file is intended for development only and not to actually
#       install the client.
#

.PHONY: all dockers

VENV=$(CURDIR)/venv


all: $(VENV)/bin/eduvpn-client
	$(VENV)/bin/eduvpn-client

$(VENV)/bin/pip:
	python3 -m venv venv


$(VENV)/bin/eduvpn: $(VENV)/bin/pip
	venv/bin/pip install -e .

dockers:
	for i in `ls docker/*.docker`; do echo "*** $$i"; docker build . -f $$i; done

# install all required binary packages on a debian based system
deb:
	apt update
	apt install -y \
		gir1.2-gtk-3.0 \
		gir1.2-notify-0.7 \
		python3-gi \
		python3-requests-oauthlib \
		python3-cryptography \
		python3-setuptools \
		python3-nacl \
		python3-pytest


# install all required binary packages on a rpm based system
dnf:
	sudo dnf install -y \
		libnotify \
		gtk3 \
		python3-dbus \
		python3-requests-oauthlib \
		python3-gobject \
		python3-pynacl \
		python3-pytest



doc:  $(VENV)/bin/pip
	$(VENV)/bin/pip install -r doc/requirements.txt
	$(VENV)/bin/python -msphinx doc doc/_build

$(VENV)/bin/pytest:
	$(VENV)/bin/pip install pytest

test: $(VENV)/bin/pytest
	$(VENV)/bin/pytest

run: $(VENV)/bin/eduvpn-client
	$(VENV)/bin/eduvpn-client

srpm:
	docker build -t rpm_centos_8 -f docker/rpm_centos_8.docker .
	docker build -t rpm_fedora_32 -f docker/rpm_fedora_32.docker .
	mkdir dist || true
	docker run -v `pwd`/dist:/dist:rw rpm_centos_8 sh -c "cp /root/rpmbuild/SRPMS/* /dist"
	docker run -v `pwd`/dist:/dist:rw rpm_fedora_32 sh -c "cp /root/rpmbuild/SRPMS/* /dist"

$(VENV)/bin/mypy: $(VENV)/bin/pip
	$(VENV)/bin/pip install mypy

mypy: $(VENV)/bin/mypy
	$(VENV)/bin/mypy --ignore-missing-imports eduvpn tests
