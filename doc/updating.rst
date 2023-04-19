============
Updating
============

Depending on the client that you want to update from, there might be some manual steps required before/after installing.

For most version updates you can simply do an update with your package manager.

Additional instructions when coming from 3.x
--------------------------------------------

When upgrading from version 3 to the newest version (currently 4.x), there are some manual steps needed for updating. The main part is that we have moved to a new repository for this major version update. We will go over the distro specific update instructions (distros that are not listed here do not need specific instructions, go to `Installation <./installation.html>`_).

Before you continue, it might be wise to close the client if you have it open. Note that once the new client is installed, you will have to add your servers again.


Debian and Ubuntu (both x86_64)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First we must remove the old files, repository and associated signing keys:

.. code-block:: console

    $ rm -r ~/.config/eduvpn
    $ sudo rm /etc/apt/sources.list.d/eduvpn.list
    $ sudo rm /etc/apt/trusted.gpg.d/eduvpn-client.gpg
    $ sudo rm /usr/share/keyrings/eduvpn.gpg
    $ sudo apt-key del 9BF9BF69E5DDE77F5ABE20DC966A924CE91888D2

It's fine if you get errors that some of these entries don't exist.


You can then continue installing the new client by adding the new repository if you have Ubuntu >= 22.04 or Debian 11:

.. code-block:: console

    $ sudo apt install apt-transport-https lsb-release wget
    $ wget -O- https://app.eduvpn.org/linux/v4/deb/app+linux@eduvpn.org.asc | gpg --dearmor | sudo tee /usr/share/keyrings/eduvpn-v4.gpg >/dev/null
    $ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/eduvpn-v4.gpg] https://app.eduvpn.org/linux/v4/deb/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/eduvpn-v4.list
    $ sudo apt update
    $ sudo apt upgrade

For other Debian based distros, you can use Pip . If you do the upgrade via Pip, remove the old client first with:

.. code-block:: console

    $ sudo apt purge eduvpn-client
    $ sudo apt autoremove

Then install via Pip, see `Pip Installation <./installation.html#pip-installation>`_

Fedora (36 & 37, both x86_64)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First we must remove the old files, repository and associated signing keys:

.. code-block:: console

    $ rm -r ~/.config/eduvpn
    $ sudo dnf copr remove @eduvpn/eduvpn-client

You can then continue installing the new client by adding the new repository:

.. code-block:: console

    $ curl -O https://app.eduvpn.org/linux/v4/rpm/app+linux@eduvpn.org.asc
    $ sudo rpm --import app+linux@eduvpn.org.asc
    $ cat << 'EOF' | sudo tee /etc/yum.repos.d/python-eduvpn-client_v4.repo
    [python-eduvpn-client_v4]
    name=eduVPN for Linux 4.x (Fedora $releasever)
    baseurl=https://app.eduvpn.org/linux/v4/rpm/fedora-$releasever-$basearch
    gpgcheck=1
    EOF
    $ sudo dnf --refresh update
