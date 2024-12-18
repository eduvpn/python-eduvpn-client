# note: this file is intended for development only and not to actually
#       install the client.
#

.PHONY: venv deb dnf mypy fmt lint clean build sloc

VENV=./venv
RUFF := $(shell command -v ruff 2> /dev/null)
ifeq ("$(wildcard $(RUFF))","")
	RUFF = $(shell echo "${PWD}/venv/bin/ruff")
endif
MYPY := $(shell command -v mypy 2> /dev/null)
ifeq ("$(wildcard $(MYPY))","")
	MYPY = $(shell echo "${PWD}/venv/bin/mypy")
endif

venv:
	python3 -m venv venv
	$(VENV)/bin/pip install --upgrade pip build


# install all required binary packages on a debian based system
deb:
	apt update
	apt install -y \
		gir1.2-nm-1.0 \
		gir1.2-secret-1 \
		gir1.2-gtk-3.0 \
		gir1.2-notify-0.7 \
		libcairo2-dev \
		libgirepository1.0-dev \
		python3-dev \
		python3-gi \
		python3-setuptools \
		python3-pytest \
		python3-wheel \
		network-manager-openvpn-gnome

# install all required binary packages on a rpm based system
dnf:
	dnf install -y \
		libnotify \
		libsecret \
		gtk3 \
		python3-gobject \
		python3-pytest \
		python3-cairo-devel \
		gobject-introspection-devel \
		cairo-gobject-devel

install-mypy: venv
	PYGOBJECT_STUB_CONFIG=Gtk3,Gdk3 $(VENV)/bin/pip install ".[mypy]" --no-cache-dir

mypy:
ifeq ("$(wildcard $(MYPY))","")
	@echo "mypy does not exist, install it with make install-mypy (will use pip) or consult your distribution manual. Note that you also need PyGObject-stubs and types-setuptools. If you don't have eduvpn-common yet you can also use make install-eduvpn-common from the test pypi"
	exit 1
endif
	$(MYPY) eduvpn tests

install-lint: venv
	$(VENV)/bin/pip install ".[lint]"

fmt:
ifeq ("$(wildcard $(RUFF))","")
	@echo "ruff does not exist for formatting, install it with make install-lint (will use pip) or consult your distribution manual"
	exit 1
endif
	$(RUFF) format eduvpn tests

lint:
ifeq ("$(wildcard $(RUFF))","")
	@echo "ruff does not exist for linting, install it with make install-lint (will use pip) or consult your distribution manual"
	exit 1
endif
# check linting
	$(RUFF) check eduvpn tests
# check formatting
	$(RUFF) format --check eduvpn tests

install-test: venv
	$(VENV)/bin/pip install ".[test]"

test: install-test
	$(VENV)/bin/python3 -m pytest tests

install-eduvpn-common: venv
	$(VENV)/bin/pip install --index-url "https://test.pypi.org/simple/" eduvpn-common

clean:
	rm -rf $(VENV) build dist .eggs eduvpn_client.egg-info .pytest_cache tests/__pycache__/
	find  . -name *.pyc -delete
	find  . -name __pycache__ -delete

build: venv
	rm -rf build
	rm -rf dist
	$(VENV)/bin/pip install build
	$(VENV)/bin/python3 -m build --sdist --wheel .

sloc:
	tokei -t=Python eduvpn || cloc --include-ext=py eduvpn
