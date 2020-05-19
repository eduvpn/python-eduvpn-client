#
## note: this file is intended for development only and not to actually
#       install the client.
#

.PHONY: all dockers


all: venv/bin/eduvpn
	venv/bin/eduvpn

venv/bin/pip:
	python3 -m venv venv


venv/bin/eduvpn: venv/bin/pip
	venv/bin/pip install -e .

dockers:
	for i in `ls docker/*.docker`; do echo "*** $$i"; docker build . -f $$i; done
