# Installation

The Desktop client only works on Linux. It is recommended to use a Deb
or RPM package to install the eduVPN client. You can also install
using Pip from PyPi or directly from GitHub. We distribute RPM
packages for Fedora, and Deb packages for Debian and Ubuntu.

> **Note**
> If your target is not supported you can make an issue on the
> [GitHub repository](https://github.com/eduvpn/python-eduvpn-client) and we will see
> if we can provide it. Right now, for RPM and DEB, we only provide x86_64 packages (we use a compiled dependency).
> If you want to install the client on ARM64, use the [Pip installation](#pip-installation) method.
>
> For pre-release instructions see [Pre-releases](./prerelease.md)

## Installation using a script

> **Note**
> This needs Curl installed, `sudo apt update && sudo apt install curl` on Debian/Ubuntu systems.
> Fedora systems automatically have Curl installed

We provide a script to ease the installation. This script works on the platforms we have official packages for: Debian/Ubuntu/Fedora/CentOS

```console
$ curl --proto '=https' --tlsv1.2 https://docs.eduvpn.org/client/linux/install.sh -O
$ bash ./install.sh
```

## Manual installation

For manual installation without using the script, pick the right section for
the Linux distribution that you are using. Note that these instructions assume
you are using Bash as your shell.

### Debian 11

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4/deb/app+linux@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4.gpg] https://app.eduvpn.org/linux/v4/deb/ bullseye main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4.list
$ sudo apt update
$ sudo apt install eduvpn-client
```

### Debian 12

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4/deb/app+linux@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4.gpg] https://app.eduvpn.org/linux/v4/deb/ bookworm main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4.list
$ sudo apt update
$ sudo apt install eduvpn-client
```

### Ubuntu 20.04

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4/deb/app+linux@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4.gpg] https://app.eduvpn.org/linux/v4/deb/ focal main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4.list
$ sudo apt update
$ sudo apt install eduvpn-client
```

### Ubuntu 22.04

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4/deb/app+linux@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4.gpg] https://app.eduvpn.org/linux/v4/deb/ jammy main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4.list
$ sudo apt update
$ sudo apt install eduvpn-client
```

### Ubuntu 23.10

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4/deb/app+linux@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4.gpg] https://app.eduvpn.org/linux/v4/deb/ mantic main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4.list
$ sudo apt update
$ sudo apt install eduvpn-client
```

### Ubuntu 24.04

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4/deb/app+linux@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4.gpg] https://app.eduvpn.org/linux/v4/deb/ noble main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4.list
$ sudo apt update
$ sudo apt install eduvpn-client
```

### Linux Mint 20.x

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4/deb/app+linux@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4.gpg] https://app.eduvpn.org/linux/v4/deb/ focal main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4.list
$ sudo apt update
$ sudo apt install eduvpn-client
```

### Linux Mint 21.x

``` console
$ sudo apt update
$ sudo apt install apt-transport-https wget
$ wget -O- https://app.eduvpn.org/linux/v4/deb/app+linux@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4.gpg >/dev/null
$ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4.gpg] https://app.eduvpn.org/linux/v4/deb/ jammy main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4.list
$ sudo apt update
$ sudo apt install eduvpn-client
```

### Fedora (39 & 40)

``` console
$ curl -O https://app.eduvpn.org/linux/v4/rpm/app+linux@eduvpn.org.asc
$ sudo rpm --import app+linux@eduvpn.org.asc
$ cat << 'EOF' | sudo tee /etc/yum.repos.d/python-eduvpn-client_v4.repo
[python-eduvpn-client_v4]
name=eduVPN for Linux 4.x (Fedora $releasever)
baseurl=https://app.eduvpn.org/linux/v4/rpm/fedora-$releasever-$basearch
gpgcheck=1
EOF
$ sudo dnf install eduvpn-client
```

### CentOS (Stream 9)

``` console
$ curl -O https://app.eduvpn.org/linux/v4/rpm/app+linux@eduvpn.org.asc
$ sudo rpm --import app+linux@eduvpn.org.asc
$ cat << 'EOF' | sudo tee /etc/yum.repos.d/python-eduvpn-client_v4.repo
[python-eduvpn-client_v4]
name=eduVPN for Linux 4.x (CentOS Stream 9)
baseurl=https://app.eduvpn.org/linux/v4/rpm/centos-stream+epel-next-9-$basearch
gpgcheck=1
EOF
$ sudo dnf install eduvpn-client
```

### NixOS

The Linux client currently is in the NixOS unstable channel. If you are running the stable channel you need to wait for NixOS 24.05 to release or import it from the unstable channel in your configuration.

The package name is `eduvpn-client` so you can just do:

```
nix-env -iA nixpkgs.eduvpn-client
```

or using the new Nix command (if you have it enabled with flakes)
```
nix run nixpkgs#eduvpn-client
```

The client needs NetworkManager, so make sure `networking.networkmanager.enable = true;` is set in your `configuration.nix`.

Of course, you can also just add the `eduvpn-client` package to your `configuration.nix` or `home.nix` (in case you're using [home-manager](https://github.com/nix-community/home-manager)).

Note that on NixOS the firewall can be pretty strict, see [The NixOS Wiki](https://wiki.nixos.org/wiki/WireGuard#Setting_up_WireGuard_with_NetworkManager) on how to allow WireGuard connections. OpenVPN should work out of the box.

### Arch (Unofficial)

There is an unofficial package in the [Arch User Repository
(AUR)](https://aur.archlinux.org/packages/python-eduvpn-client/). Make sure to first import the gpg signing key:

```console
$ curl https://app.eduvpn.org/linux/v4/deb/app+linux@eduvpn.org.asc | gpg --import -
```

Then build and install using your preferred AUR helper, e.g. `pamac`:

```console
$ pamac build python-eduvpn-client
```

or `yay`:

```console
$ yay -S python-eduvpn-client
```

### Pip installation

We also provide Pip packages. These are useful if your distro is not
officially supported in our packaging (yet).

#### Dependencies

To manually install the eduVPN package via Pip you first need to satisfy
the dependencies.

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

#### Pip commands

> **Note**
> If the Pip installation fails due to "error: externally-managed-environment",
> we recommend you to try to install the package with [Pipx](https://github.com/pypa/pipx) instead

You can then continue with installing via Pip:

``` console
$ pip install "eduvpn-client[gui]"
```
