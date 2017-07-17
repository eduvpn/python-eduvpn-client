
.PHONEY: deb  notebook-dev notebook-venv

deb:
	sudo apt install -y \
		python-networkmanager \
		network-manager-openvpn-gnome \
		python-dbus \
		jupyter-notebook \
		python-nacl \
		python-requests-oauthlib

.virtualenv/:
	virtualenv -p python2 .virtualenv
	.virtualenv/bin/pip install -r requirements.txt

notebook-venv: .virtualenv
	.virtualenv/bin/jupyter notebook


notebook-deb: debs
	/usr/bin/jupyter-notebook
