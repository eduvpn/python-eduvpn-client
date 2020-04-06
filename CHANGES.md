Work in progress
================

changes:

 * Remove Python 2 support #192
 * Remove CentOS 7 support #192
 * Use stdlib instead of python3-configparser dependency #210
 * Use stdlib instead of python3-mock dependency #211
 * Use stdlib instead of python3-repoze-lru #212

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
