
.PHONEY: debs dev notebook

debs:
	sudo apt install -y python-networkmanager network-manager-openvpn-gnome python-dbus

dev:
	sudo apt install -y jupyter-notebook


notebook: dev debs
	/usr/bin/jupyter-notebook
