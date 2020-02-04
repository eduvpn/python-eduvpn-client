%global srcname lets_connect_client
%global sum client for Let's Connect!

Name:           lets_connect_client
Version:        1.0.3
Release:        1%{?dist}
Summary:        %{sum}

License:        MIT
URL:            https://pypi.python.org/pypi/%{srcname}
Source0:        https://files.pythonhosted.org/packages/source/e/%{srcname}/%{srcname}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires: pytest
BuildRequires: python2-pytest-runner
BuildRequires: gtk3
BuildRequires: libnotify
BuildRequires: dbus-python
BuildRequires: python-gobject
BuildRequires: python2-pynacl
BuildRequires: python-repoze-lru
BuildRequires: python2-devel
BuildRequires: python2-requests-oauthlib
BuildRequires: python2-configparser
BuildRequires: python2-future
BuildRequires: python2-mock
BuildRequires: python-dateutil
BuildRequires: python2-cryptography
BuildRequires: python-qrcode
BuildRequires: python-pillow

%description
An python module which provides a convenient example.

%package -n python2-lets-connect-client
Summary:        %{sum}
%{?python_provide:%python_provide python2-lets-connect-client}
Requires: python-gobject
Requires: dbus-python
Requires: python2-pynacl
Requires: python-repoze-lru
Requires: python2-requests-oauthlib
Requires: python2-configparser
Requires: python2-future
Requires: python2-dateutil
Requires: python2-cryptography
Requires: python-qrcode
Requires: python-pillow
Conflicts: python2-eduvpn-client 


%description -n python2-lets-connect-client
Let's Connect client API for Python2

%package -n lets-connect-client
Summary: %[sum}
Requires: gtk3
Requires: libnotify
Requires:  python2-lets-connect-client
Conflicts: eduvpn-client 

%description -n lets-connect-client
Let's Connect desktop client

%prep
%autosetup -n %{srcname}-%{version}

%build
%{__python2} setup_letsconnect.py build


%install
%{__python2} setup_letsconnect.py install --root $RPM_BUILD_ROOT


%check
%{__python2} setup_letsconnect.py test

%files -n python2-lets-connect-client
%license LICENSE
%doc README.md
%{python2_sitelib}/*

%files -n lets-connect-client
%license LICENSE
%doc README.md
%{_bindir}/lets-connect-client
%{_datarootdir}/applications/lets-connect-client.desktop
%{_datarootdir}/eduvpn/eduvpn.png
%{_datarootdir}/eduvpn/institute.png
%{_datarootdir}/eduvpn/institute_small.png
%{_datarootdir}/eduvpn/internet.png
%{_datarootdir}/eduvpn/internet_small.png
%{_datarootdir}/eduvpn/builder/2fa.ui
%{_datarootdir}/eduvpn/builder/connection_type.ui
%{_datarootdir}/eduvpn/builder/custom_url.ui
%{_datarootdir}/eduvpn/builder/fetch.ui
%{_datarootdir}/eduvpn/builder/instances.ui
%{_datarootdir}/eduvpn/builder/profiles.ui
%{_datarootdir}/eduvpn/builder/redirecturl.ui
%{_datarootdir}/eduvpn/builder/token.ui
%{_datarootdir}/eduvpn/builder/window.ui
%{_datarootdir}/eduvpn/builder/totp_enroll.ui
%{_datarootdir}/eduvpn/builder/yubi_enroll.ui
%{_datarootdir}/icons/hicolor/128x128/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/256x256/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/48x48/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/512x512/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/48x48/apps/lets-connect-client.png
%{_datarootdir}/icons/hicolor/256x256/apps/lets-connect-client.png
%{_datarootdir}/icons/hicolor/512x512/apps/lets-connect-client.png
%{_datarootdir}/icons/hicolor/128x128/apps/lets-connect-client.png
%{_datarootdir}/letsconnect/settings_full.png
%{_datarootdir}/letsconnect/connected.png
%{_datarootdir}/letsconnect/connecting.png
%{_datarootdir}/letsconnect/tray.png
%{_datarootdir}/letsconnect/settings.png
%{_datarootdir}/letsconnect/fallback.png
%{_datarootdir}/letsconnect/disconnected.png

%changelog
