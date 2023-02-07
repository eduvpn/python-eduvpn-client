%global srcname eduvpn_client
%global sum client for eduVPN

Name:           eduvpn_client
Version:        3.3.1
Release:        0.1%{?dist}
Summary:        %{sum}

License:        GPLv3+
URL:            https://pypi.python.org/pypi/%{srcname}
Source0:        https://files.pythonhosted.org/packages/source/e/%{srcname}/%{srcname}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires: gtk3
BuildRequires: libnotify
BuildRequires: python3-pytest
BuildRequires: python3-pytest-runner
BuildRequires: python3-dbus
BuildRequires: python3-gobject
BuildRequires: python3-devel
BuildRequires: python3-wheel
BuildRequires: python3-pip
BuildRequires: python3-pycodestyle
BuildRequires: python3-eduvpn-common
BuildRequires: desktop-file-utils

%description
The eduVPN client.

%package -n python3-eduvpn-client
Summary:        %{sum}
%{?python_provide:%python_provide python3-eduvpn-client}
Requires: python3-gobject
Requires: python3-dbus
Requires: python3-eduvpn-common >= 0.3.0, python3-eduvpn-common < 0.4.0
Requires: NetworkManager-openvpn
Requires: libsecret
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
desktop-file-install %{buildroot}/%{_datadir}/applications/org.eduvpn.client.desktop

#%check
#%{__python3} setup.py test


%files -n python3-eduvpn-client
%license LICENSE
%doc README.md
%{python3_sitelib}/*

%files -n eduvpn-client
%license LICENSE
%doc README.md
%{_bindir}/eduvpn-cli
%{_bindir}/eduvpn-gui
%{_datarootdir}/applications/org.eduvpn.client.desktop
%{_datarootdir}/eduvpn/eduvpn.png
%{_datarootdir}/eduvpn/country_codes.json
%{_datarootdir}/eduvpn/builder/mainwindow.ui
%{_datarootdir}/icons/hicolor/128x128/apps/org.eduvpn.client.png
%{_datarootdir}/icons/hicolor/256x256/apps/org.eduvpn.client.png
%{_datarootdir}/icons/hicolor/48x48/apps/org.eduvpn.client.png
%{_datarootdir}/icons/hicolor/512x512/apps/org.eduvpn.client.png
%{_datarootdir}/eduvpn/images/*.svg
%{_datarootdir}/eduvpn/images/*.png
%{_datarootdir}/eduvpn/images/flags/png/*.png
%{_datarootdir}/locale/*/LC_MESSAGES/eduVPN.mo

%files -n letsconnect-client
%license LICENSE
%doc README.md
%{_bindir}/letsconnect-cli
%{_bindir}/letsconnect-gui
%{_datarootdir}/applications/org.letsconnect-vpn.client.desktop
%{_datarootdir}/eduvpn/builder/mainwindow.ui
%{_datarootdir}/eduvpn/country_codes.json
%{_datarootdir}/icons/hicolor/128x128/apps/org.letsconnect-vpn.client.png
%{_datarootdir}/icons/hicolor/256x256/apps/org.letsconnect-vpn.client.png
%{_datarootdir}/icons/hicolor/48x48/apps/org.letsconnect-vpn.client.png
%{_datarootdir}/icons/hicolor/512x512/apps/org.letsconnect-vpn.client.png
%{_datarootdir}/eduvpn/images/*.svg
%{_datarootdir}/eduvpn/images/*.png
%{_datarootdir}/letsconnect/images/*.png
%{_datarootdir}/letsconnect/images/*.svg

%changelog
