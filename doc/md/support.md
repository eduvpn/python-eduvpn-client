# Support

If you experience any issues you could and should report them at our
[issue tracker](https://github.com/eduvpn/python-eduvpn-client/issues).
Please don't forget to mention:

- Your distribution
- Method of installation
- The eduVPN client version
- Instructions on how to reproduce the problem.

If you
have a problem enabling your VPN connection please also examine the
`journalctl -u NetworkManager` logs. 

The log file of the
eduVPN app can also help us figure out the problem, running the gui or
cli in debug mode (-d) flag will print debug logging to the log file
located at: `~/.config/eduvpn/log` or `~/.config/letsconnect/log` for
Let's Connect!.

If you prefer e-mail, you can send one, with the same details, to:

[eduvpn-support@lists.geant.org](mailto:eduvpn-support@lists.geant.org)

See the section below for any known issues.

## Known issues

### WireGuard IPv6 blocked with firewalld

Firewalld is a firewall that is used by default on e.g. Fedora.
There is an issue with IPv6 traffic and WireGuard, see: https://github.com/firewalld/firewalld/issues/1203 and https://bugzilla.redhat.com/show_bug.cgi?id=2293925

The workaround is to set `IPv6_rpfilter=no` in `/etc/firewalld/firewalld.conf` and restarting firewalld.service or rebooting

### OpenVPN <= 2.5.7 and OpenSSL 3

When your distribution uses OpenSSL 3 and an OpenVPN version before
2.5.8, you might get the following error in the NetworkManager logging
after connecting to a server that uses OpenVPN:

``` console
Cipher BF-CBC not supported
```

This means that OpenVPN is trying to initialize this legacy/deprecated
cipher, even though it is not used in the config. The fix is in OpenVPN
version starting at 2.5.8.

### Could not find source connection

It could be the case where the client does not work due to the fact that
NetworkManager does not manage your connections.

You could see errors such as:

``` console
nm-manager-error-quark: Could not find source connection.
```

To fix this, make sure that NetworkManager is managing your primary
interface. For e.g. Debian systems you can follow the instructions on
[The Debian
Wiki](https://wiki.debian.org/NetworkManager#Enabling_Interface_Management)
and then reboot. Pull requests are welcome to make the client work
without NetworkManager.

### Version GLIBC_2.32 not found

If you install the client using instructions for a different
distribution, you can have these GLIBC errors showing when the client is
trying to load eduvpn-common. To fix this make sure to uninstall *all*
the packages you currently have installed (Pip, Deb/RPM) and then follow
the instructions for your appropriate distribution. See
[Installation](./installation.md).

If you have followed the right instructions and are still getting these
errors you can make an issue.

### GUI does not launch due to getting attribute errors

If your GUI does not launch and you get errors such as:

``` console
File "/usr/lib/python3/dist-packages/eduvpn/ui/ui.py", line 165, in setup
self.common_version.set_text(f"{commonver}")
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'set_text'
```

It can mean that you have installed multiple versions of the client. If
you\'re trying to use the Deb/RPM version see if:

``` console
pip uninstall eduvpn-client[gui]
```

Does anything.

Otherwise, if there are files in `~/.local/share/eduvpn`
try to move them to e.g. `~/.local/share/eduvpn2`. If the
client then still doesn't launch you can make an issue.
