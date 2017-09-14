%global srcname eduvpn_client
%global sum client for eduVPN

Name:           eduvpn-client
Version:        0.7.2
Release:        1%{?dist}
Summary:        %{sum}

License:        MIT
URL:            https://pypi.python.org/pypi/%{srcname}
Source0:        https://files.pythonhosted.org/packages/source/e/%{srcname}/%{srcname}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python2-devel python3-devel

%description
An python module which provides a convenient example.

%package -n python2-%{srcname}
Summary:        %{sum}
%{?python_provide:%python_provide python2-%{srcname}}

%description -n python2-%{srcname}
eduVPN client API for Python2


%package -n python3-%{srcname}
Summary:        %{sum}
%{?python_provide:%python_provide python3-%{srcname}}

%description -n python3-%{srcname}
eduVPN client API for Python3


%package -n %{Name}
Summary: %[sum}

%description -n %{Name}
eduVPN desktop client


%prep
%autosetup -n %{srcname}-%{version}

%build
%py2_build
%py3_build

%install
# Must do the python2 install first because the scripts in /usr/bin are
# overwritten with every setup.py install, and in general we want the
# python3 version to be the default.
# If, however, we're installing separate executables for python2 and python3,
# the order needs to be reversed so the unversioned executable is the python2 one.
%py2_install
%py3_install

#%check
#%{__python2} setup.py test
#%{__python3} setup.py test

# Note that there is no %%files section for the unversioned python module if we are building for several python runtimes
%files -n python2-%{srcname}
%license LICENSE
%doc README.md
%{python2_sitelib}/*

%files -n python3-%{srcname}
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
