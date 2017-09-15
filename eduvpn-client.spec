%global srcname eduvpn_client
%global sum client for eduVPN

Name:           eduvpn_client
Version:        1.0rc1
Release:        1%{?dist}
Summary:        %{sum}

License:        MIT
URL:            https://pypi.python.org/pypi/%{srcname}
Source0:        https://files.pythonhosted.org/packages/source/e/%{srcname}/%{srcname}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python2-devel python3-devel

%description
An python module which provides a convenient example.

%package -n python2-eduvpn-client
Summary:        %{sum}
%{?python_provide:%python_provide python2-eduvpn-client}
Requires: python-gobject
Requires: python2-networkmanager
Requires: python2-pydbus
Requires: python2-pynacl
Requires: python2-requests-oauthlib
Requires: python2-configparser
Requires: python2-future


%description -n python2-eduvpn-client
eduVPN client API for Python2


%package -n python3-eduvpn-client
Summary:        %{sum}
%{?python_provide:%python_provide python3-eduvpn-client}
Requires: python3-networkmanager
Requires: python3-pydbus
Requires: python3-pynacl
Requires: python3-requests-oauthlib
Requires: python3-gobject
Requires: python3-configparser
Requires: python3-future

%description -n python3-eduvpn-client
eduVPN client API for Python3

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
%py3_build
%py2_build

%install
%py3_install
%py2_install

# todo: disable for now, creates side effects
#%check
#%{__python3} setup.py test
#%{__python2} setup.py test

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
%{_datarootdir}/eduvpn/eduvpn.ui
%{_datarootdir}/eduvpn/institute.png
%{_datarootdir}/eduvpn/institute_small.png
%{_datarootdir}/eduvpn/internet.png
%{_datarootdir}/eduvpn/internet_small.png
%{_datarootdir}/icons/hicolor/128x128/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/256x256/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/48x48/apps/eduvpn-client.png
%{_datarootdir}/icons/hicolor/512x512/apps/eduvpn-client.png

%changelog
