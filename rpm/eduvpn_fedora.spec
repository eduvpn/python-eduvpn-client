%global srcname eduvpn_client
%global sum client for eduVPN

Name:           eduvpn_client
Version:        1.0.1
Release:        1%{?dist}
Summary:        %{sum}

License:        MIT
URL:            https://pypi.python.org/pypi/%{srcname}
Source0:        https://files.pythonhosted.org/packages/source/e/%{srcname}/%{srcname}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires: pytest
BuildRequires: python2-pytest-runner
BuildRequires: python3-pytest-runner
BuildRequires: gtk3
BuildRequires: libnotify
BuildRequires: dbus-python
BuildRequires: python-gobject
BuildRequires: python2-devel
BuildRequires: python2-pynacl
BuildRequires: python2-requests-oauthlib
BuildRequires: python2-configparser
BuildRequires: python2-future
BuildRequires: python2-mock
BuildRequires: python2-cryptography
BuildRequires: (python2-qrcode or python-qrcode)
BuildRequires: python2-pillow
BuildRequires: python-repoze-lru
BuildRequires: python3-devel
BuildRequires: python2-dateutil
BuildRequires: python3-dbus
BuildRequires: python3-pynacl
BuildRequires: python3-requests-oauthlib
BuildRequires: python3-gobject
BuildRequires: python3-future
BuildRequires: python3-dateutil
BuildRequires: python3-repoze-lru
BuildRequires: python3-mock
BuildRequires: python3-cryptography
BuildRequires: python3-qrcode
BuildRequires: python3-pillow


%description
An python module which provides a convenient example.

%package -n python2-eduvpn-client
Summary:        %{sum}
%{?python_provide:%python_provide python2-eduvpn-client}
Requires: python-gobject
Requires: dbus-python
Requires: python2-pynacl
Requires: python2-requests-oauthlib
Requires: python2-configparser
Requires: python2-future
Requires: python2-dateutil
Requires: python-repoze-lru
Requires: python2-cryptography
Requires: (python2-qrcode or python-qrcode)
Requires: python2-pillow
Conflicts: python2-lets-connect-client

%description -n python2-eduvpn-client
eduVPN client API for Python2


%package -n python3-eduvpn-client
Summary:        %{sum}
%{?python_provide:%python_provide python3-eduvpn-client}
Requires: python3-dbus
Requires: python3-pynacl
Requires: python3-requests-oauthlib
Requires: python3-gobject
Requires: python3-future
Requires: python3-dateutil
Requires: python3-repoze-lru
Requires: python3-cryptography
Requires: python3-qrcode
Requires: python3-pillow
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
%py2_build
%py3_build


%install
%py2_install
%py3_install


%check
%{__python3} setup.py test
%{__python2} setup.py test

%files -n python2-eduvpn-client
%license LICENSE
%doc README.md
%{python2_sitelib}/*

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
