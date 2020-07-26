# note: this file is intended for development only and not to actually
#       install the client.
#

.PHONY: all dockers

VENV=./venv


all: run

$(VENV)/:
	python3 -m venv venv
	venv/bin/pip install --upgrade pip wheel

gui: $(VENV)/bin/eduvpn-gui
	venv/bin/eduvpn-gui

$(VENV)/bin/eduvpn-gui: $(VENV)/
	venv/bin/pip install -e ".[test,gui]"

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
		python3-pytest \
		python3-wheel \
		python3-dbus

# install all required binary packages on a debian based system
debdev: deb
	apt update
	apt install -y \
		git \
		python3-venv \
		pkg-config \
		libcairo2-dev \
		libpython3-dev \
		gobject-introspection \
		libgirepository1.0-dev \
		network-manager-openvpn-gnome \
		libdbus-1-dev

# install all required binary packages on a rpm based system
dnf:
	sudo dnf install -y \
		libnotify \
		gtk3 \
		python3-dbus \
		python3-requests-oauthlib \
		python3-gobject \
		python3-pynacl \
		python3-pytest \
		python3-cairo-devel \
		gobject-introspection-devel \
		cairo-gobject-devel \
		dbus-python-devel

doc:  $(VENV)/
	$(VENV)/bin/pip install -r doc/requirements.txt
	$(VENV)/bin/python -msphinx doc doc/_build

$(VENV)/bin/pytest:
	$(VENV)/bin/pip install pytest

test: $(VENV)/bin/pytest
	$(VENV)/bin/pytest

run: $(VENV)/bin/eduvpn-gui
	$(VENV)/bin/eduvpn-client interactive

srpm:
	docker build -t rpm_centos_8 -f docker/rpm_centos_8.docker .
	docker build -t rpm_fedora_32 -f docker/rpm_fedora_32.docker .
	mkdir dist || true
	docker run -v `pwd`/dist:/dist:rw rpm_centos_8 sh -c "cp /root/rpmbuild/SRPMS/* /dist"
	docker run -v `pwd`/dist:/dist:rw rpm_fedora_32 sh -c "cp /root/rpmbuild/SRPMS/* /dist"

$(VENV)/bin/mypy: $(VENV)/
	$(VENV)/bin/pip install mypy

mypy: $(VENV)/bin/mypy
	$(VENV)/bin/mypy --config-file setup.cfg eduvpn tests

$(VENV)/bin/pycodestyle: $(VENV)/
	$(VENV)/bin/pip install pycodestyle

pycodestyle: $(VENV)/bin/pycodestyle
	$(VENV)/bin/pycodestyle eduvpn tests
	
$(VENV)/bin/jupyter-notebook: $(VENV)/bin/eduvpn-gui
	$(VENV)/bin/pip install -r notebooks/requirements.txt

notebook: $(VENV)/bin/jupyter-notebook
	$(VENV)/bin/jupyter-notebook --notebook-dir= notebooks/
