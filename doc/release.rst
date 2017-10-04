How to make a release
=====================

* Determine version number (for example 1.0rc8)

* Make sure the development discovery URL's are disabled in eduvpn/config.py

* Make sure the test suite runs with python2 and python3

* Set version number in setup.py and eduvpn-client.spec

* Commit

* Press release button on github. List all changes since the last release

* Check if travis builds. If so, it will upload to pypi.


* If it doesn't build fix and do a manual upload using twine

  https://github.com/pypa/twine

* Make a SRPM and upload to https://copr.fedorainfracloud.org/coprs/gijzelaerr/eduvpn-client/

* make a debian package https://github.com/eduvpn-debian/packaging
