%global srcname eduvpn_client
%global sum client for eduVPN

Name:           eduvpn_client
Version:        1.9.0
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
Conflicts: python3-lets-connect-client

%description -n python3-eduvpn-client
eduVPN client API for Python3

%package -n eduvpn-client
Summary: %[sum}
Requires: gtk3
Requires: libnotify
Requires:  python3-eduvpn-client
Conflicts: lets-connect-client

%description -n eduvpn-client
eduVPN desktop client

%prep
%autosetup -n %{srcname}-%{version}

%build
%{__python3} setup.py build

%install
%{__python3} setup.py install --root $RPM_BUILD_ROOT

%check
%{__python3} setup.py test

%files -n python3-eduvpn-client
%license LICENSE
%doc README.md
%{python3_sitelib}/*

%files -n eduvpn-client
%license LICENSE
%doc README.md
%{_bindir}/eduvpn-client
%{_datarootdir}/applications/eduvpn-client.desktop
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

%changelog
