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
BuildRequires: gtk3
BuildRequires: python3-pytest
BuildRequires: python3-pytest-runner
BuildRequires: python3-dbus
BuildRequires: python3-gobject
BuildRequires: python3-pynacl
BuildRequires: python3-requests-oauthlib
BuildRequires: python3-future
BuildRequires: python3-dateutil
BuildRequires: python3-cryptography
BuildRequires: python3-qrcode
BuildRequires: python3-pillow
# BuildRequires: python3-repoze-lru

%description
An python module which provides a convenient example.

%package -n python3-lets-connect-client
Summary:        %{sum}
%{?python_provide:%python_provide python3-lets-connect-client}
Requires: python3-gobject
Requires: python3-dbus
Requires: python3-pynacl
Requires: python3-requests-oauthlib
Requires: python3-future
Requires: python3-dateutil
Requires: python3-cryptography
Requires: python3-qrcode
Requires: python3-pillow
Conflicts: python3-lets-connect-client
# Requires: python3-repoze-lru


%description -n python3-lets-connect-client
Let's Connect client API for Python3

%package -n lets-connect-client
Summary: %[sum}
Requires: gtk3
Requires: libnotify
Requires:  python3-lets-connect-client
Conflicts: eduvpn-client

%description -n lets-connect-client
Let's Connect desktop client

%prep
%autosetup -n %{srcname}-%{version}

%build
%{__python3} setup_letsconnect.py build


%install
%{__python3} setup_letsconnect.py install --root $RPM_BUILD_ROOT


%check
%{__python3} setup_letsconnect.py test

%files -n python3-lets-connect-client
%license LICENSE
%doc README.md
%{python3_sitelib}/*

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
