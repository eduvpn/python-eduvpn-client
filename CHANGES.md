# 4.2.99.0 (2024-03-11)

* Update eduvpn-common to 1.99.1
* Implement WireGuard over TCP using Proxyguard
* Have the ability to cancel any NetworkManager operation in the UI, e.g. if it takes a long time for OpenVPN/WireGuard to connect, you can simply click the connection slider to cancel
* Convert the secure internet location button to a combobox
* Disable the search for a secure internet server if one is already configured
* Implement back button on choose profile page #453

# 4.2.1 (2024-02-02)

* Make the OpenVPN/WireGuard DNS the maximum priority to avoid DNS from resolving through other interfaces

# 4.2.0 (2023-12-08)

* Implement expiry notifications according to spec (Fixes: #534)
* Connection info counts up/down before revealed (Fixes: #531)
* Implement validity timer according to spec
* Move protocol info to connection info details instead of connection info title
* Bump eduvpn-common to 1.2.0
* Log unhandled exceptions

# 4.1.99.0 (2023-10-25)
Pre-release for 4.2.0:

* Remove unused dbus dependency (thanks! @a-andre)
* Make tests work without NetworkManager
* Do manual WireGuard routing using a fixed fwmark and a custom route table:
  - Have the ability to block LAN
  - Fix split tunnel where the VPN peer IP overlaps with the tunneled subnet (#551)
  - Do not set the never-default setting
* Settings:
  - Add back settings with only the WireGuard allow LAN toggle for now (default = True)
* Bump eduvpn-common to 1.1.99.0
* Manually configure DNS search domains with OpenVPN to fix #550
* Releases:
  - Add development GPG key to `keys/app+linux+dev@eduvpn.org.asc`
  - Update make script to automatically create a (pre-)release and upload tarballs with signatures

# 4.1.3 (2023-09-01)
Small hotfixes for 4.1.2:

* Bump eduvpn-common to 1.1.2 to further handle endpoint caching
* Mention eduvpn-common version in the UI
* Add a version flag to the CLI

# 4.1.2 (2023-08-29)
Small hotfixes for 4.1.1:

* Make sure profile combo indexes are always set correctly when ignoring the reconnect dialog
* Support MTU for WireGuard
* Bump eduvpn-common to 1.1.1 in order to fix OAuth endpoint caching issues

# 4.1.1 (2023-04-20)
Small hotfix for 4.1.0:

* Fix profile combo in UI not selecting the actual current profile

# 4.1.0 (2023-04-18)
Changes since 4.0.1:

* Update internal API to use eduvpn-common 1.1.0
    - Fixes OAuth issues with version 2 servers (empty refresh tokens on getting new tokens with a refresh token), fixes #521
    - Makes sure tokens are kept in sync between client and lib with a callback
    - Secure Internet: The default home location is chosen on adding
* Sort profiles and locations in CLI and UI, fixes #523
* Failover: The procedure that tries to detect issues with UDP connectivity
    - Support failover for OpenVPN, fixes #519
    - If failover was unable to determine connectivity issues but it took longer than normal (meaning: after the 2 second timeout where we try to get a pong from the server), a "reconnect with TCP" button is shown in the UI. For the CLI a --tcp flag is added, fixes #519
    - Use the first available IP in the subnet for the WireGuard gateway, for OpenVPN we request the gateway IP from NetworkManager
* CLI
    - Various fixes with regards to connecting, e.g. supplying an organisation ID previously resulted in an error
    - Clarify in flags help when a server is added fresh
    - Hide change location in Let's Connect!
* Misc
    - Hide the connection validity text when connecting
    - Be sure the renew session button is hidden when not connected
    - Update issues URL to link to the Linux client repo instead of eduvpn-common
    - Update desktop files with the correct name, fixes #522


# 4.0.1 (2023-03-07)
Hotfix release. Changes since 4.0.0:

* File keyring:
  - Make sure it supports multiple servers
  - Do not error out on invalid JSON
  - Add a version field to the JSON
* Properly delete the eduVPN connection on disconnect


# 4.0.0 (2023-03-02)
First release using eduvpn-common, changes since 3.3.1:

* Update to eduvpn-common 1.0.0
* Fix CLI by making GTK optional on runtime
* Asynchronously update discovery
* Show profile combo for 1 profile too
* CLI: ensure shorthand flag is available for --number
* CLI: Add VPN protocol to status
* CLI: Improve messages and error handling
* Drop OSX support, use eduvpn-common for an API
* Remove notebook files
* Update docs
* Try to fix Fedora freezes by ensuring connection info is run in the proper thread
* Make sure browser child processes are not left open by using `os.wait()`

# 3.3.1 (Beta/pre-release 2023-02-07)
This pre-release are a couple of Let's Connect! and threading changes

* Try to fix threading issues by only running async nm functions in the glib thread
* Fix launching of Let's Connect!
* Properly hide certain elements that are only applicable for eduVPN

# 3.3.0 (Beta/pre-release 2023-02-01)
This pre-release are a couple of QoL changes in the UI

* Do not style tree views
* Remove settings & help page and create an info popup instead
* Remove cancel on right click on a server
* Add dark theme support by using the right icons and using default buttons when we can
* Improve failover UI
* Add additonal logging to keyring


# 3.2.0 (Beta/pre-release 2022-12-23)
This pre-release refactors the whole app using the [eduvpn-common](https://github.com/eduvpn/eduvpn-common) Go library.

## Fixes
* #481 - The OAuth library/implementation we use now is built in house and fixes this
* #478/#465 - A profile expander is shown now
* #467 - The CLI has been rewritten to be more user friendly and work correctly with the V3 API
* #453 - Back buttons are shown correctly where they are possible/needed
* #434 - Most tests are now in the Go library that sets up a local network
* #428 - Proper imeouts are now used
* #426 - A renew session button is shown with accordance to the eduVPN specification https://github.com/eduvpn/documentation/blob/v3/API.md#session-expiry
* #412 - Prehashed signatures are supported because we use the official minisign go library in the eduvpn-common codebase
* #405 - The CLI now works correctly and should be more user friendly, especially if the interactive mode is used
* #374 - Let's Connect! now also has a CLI
* #351 - No longer a warning should be shown
* #336 - Implemented
* #335 - Exceptions are now shown in an error revealer similar to other clients
* #333 - Implemented
* #255 - We now implement it according to the eduVPN specification
* #253 - Removing a connection is now possible by right clicking on a server

## New features/Improvements that are not mentioned yet
* OAuth has a check for the new ISS parameter if the server supports it (https://datatracker.ietf.org/doc/rfc9207/)
* A server is now added instead of immediately connected, making it the same as other clients. The old behaviour can be toggled in the settings
* Let's Connect!/eduVPN now uses completely separate configurations
* Keyring implementation using Dbus to securely store OAuth tokens
* WireGuard to OpenVPN failover (if UDP is blocked)


# 3.1.0 (2022-06-23)

## Additions
* #489 Make NetworkManager connections optionally for the current user only by @jwijenbergh. This can get rid of authentication popups depending on your polkit settings
* #490 Add a quick note for the AUR package by @jwijenbergh

## Bugfixes
* #491 Refactor selections by @jwijenbergh. This fixes profiles/servers being selected automatically
* #494 Simplify getting interface/IP info and fix inconsistencies by @jwijenbergh. This gives a more accurate way to get the network interface across all systems
* #495 Cleanup network states by @jwijenbergh. This makes sure that we use the right connection for state updates, which fixes bugs when using eduVPN with another VPN/Connection. Additionally it fixes a major bug with reconnecting when using OpenVPN
* #497 Fix server info launch by @jwijenbergh. This guarantees that server info is correctly displayed when launching the app with an active eduVPN connection

# 3.0.0 (2022-05-09)

This version of the client makes it API compatible with eduVPN server version 3. A notable addition that this brings is Wireguard support.

## Additions
* #457 Update API to V3 by @alvra
* #461 Add a connection info expander by @jwijenbergh
* #466 WireGuard support by @alvra

## Bugfixes
* #455  Update makefile centos paths by @jwijenbergh
* #456  Makefile: do not fail rm if files do not exist by @jwijenbergh
* #472  Fix OpenVPN parsing by @dahooz
* #477  Make tests pass when running with NetworkManager by @jwijenbergh
* #483  Correct version flag by @gijzelaerr

## Enhancements
* #459  Add dates of releases by @fkooman
* #475  Wireguard: Disable autoconnect to match OpenVPN behaviour by @jwijenbergh
* #484  Add long description to pypi by @gijzelaerr


# 2.2.1 (2022-02-18)

## Bugfixes
* #440  Fix authorization for the Pale Moon browser by @jwijenbergh
* #448  Fix backwards compatibility with older GTK versions (e.g. Ubuntu 18.04) by @jwijenbergh

## Enhancements
* #437  Switch from /info.json to /.well-known/vpn-user-portal by @fkooman
* #443  Use the vault archive for CentOS 8 in the CI by @jwijenbergh
* #449  Add an error popup if no device of the primary connection is managed by NetworkManager by @jwijenbergh
* #450  Add missing gir1.2 nm package for Debian based systems to the Makefile by @jwijenbergh
* #452  Move from CentOS 8 in the CI to CentOS stream 8 by @jwijenbergh
* #453  Remove change location button by @jwijenbergh

# 2.2 (2022-12-20)

## Bugfixes
* #408  Fix issue with missing country flags by @alvra
* #416  Fix config directory permissions by @alvra
* #420  RPM icon issue by @gijzelaerr
* #431  Fix os.chdir by @fkooman
* #436  Fix split tunnel by @fkooman

## Enhancements
* #400  Various improvements by @alvra
* #401  Update license references to GPLv3+ by @fkooman
* #409  Allow the window to remain open by @alvra
* #414  Implement settings page by @alvra
* #419  Updates by @alvra
* #427  Allow user defined config directory using $XDG_CONFIG_HOME by @Jesse-Bakker


# 2.1 (2021-07-07)

## Bugfixes

* #386  Connexion still load details server  
* #384  Can't select my Organisation a second time
* #380  My VPN stopped working - unable to use eduvpn to re-setup network manager 
* #367  long institute/secure internet expand the scroll list vertically too much 
* #362  Bug in NaCL VerifyKey.__unicode__ 
* #360  command line config not working in GUI mode
* #310  oauthlib deprication warning on Ubuntu 20.04 
* #370  GTK app icon not set (only used in some edge cases)
* #358  eduVPN 2.0 package should depend on gir1.2-nm-1.0 

# Enhancements

* #340  Show notifications for session expiry   
* #332  Provide test coverage     
* #331  Create the "Let's Connect" variant of the app   
* #241  New UI: show an early warning when there is no NetworkManager active 
* #236  Implement "Skip WAYF"
* #231  Add internationalisation 
* #257  Improve documentation


# 2.0 (2021-04-09)

This is a complete rewrite of the code base.

Notable new features:

 * #337  Implement localization
 * #200/#229  Add command line interface
 * #206  Remove 2FA support (done by remote server now)
 * #153  Make GUI similar to other clients

Bug fixes:

 * #346  g_main_context warnings printed to console
 * #329  Selecting SURFnet bv and selecting Norway causes traceback
 * #312  Renew session button doesn't seem to do anything
 * #311  While starting/status update, check if active connection is the eduVPN connection
 * #296  Remove eduvpn.nm.VpnConnection layer
 * #295  Replace eduvpn.ui.vpn_connection with eduvpn.storage implementation
 * #293  PyGTKDeprecationWarning in ui/__main__.py on Ubuntu 20.04
 * #292  Application should show and only then start doing web requests
 * #291  GTK component is modified from background thread
 * #288  Disconnecting from an already disconnected session doesnt work
 * #283  Selecting a secure internet server doesn't work correctly
 * #281  Add new public keys for discovery signature verification
 * #279  let's connect: proceed when pressed <enter> after entering URL
 * #273  update discovery URL
 * #269  Debian: connecting to another vpn server fails
 * #265  TypeError: write() argument must be str, not None
 * #264  when connected, close app, restart app, configure profile, app indicated 'not connected' while connected
 * #263  When connected and re-configuring profile, user ends up in 'connected' screen with wrong info
 * #260  Error with cli when nm and/or dbus are not installed or not available
 * #259  Dark mode should look good (icons etc.)
 * #258  Refactor ui.py
 * #256  Improve logging
 * #254  Error handling/display
 * #252  React on status changes in the NetworkManager connection
 * #251  Remember the last connection
 * #250  Save the connection so you can access it quickly again
 * #249  Get UI stable
 * #247  In dark mode institute list background is still light 
 * #246  new UI: improve token handling
 * #246  new UI: improve token handling
 * #245  new UI: make tests work with docker / travis
 * #244  new UI: create a deb package
 * #243  new UI: create a RPM package
 * #242  new UI: install using pip install
 * #237  building eduVPN from fc31.src.rpm on Fedora 32 fails
 * #235  Switch the country_code instead of display_name for "Secure Internet"
 * #234  centos8 docker container RPM build fails on travis
 * #233  Use DBus in case of VPN connection status change
 * #232  Update debian packages to match new setup.py layout
 * #230  Support multiple verify keys
 * #224  Only use one dynamically updated networkmanager VPN configuration
 * #223  Simplify storing of metadata
 * #222  Create new ui files for all screens
 * #221  Merge all RPM spec files into one
 * #213  Do not show VPN entries already in NetworkManager
 * #208  tests failure in headless Linux build environment
 * #205  switch to new server discovery procedure
 * #197  remove /user_info API calls
 * #175  Restructure packaging to improve letsconnect/eduvpn packaging results
 * #173  Reorganise certificate management
 * #170  Use NM config parser for importing .ovpn
 * #159  when obtaining new token for 1 profile for one server, other profiles should not ask again
 * #152  profiles selected one by one after profile delete triggering user/system message fetch
 * #151  No need to create new keypair per profile
 * #139  Add connect-timeout to settings

# 1.1

 * Remove Python 2 support #192
 * Remove CentOS 7 support #192
 * Use stdlib instead of python3-configparser dependency #210
 * Use stdlib instead of python3-mock dependency #211
 * Use stdlib instead of python3-repoze-lru #212
 * Make sure Centos 8 rpm builds properly (on copr) #220


# 1.0.3

bugfixes:

 * can't finalize configuration: ValueError: Missing access token. #198
 * Unicode providers don't work with python2 #191
 * failure while reading networkmanager configuration #189
 * Include client_id in phase 2 #184
 
changes:

 * Remove .pyi files #174
 * Remove DNS leaking warming for 18.04 since it seems to be fixed. #177
 

# 1.0.2

 * client expects multiple remotes #156
 * use LC client_id for for LC client #155
 * DNS leaking on Ubuntu 18.04 #160
 * debian tls-crypt config parse bug #157
 

# 1.0.1

 * pypi doesnt show latest version - make 1.0(.1) release #135
 

# 1.0rc17

 * Let's Connect integration #134
 
 
# 1.0rc16

 * Make all UI element uniform (again) #143
 * make sure OTP enroll dialog fits on 1366x768 resolution #146
 * After re-auth flow completed, all other expired configurations create a popup low priority #121
 * refreshing token when refresh token is expired broken #150
 * limit totp and yubikey entry fields to specific chars #149
 * disconnect active VPN connections when connecting #130
 * kill webserver thread on cancel in browser step, better error parsing low priority #74 
 * use username in qr token #144
 * client does not detect removed TOTP secret #148
 * increase length of TOTP secret #147
 * no error in UI when entering wrong OTP key #145
 * add qr and pillow dependency to all packages #142
 * fix renew X.509 certificate #115
 * Add yubi_enroll.ui install setup.py #140
 * add QR dependency #141
 * double clicking on icon to connect gives error #136
 * "fetching" dialog doesn't have main screen as transient parent on Fedora #132
 * OAuth token expiry - on/off switch only reports, doesn't trigger re-auth flow #126
 * Reauthorize should not show "choose your profile" again #119
 * 2fa is "used" when connecting to profile that has no 2fa bug #118
 * deleting one provider deletes multiple from list bug #112
 * revoking client gives error bug #111
 * add cli flags to switch to debug server #131
 

# 1.0rc15

* Disable connect-timeout setting #138


# 1.0rc14

* Dev servers were accidentally enabled for 1.0rc13


# 1.0rc13

 * 'distributed' does not work #124 
 *  server-poll-timeout ignored #122
 * key-direction ignored when importing profile #123 
 * can't enable connection bug #110 
 * key-direction only relevant for tls-auth, not tls-crypt bug #108 
 * 2FA error makes no sense? bug #114 
 * callback doesn't check state #72
 * Ip addresses not shown with OS using netplan bug #99
 * Add Ubuntu 18.04 to supported architectures in doc #98


# 1.0rc12

 * comp-lzo should not (always) be on bug #107 
 * problems with lambdas handling exception in Python 3.6 #106 
 * invalid refresh token / access token should trigger reauthorization 105 
 * We support system wide install and virtualenv but not pip install in .local 104 
 * python test suite fails during debian package build low priority 61
 * API documentation on readthedocs partially broken #90
 * username unknown while auth-user-pass is set bug #102 
 * OAuth client ID enhancement#95 
 * tls-crypt not supported bug #100 
 * Manage script by entrypoint enhancement #101
 * Ubuntu 16.04.3 LTS > 'property 'tls-cipher' invalid or not supported' #92
 * Ubuntu 17.10 > no protocol specified #93 


# 1.0rc9

 * AttributeError #86
 * python test suite fails during debian package build low priority #61
 * test suite passes but raises errors in threads low priority #75


# 1.0rc8

 * Add distributed support #71
 * don't look at user_info to see if 2fa is enabled for profile #79
 * client gets confused on duplicate entries? #73
 * enable timing in logs #81
 
 
# 1.0.rc7

 * client disabled dialog broken #80
 * rpm buid fails for 1.05c6 due to missing pytest-runner #76
 

# 1.0rc6

 * Fedora 27 build fails #68
 * can't handle non ascii code in display_name on python2 #70
 * selection screen not working in case of more than one 2fa methods #69
 
 
# 1.0rc5

 * settings don't update for a new connection #67
 
 
# 1.0rc4

 * resturcture metadata to make more robust and future ready #66
 * profile model not cleared on new flow #65
 * ERROR:eduvpn.util:Can't fetch user messages: Invalid scope (config), must be string, tuple, set, or list. #64
 
 
# 1.0rc3

 * add choice for 2FA method (if enabled) #59
 * make python 3 debian package low priority #44
 * documentation doesn't generate well due to missing modules #54
 * show notification if account is disabled #60
 * messages can use some formatting #58
 * enable online test suite #52
 * improve test suite #45
 * make sure 2fa is working #51
 * issue with oauth requests module on Ubuntu 14.04 #53
 * prettify notification #57
 * update connection switch when user connects using networkmanager low priority #36
 * probably bug in networkmanager or dbus package for fedora 26 #42
 * The "Connected" button breaks often #56
 
 
# 1.0rc2

 * revoked token gives error #49
 * choosing profile does not work #50
 * refresh tokens not implemented #48
 
 
# 1.0rc1

 * missing README.md? #46
 * go one last time over all graphical elements #35
 * some changes in use of text #47
 
 
# 0.8

 * add headers to all files #29
 * modify 'display_name' to "eduVPN for Linux" #37
 * give user choice to open browser or show link #30
 * http callback window acts funny when closed #34
 * add logic to refresh configuration / certificates #24
 * add support for newer networkmanager signals #43
 * Make RPM #39
 * no notification #32
