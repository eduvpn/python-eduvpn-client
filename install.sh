#!/bin/sh

set -e

ARCH="$(uname -m)"

if [ ! "$ARCH" = "x86_64" ] && [ ! "$ARCH" = "amd64" ]; then
    printf "Your architecture: %s, is not supported.
Your architecture might, however, be supported by the Pip package. You may try the following instructions: https://docs.eduvpn.org/client/linux/installation.html#pip-installation" "$ARCH"
    exit 1
fi

. "/etc/os-release"

install_deb() {
    set -x
    sudo apt-get update
    # Make sure https apt transport is possible and curl is available
    # curl might not be available if the script is downloaded manually
    sudo apt-get install apt-transport-https curl
    curl -sSf https://app.eduvpn.org/linux/v4/deb/app+linux@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4.gpg >/dev/null
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4.gpg] https://app.eduvpn.org/linux/v4/deb/ $1 main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4.list
    sudo apt-get update
    sudo apt-get install eduvpn-client
    exit 0
}

install_fedora() {
    set -x
    curl -O https://app.eduvpn.org/linux/v4/rpm/app+linux@eduvpn.org.asc
    sudo rpm --import app+linux@eduvpn.org.asc
    cat << 'EOF' | sudo tee /etc/yum.repos.d/python-eduvpn-client_v4.repo
[python-eduvpn-client_v4]
name=eduVPN for Linux 4.x (Fedora $releasever)
baseurl=https://app.eduvpn.org/linux/v4/rpm/fedora-$releasever-$basearch
gpgcheck=1
EOF
    sudo dnf install eduvpn-client
    exit 0
}

install_centos() {
    if [ "$VERSION" != "9" ]; then
	echo "CentOS Stream $VERSION is not supported"
	exit 1
    fi
    set -x
    curl -O https://app.eduvpn.org/linux/v4/rpm/app+linux@eduvpn.org.asc
    sudo rpm --import app+linux@eduvpn.org.asc
    cat << 'EOF' | sudo tee /etc/yum.repos.d/python-eduvpn-client_v4.repo
[python-eduvpn-client_v4]
name=eduVPN for Linux 4.x (CentOS Stream 9)
baseurl=https://app.eduvpn.org/linux/v4/rpm/centos-stream+epel-next-9-$basearch
gpgcheck=1
EOF
    sudo dnf install eduvpn-client
    exit 0
}

case $VERSION_CODENAME in
    # ubuntu versions
    "focal" | "jammy" | "mantic" | "noble" | "bullseye" | "bookworm")
	install_deb "$VERSION_CODENAME"
	;;
    # For linux mint we need to do some redirections to ubuntu codenames
    # See https://linuxmint.com/download_all.php
    # redirect linux mint 20.x codenames to focal
    "ulyana" | "ulyssa" | "uma" | "una")
	install_deb "focal"
	;;
    # redirect linux mint 21.x codenames to jammy
    "vanessa" | "vera" | "victoria")
	install_deb "jammy"
	;;
esac

# No codename or unsupported codename, get based on name
case $NAME in
    "Fedora Linux")
	install_fedora
	;;
    "CentOS Stream")
	install_centos
	;;
    *)
	echo "OS: \"$NAME\" with codename \"$VERSION_CODENAME\" is not supported"
	exit 1
	;;
esac
