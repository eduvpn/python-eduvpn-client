%global srcname eduvpn_client
%global sum client for eduVPN

Name:           eduvpn_client
Version:        1.0rc12
Release:        1%{?dist}
Summary:        %{sum}

License:        MIT
URL:            https://pypi.python.org/pypi/%{srcname}
Source0:        https://files.pythonhosted.org/packages/source/e/%{srcname}/%{srcname}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires: pytest
# BuildRequires: python2-pytest-runner   # - not included in centos7
BuildRequires: gtk3
BuildRequires: libnotify
BuildRequires: dbus-python
BuildRequires: python-gobject
# BuildRequires: python-pynacl   # - not included in centos7
BuildRequires: python-repoze-lru
BuildRequires: python2-devel
BuildRequires: python2-requests-oauthlib
BuildRequires: python2-configparser
BuildRequires: python2-future
BuildRequires: python2-mock
BuildRequires: python-dateutil
BuildRequires: gcc
# GCC is required for the test run that will compile and install pynacl manually



%description
An python module which provides a convenient example.

%package -n python2-eduvpn-client
Summary:        %{sum}
%{?python_provide:%python_provide python2-eduvpn-client}
Requires: python-gobject
Requires: dbus-python
# Requires: python-pynacl  # - not included in centos7
Requires: python-repoze-lru
Requires: python2-requests-oauthlib
Requires: python2-configparser
Requires: python2-future
Requires: python2-dateutil


%description -n python2-eduvpn-client
eduVPN client API for Python2

%package -n eduvpn-client
Summary: %[sum}
Requires: gtk3
Requires: libnotify
Requires:  python3-eduvpn-client

%description -n eduvpn-client
eduVPN desktop client

%prep
%autosetup -n %{srcname}-%{version}

%build
%py2_build


%install
%py2_install


%check
%{__python2} setup.py test

%files -n python2-eduvpn-client
%license LICENSE
%doc README.md
%{python2_sitelib}/*

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
%{_datarootdir}/icons/hicolor/128x128/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/256x256/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/48x48/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/512x512/apps/eduvpn-client.png

%changelog
