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
