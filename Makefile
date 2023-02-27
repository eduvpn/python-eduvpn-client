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
	for i in `ls docker/*.docker`; do echo "*** $$i"; docker build --progress=plain . -f $$i; done

# install all required binary packages on a debian based system
deb:
	apt update
	apt install -y \
		gir1.2-nm-1.0 \
		gir1.2-secret-1 \
		gir1.2-gtk-3.0 \
		gir1.2-notify-0.7 \
		libdbus-glib-1-dev \
		python3-gi \
		python3-setuptools \
		python3-pytest \
		python3-wheel \
		python3-dbus \
		network-manager-openvpn-gnome

# install all required binary packages on a rpm based system
dnf:
	sudo dnf install -y \
		libnotify \
		libsecret \
		gtk3 \
		python3-dbus \
		python3-gobject \
		python3-pytest \
		python3-cairo-devel \
		gobject-introspection-devel \
		cairo-gobject-devel \
		dbus-python-devel

doc:  $(VENV)/
	$(VENV)/bin/pip install -r doc/requirements.txt
	$(VENV)/bin/python -msphinx doc doc/_build

srpm-fedora:
	rm -f dist/*.src.rpm
	docker build --progress=plain -t rpm_fedora_37 -f docker/rpm_fedora_37.docker .
	mkdir -p dist
	docker run -v `pwd`/dist:/dist:rw rpm_fedora_37 sh -c "cp /root/rpmbuild/SRPMS/* /dist"

rpm-fedora:
	docker build --progress=plain -t rpm_fedora_37 -f docker/rpm_fedora_37.docker .
	mkdir -p dist
	docker run -v `pwd`/dist:/dist:rw rpm_fedora_37 sh -c "cp /root/rpmbuild/RPMS/noarch/* /dist"

rpm-centos:
	docker build --progress=plain -t rpm_centos_stream8 -f docker/rpm_centos_stream8.docker .
	mkdir -p dist
	docker run -v `pwd`/dist:/dist:rw rpm_centos_stream8 sh -c "cp /root/rpmbuild/RPMS/noarch/* /dist"

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

clean:
	rm -rf $(VENV) dist .eggs eduvpn_client.egg-info .pytest_cache tests/__pycache__/
	find  . -name *.pyc -delete
	find  . -name __pycache__ -delete

sdist: $(VENV)
	rm -f dist/*.tar.gz
	$(VENV)/bin/python setup.py sdist

bdist_wheel: $(VENV)
	rm -f dist/*.whl
	$(VENV)/bin/python setup.py bdist_wheel

rpmbuild: sdist
	mkdir -p ~/rpmbuild/SOURCES/.
	cp dist/*.tar.gz ~/rpmbuild/SOURCES/.
	rpmbuild -bs eduvpn.spec
	rpmbuild -bb eduvpn.spec
$(VENV)/bin/twine: $(VENV)
	$(VENV)/bin/pip install twine


twine-upload: sdist bdist_wheel $(VENV)/bin/twine
	$(VENV)/bin/twine upload dist/*.tar.gz dist/*.whl
