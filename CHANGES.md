2.1
===

Bugfixes
--------

* #386  Connexion still load details server  
* #384  Can't select my Organisation a second time
* #380  My VPN stopped working - unable to use eduvpn to re-setup network manager 
* #367  long institute/secure internet expand the scroll list vertically too much 
* #362  Bug in NaCL VerifyKey.__unicode__ 
* #360  command line config not working in GUI mode
* #310  oauthlib deprication warning on Ubuntu 20.04 
* #370  GTK app icon not set (only used in some edge cases)
* #358  eduVPN 2.0 package should depend on gir1.2-nm-1.0 

Enhancements
------------

* #340  Show notifications for session expiry   
* #332  Provide test coverage     
* #331  Create the "Let's Connect" variant of the app   
* #241  New UI: show an early warning when there is no NetworkManager active 
* #236  Implement "Skip WAYF"
* #231  Add internationalisation 
* #257  Improve documentation


2.0
===

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

1.1
===

 * Remove Python 2 support #192
 * Remove CentOS 7 support #192
 * Use stdlib instead of python3-configparser dependency #210
 * Use stdlib instead of python3-mock dependency #211
 * Use stdlib instead of python3-repoze-lru #212
 * Make sure Centos 8 rpm builds properly (on copr) #220


1.0.3
=====

bugfixes:

 * can't finalize configuration: ValueError: Missing access token. #198
 * Unicode providers don't work with python2 #191
 * failure while reading networkmanager configuration #189
 * Include client_id in phase 2 #184
 
changes:

 * Remove .pyi files #174
 * Remove DNS leaking warming for 18.04 since it seems to be fixed. #177
 

1.0.2
=====

 * client expects multiple remotes #156
 * use LC client_id for for LC client #155
 * DNS leaking on Ubuntu 18.04 #160
 * debian tls-crypt config parse bug #157
 

1.0.1
=====

 * pypi doesnt show latest version - make 1.0(.1) release #135
 

1.0rc17
=======

 * Let's Connect integration #134
 
 
1.0rc16
=======

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
 

1.0rc15
=======

* Disable connect-timeout setting #138


1.0rc14
=======

* Dev servers were accidentally enabled for 1.0rc13


1.0rc13
=======

 * 'distributed' does not work #124 
 *  server-poll-timeout ignored #122
 * key-direction ignored when importing profile #123 
 * can't enable connection bug #110 
 * key-direction only relevant for tls-auth, not tls-crypt bug #108 
 * 2FA error makes no sense? bug #114 
 * callback doesn't check state #72
 * Ip addresses not shown with OS using netplan bug #99
 * Add Ubuntu 18.04 to supported architectures in doc #98


1.0rc12
=======

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


1.0rc9
======

 * AttributeError #86
 * python test suite fails during debian package build low priority #61
 * test suite passes but raises errors in threads low priority #75


1.0rc8
======

 * Add distributed support #71
 * don't look at user_info to see if 2fa is enabled for profile #79
 * client gets confused on duplicate entries? #73
 * enable timing in logs #81
 
 
1.0.rc7
=======

 * client disabled dialog broken #80
 * rpm buid fails for 1.05c6 due to missing pytest-runner #76
 

1.0rc6
======

 * Fedora 27 build fails #68
 * can't handle non ascii code in display_name on python2 #70
 * selection screen not working in case of more than one 2fa methods #69
 
 
1.0rc5
======

 * settings don't update for a new connection #67
 
 
1.0rc4
======

 * resturcture metadata to make more robust and future ready #66
 * profile model not cleared on new flow #65
 * ERROR:eduvpn.util:Can't fetch user messages: Invalid scope (config), must be string, tuple, set, or list. #64
 
 
1.0rc3
======

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
 
 
1.0rc2
======

 * revoked token gives error #49
 * choosing profile does not work #50
 * refresh tokens not implemented #48
 
 
1.0rc1
======

 * missing README.md? #46
 * go one last time over all graphical elements #35
 * some changes in use of text #47
 
 
0.8
===

 * add headers to all files #29
 * modify 'display_name' to "eduVPN for Linux" #37
 * give user choice to open browser or show link #30
 * http callback window acts funny when closed #34
 * add logic to refresh configuration / certificates #24
 * add support for newer networkmanager signals #43
 * Make RPM #39
 * no notification #32
