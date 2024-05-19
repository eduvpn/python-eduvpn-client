# Pre-release Installation

Sometimes we might ask you to test a development/pre-release release. This is the instruction on how to get this pre-release.

It is always helpful to have as many testers as we can, so if you want to run a pre-release without us asking, you are welcome to do so. But do note that bugs may occur.

### Debian 11

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4-dev/deb/app+linux+dev@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4-dev.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4-dev.gpg] https://app.eduvpn.org/linux/v4-dev/deb/ bullseye main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4-dev.list
$ sudo apt update
$ sudo apt install eduvpn-client
$ sudo apt upgrade
```

### Debian 12

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4-dev/deb/app+linux+dev@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4-dev.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4-dev.gpg] https://app.eduvpn.org/linux/v4-dev/deb/ bookworm main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4-dev.list
$ sudo apt update
$ sudo apt install eduvpn-client
$ sudo apt upgrade
```

### Ubuntu 20.04

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4-dev/deb/app+linux+dev@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4-dev.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4-dev.gpg] https://app.eduvpn.org/linux/v4-dev/deb/ focal main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4-dev.list
$ sudo apt update
$ sudo apt install eduvpn-client
$ sudo apt upgrade
```

### Ubuntu 22.04

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4-dev/deb/app+linux+dev@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4-dev.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4-dev.gpg] https://app.eduvpn.org/linux/v4-dev/deb/ jammy main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4-dev.list
$ sudo apt update
$ sudo apt install eduvpn-client
$ sudo apt upgrade
```

### Ubuntu 23.10

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4-dev/deb/app+linux+dev@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4-dev.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4-dev.gpg] https://app.eduvpn.org/linux/v4-dev/deb/ mantic main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4-dev.list
$ sudo apt update
$ sudo apt install eduvpn-client
$ sudo apt upgrade
```

### Ubuntu 24.04

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4-dev/deb/app+linux+dev@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4-dev.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4-dev.gpg] https://app.eduvpn.org/linux/v4-dev/deb/ noble main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4-dev.list
$ sudo apt update
$ sudo apt install eduvpn-client
$ sudo apt upgrade
```

### Linux Mint 20.x

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4-dev/deb/app+linux+dev@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4-dev.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4-dev.gpg] https://app.eduvpn.org/linux/v4-dev/deb/ focal main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4-dev.list
$ sudo apt update
$ sudo apt install eduvpn-client
$ sudo apt upgrade
```

### Linux Mint 21.x

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4-dev/deb/app+linux+dev@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4-dev.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4-dev.gpg] https://app.eduvpn.org/linux/v4-dev/deb/ jammy main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4-dev.list
$ sudo apt update
$ sudo apt install eduvpn-client
$ sudo apt upgrade
```

### Fedora (39 & 40)

``` console
$ curl -O https://app.eduvpn.org/linux/v4-dev/rpm/app+linux+dev@eduvpn.org.asc
$ sudo rpm --import app+linux+dev@eduvpn.org.asc
$ cat << 'EOF' | sudo tee /etc/yum.repos.d/python-eduvpn-client_v4-dev.repo
[python-eduvpn-client_v4-dev]
name=eduVPN for Linux 4.x Pre-releases (Fedora $releasever)
baseurl=https://app.eduvpn.org/linux/v4-dev/rpm/fedora-$releasever-$basearch
gpgcheck=1
EOF
$ sudo dnf install eduvpn-client
$ sudo dnf upgrade
```

### CentOS (Stream 9)

``` console
$ curl -O https://app.eduvpn.org/linux/v4-dev/rpm/app+linux+dev@eduvpn.org.asc
$ sudo rpm --import app+linux+dev@eduvpn.org.asc
$ cat << 'EOF' | sudo tee /etc/yum.repos.d/python-eduvpn-client_v4-dev.repo
[python-eduvpn-client_v4-dev]
name=eduVPN for Linux 4.x Pre-releases (CentOS Stream 9)
baseurl=https://app.eduvpn.org/linux/v4-dev/rpm/centos-stream+epel-next-9-$basearch
gpgcheck=1
EOF
$ sudo dnf install eduvpn-client
$ sudo dnf upgrade
```

### Pip
Install the dependencies as normal

For Debian or Ubuntu:

``` console
$ sudo apt update
$ sudo apt install \
    gir1.2-nm-1.0 \
    gir1.2-secret-1 \
    gir1.2-gtk-3.0 \
    gir1.2-notify-0.7 \
    libgirepository1.0-dev \
    python3-gi \
    python3-setuptools \
    python3-pytest \
    python3-wheel \
    network-manager-openvpn-gnome
```

For Fedora:

``` console
$ sudo dnf install \
    libnotify \
    libsecret \
    gtk3 \
    python3-gobject \
    python3-pytest \
    python3-cairo-devel \
    gobject-introspection-devel \
    cairo-gobject-devel
```

For openSUSE Tumbleweed:
```console
$ sudo zypper install \
    libnotify \
    libsecret \
    gtk3 \
    python3-gobject \
    python3-pytest \
    python3-cairo-devel \
    gobject-introspection-devel \
	typelib-1_0-Notify-0_7 \
    typelib-1_0-Secret-1 \
    typelib-1_0-Gtk-3_0
```

Then install using pipx/pip using the testpypi:

```console
$ pip install --index-url https://test.pypi.org/simple/ "eduvpn-client[gui]"
```
