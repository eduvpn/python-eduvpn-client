---
name: Bug report
about: Create a report to help us improve

---

# Installation

How did you install the eduVPN/Let's Connect! client?

# Version

What version of the client you are running? Try your package manager or otherwise `eduvpn-gui -v` or `letsconnect-gui -v`.

Double check that you are running the latest version, see [the
releases page](https://github.com/eduvpn/python-eduvpn-client/releases) if a
new version is available.

# OS/Distribution

What operating system/distribution and version you are running?

# Logs

## Do you have a problem while adding before connecting?

eduVPN/Let's Connect! will print out information to the console while running. Please try running `eduvpn-gui` or `eduvpn-cli` (or `letsconnect-cli`, `letsconnect-gui` for Let's Connect!) in a console.  Are there any interesting logs appearing when you try to connect? There is also a more verbose mode available which is enabled with the `-d` flag. The log file is also located at `~/.config/eduvpn/log` for eduVPN and `~/.config/letsconnect/log` for Let's Connect!.

## Do you have a problem during or after connecting?

Please examine the eduVPN/Let's Connect! for errors or messages while connecting. Note that the actual VPN connection management is not done by eduVPN, but by network management tool bundeled with your OS named NetworkManager. You can examine the NetworkManager logs with `$ sudo journalctl -u NetworkManager`.
