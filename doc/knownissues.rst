============
Known issues
============

This chapter contains some known issues for the Linux client that are not possible or hacky to fix in the client itself

OpenVPN <= 2.5.7 and OpenSSL 3
==============================

When your distribution uses OpenSSL 3 and an OpenVPN version before 2.5.8, you might get the following error in the NetworkManager logging after connecting to a server that uses OpenVPN:

.. code-block:: console

    $ Cipher BF-CBC not supported

This means that OpenVPN is trying to initialize this legacy/deprecated cipher, even though it is not used in the config. The fix is in OpenVPN version starting at 2.5.8.

Could not find source connection/NetworkManager not managing connections
========================================================================

It could be the case where the client does not work due to the fact that NetworkManager does not manage your connections.

You could see errors such as:

.. code-block:: console

    $ nm-manager-error-quark: Could not find source connection.

To fix this, make sure that NetworkManager is managing your primary interface.
For e.g. Debian systems you can follow the instructions on `The Debian Wiki <https://wiki.debian.org/NetworkManager#Enabling_Interface_Management>`_ and then reboot. Pull requests are welcome to make the client work without NetworkManager.

Version GLIBC_2.32 not found
============================

If you install the client using instructions for a different distribution, you can have these GLIBC errors showing when the client is trying to load eduvpn-common. To fix this make sure to uninstall *all* the packages you currently have installed (Pip, DEB/RPM) and then follow the instructions for your appropriate distribution. See `Installation <./installation.html>`_.

If you have followed the right instructions and are still getting these errors you can make an issue.


GUI does not launch due to getting attribute errors
===================================================

If your GUI does not launch and you get errors such as:

.. code-block:: console

    $ File "/usr/lib/python3/dist-packages/eduvpn/ui/ui.py", line 165, in setup
    $ self.common_version.set_text(f"{commonver}")
    $ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    $ AttributeError: 'NoneType' object has no attribute 'set_text'

It can mean that you have installed multiple versions of the client. If you're trying to use the DEB/RPM version see if:

.. code-block:: console

    $ pip uninstall eduvpn-client[gui]

Does anything.

Otherwise, if there are files in `~/.local/share/eduvpn` try to move them to e.g. `~/.local/share/eduvpn2`. If the client then still doesn't launch you can make an issue.
