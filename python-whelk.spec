%if 0%{?fedora} > 12
%global with_python3 1
%else
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print (get_python_lib())")}
%endif

%global srcname distribute
Name:           python-whelk
Version:        2.5.1
Release:        1%{?dist}
Summary:        Pretending python is a shell

License:        zlib
URL:            https://github.com/seveas/whelk
Source0:        http://pypi.python.org/packages/source/w/whelk/whelk-%{version}.tar.gz

%if 0%{?with_python3}
BuildRequires:  python3-devel
%endif

BuildRequires:  python2-devel

BuildArch:      noarch

%description
We all like python for scripting, because it's so much more powerful than a
shell. But sometimes we really need to call a shell command because it's so
much easier than writing yet another library in python or adding a dependency.

%if 0%{?with_python3}
%package -n python3-whelk
Summary:        Pretending python is a shell
%description -n python3-whelk
We all like python for scripting, because it's so much more powerful than a
shell. But sometimes we really need to call a shell command because it's so
much easier than writing yet another library in python or adding a dependency.
%endif

%prep
%setup -q -n whelk-%{version}

# remove upstream egg-info
rm -rf *.egg-info

# make a copy for python3 install
%if 0%{?with_python3}
rm -rf %{py3dir}
cp -a . %{py3dir}
%endif

%build
%{__python} setup.py build

%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py build
popd
%endif

%install
%{__python} setup.py install --skip-build --root $RPM_BUILD_ROOT
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py install --skip-build --root $RPM_BUILD_ROOT
popd
%endif 

%check

%files
%{python_sitelib}/whelk/*.py*
%{python_sitelib}/whelk-*.egg-info
%if 0%{?with_python3}
%files -n python3-whelk
%{python3_sitelib}/whelk/*py*
%{python3_sitelib}/whelk-*.egg-info
%endif

%changelog
* Sun Nov 01 2015 Dennis Kaarsemaker <dennis@kaarsemaker.net> - 2.5-1
- Initial package. See git tree for changelog.
