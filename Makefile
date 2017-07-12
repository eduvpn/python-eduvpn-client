
.PHONEY: deb  notebook-dev notebook-vent

deb:
	sudo apt install -y python-networkmanager network-manager-openvpn-gnome python-dbus dev jupyter-notebook python-nacl

.virtualenv/:
	virtualenv -p python2 .virtualenv
	.virtualenv/bin/pip install -r requirements.txt

notebook-venv: .virtualenv
	.virtualenv/bin/jupyter notebook


notebook-deb: debs
	/usr/bin/jupyter-notebook
