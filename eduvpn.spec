%global srcname eduvpn_client
%global sum client for eduVPN

Name:           eduvpn_client
Version:        2.0.0
Release:        1%{?dist}
Summary:        %{sum}

License:        MIT
URL:            https://pypi.python.org/pypi/%{srcname}
Source0:        https://files.pythonhosted.org/packages/source/e/%{srcname}/%{srcname}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires: gtk3
BuildRequires: libnotify
BuildRequires: python3-pytest
BuildRequires: python3-pytest-runner
# BuildRequires: python3-devel
BuildRequires: python3-dbus
BuildRequires: python3-gobject
BuildRequires: python3-pynacl
BuildRequires: python3-requests-oauthlib
BuildRequires: python3-dateutil
BuildRequires: python3-cryptography


%description
The eduVPN client.

%package -n python3-eduvpn-client
Summary:        %{sum}
%{?python_provide:%python_provide python3-eduvpn-client}
Requires: python3-gobject
Requires: python3-dbus
Requires: python3-pynacl
Requires: python3-requests-oauthlib
Requires: python3-dateutil
Requires: python3-cryptography
Requires: NetworkManager-openvpn
Conflicts: python3-letsconnect-client

%description -n python3-eduvpn-client
eduVPN client API for Python3

%package -n eduvpn-client
Summary: %{sum}
Requires: gtk3
Requires: libnotify
Requires: NetworkManager-openvpn
Requires:  python3-eduvpn-client
Conflicts: letsconnect-client

%description -n eduvpn-client
eduVPN desktop client


%package -n letsconnect-client
Summary: %{sum}
Requires: gtk3
Requires: libnotify
Requires:  python3-eduvpn-client

%description -n letsconnect-client
Let's Connect! desktop client

%prep
%autosetup -n %{srcname}-%{version}

%build
%py3_build


%install
%py3_install


%check
%{__python3} setup.py test


%files -n python3-eduvpn-client
%license LICENSE
%doc README.md
%{python3_sitelib}/*

%files -n eduvpn-client
%license LICENSE
%doc README.md
%{_bindir}/eduvpn-cli
%{_bindir}/eduvpn-gui
%{_datarootdir}/applications/eduvpn-client.desktop
%{_datarootdir}/eduvpn/eduvpn.png
%{_datarootdir}/eduvpn/country_codes.json
%{_datarootdir}/eduvpn/builder/mainwindow.ui
%{_datarootdir}/icons/hicolor/128x128/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/256x256/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/48x48/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/512x512/apps/eduvpn-client.png
%{_datarootdir}/eduvpn/images/*.svg
%{_datarootdir}/eduvpn/images/*.png

%files -n letsconnect-client
%license LICENSE
%doc README.md
%{_bindir}/letsconnect-cli
%{_bindir}/letsconnect-gui
%{_datarootdir}/applications/letsconnect-client.desktop
%{_datarootdir}/eduvpn/builder/mainwindow.ui
%{_datarootdir}/eduvpn/country_codes.json
%{_datarootdir}/icons/hicolor/128x128/apps/letsconnect-client.png
%{_datarootdir}/icons/hicolor/256x256/apps/letsconnect-client.png
%{_datarootdir}/icons/hicolor/48x48/apps/letsconnect-client.png
%{_datarootdir}/icons/hicolor/512x512/apps/letsconnect-client.png
%{_datarootdir}/eduvpn/images/*.svg
%{_datarootdir}/eduvpn/images/*.png
%{_datarootdir}/letsconnect/images/*.png
%{_datarootdir}/letsconnect/images/*.svg

%changelog
