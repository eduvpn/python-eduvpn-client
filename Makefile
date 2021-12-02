# note: this file is intended for development only and not to actually
#       install the client.
#

.PHONY: all dockers doc

VENV=./venv


all: eduvpn-cli

$(VENV)/:
	python3 -m venv venv --system-site-packages
	$(VENV)/bin/pip install --upgrade pip wheel pytest

$(VENV)/bin/eduvpn-cli: $(VENV)/
	$(VENV)/bin/pip install -e ".[test]"

$(VENV)/bin/eduvpn-gui: $(VENV)/
	$(VENV)/bin/pip install -e ".[test,gui]"

eduvpn-gui: $(VENV)/bin/eduvpn-gui
	$(VENV)/bin/eduvpn-gui

letsconnect-gui: $(VENV)/bin/eduvpn-gui
	venv/bin/letsconnect-gui

eduvpn-cli: $(VENV)/bin/eduvpn-cli
	$(VENV)/bin/eduvpn-cli interactive

dockers:
	for i in `ls docker/*.docker`; do echo "*** $$i"; docker build . -f $$i; done

# install all required binary packages on a debian based system
deb:
	apt update
	apt install -y \
		gir1.2-gtk-3.0 \
		gir1.2-notify-0.7 \
		libdbus-glib-1-dev \
		python3-gi \
		python3-requests-oauthlib \
		python3-cryptography \
		python3-setuptools \
		python3-nacl \
		python3-pytest \
		python3-wheel \
		python3-dbus \
		network-manager-openvpn-gnome

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

# install required binary packages when running GUI on OSX
osx:
	brew install gobject-introspection cairo # py3cairo pygobject3

doc:  $(VENV)/
	$(VENV)/bin/pip install -r doc/requirements.txt
	$(VENV)/bin/python -msphinx doc doc/_build

srpm:
	docker build -t rpm_centos_8 -f docker/rpm_centos_8.docker .
	docker build -t rpm_fedora_35 -f docker/rpm_fedora_35.docker .
	mkdir -p dist
	docker run -v `pwd`/dist:/dist:rw rpm_centos_8 sh -c "cp /root/rpmbuild/SRPMS/* /dist"
	docker run -v `pwd`/dist:/dist:rw rpm_fedora_35 sh -c "cp /root/rpmbuild/SRPMS/* /dist"

rpm:
	docker build -t rpm_centos_8 -f docker/rpm_centos_8.docker .
	docker build -t rpm_fedora_35 -f docker/rpm_fedora_35.docker .
	mkdir -p dist
	docker run -v `pwd`/dist:/dist:rw rpm_centos_8 sh -c "cp /root/rpmbuild/RPMS/noarch/* /dist"
	docker run -v `pwd`/dist:/dist:rw rpm_fedora_35 sh -c "cp /root/rpmbuild/RPMS/noarch/* /dist"


$(VENV)/bin/pycodestyle $(VENV)/bin/pytest: $(VENV)/
	$(VENV)/bin/pip install -e ".[test]"
	touch $(VENV)/bin/pytest
	touch $(VENV)/bin/pycodestyle

$(VENV)/bin/mypy: $(VENV)/
	$(VENV)/bin/pip install -e ".[mypy]"
	touch $(VENV)/bin/mypy

mypy: $(VENV)/bin/mypy
	$(VENV)/bin/mypy --config-file setup.cfg eduvpn tests

pycodestyle: $(VENV)/bin/pycodestyle
	$(VENV)/bin/pycodestyle eduvpn tests

test: $(VENV)/bin/pytest
	$(VENV)/bin/pytest
	
checks: test mypy pycodestyle

$(VENV)/bin/jupyter-notebook: $(VENV)/bin/eduvpn-gui
	$(VENV)/bin/pip install -r notebooks/requirements.txt
	touch $(VENV)/bin/jupyter-notebook

notebook: $(VENV)/bin/jupyter-notebook
	$(VENV)/bin/jupyter-notebook --notebook-dir= notebooks/

clean:
	rm -rf $(VENV) dist .eggs eduvpn_client.egg-info .pytest_cache tests/__pycache__/
	find  . -name *.pyc -delete
	find  . -name __pycache__ -delete

