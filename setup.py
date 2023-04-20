import os
from glob import glob

from setuptools import setup, find_packages

__version__ = "4.1.1"

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


install_requires = [
    'wheel',
    'eduvpn_common==1.1.0',
]

tests_require = [
    'pytest',
    'pycodestyle',
]

mypy_require = [
    'mypy',
    'PyGObject-stubs',
    'types-setuptools',
]

gui_require = [
    'dbus-python',
    'pygobject',
]

extras_require = {
    'gui': gui_require,
    'test': tests_require,
    'mypy': mypy_require,
}


def extra_files_line(dir_: str):
    return dir_, [os.path.join(dir_, i) for i in os.listdir(dir_) if os.path.isfile(os.path.join(dir_, i))]


data_files = [
    extra_files_line('share/applications'),
    extra_files_line('share/eduvpn'),
    extra_files_line('share/eduvpn/builder'),
    extra_files_line('share/eduvpn/images'),
    extra_files_line('share/eduvpn/images/flags/png'),
    extra_files_line('share/letsconnect/images'),
    extra_files_line('share/icons/hicolor/48x48/apps'),
    extra_files_line('share/icons/hicolor/128x128/apps'),
    extra_files_line('share/icons/hicolor/256x256/apps'),
    extra_files_line('share/icons/hicolor/512x512/apps'),
]
for dir in glob('share/locale/*/LC_MESSAGES'):
    data_files.append([dir, glob(os.path.join(dir,'*.mo'))])

setup(
    name="eduvpn_client",
    version=__version__,
    packages=find_packages(exclude=['tests']),
    data_files=data_files,
    install_requires=install_requires,
    extras_require=extras_require,
    author="Jeroen Wijenbergh",
    author_email="jeroen.wijenbergh@geant.org",
    description="eduVPN client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GPL3",
    setup_requires=[],
    tests_require=tests_require,
    test_suite="tests",
    keywords="vpn openvpn networking security",
    url="https://github.com/eduvpn/python-eduvpn-client",
    python_requires='>=3.6',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: System :: Operating System Kernels :: Linux",
        "Topic :: System :: Networking",
        "Environment :: X11 Applications",
    ],
    entry_points={
        'console_scripts': [
            'eduvpn-cli = eduvpn.cli:eduvpn',
            'letsconnect-cli = eduvpn.cli:letsconnect',
        ],
        'gui_scripts': [
            'eduvpn-gui = eduvpn.ui.__main__:eduvpn',
            'letsconnect-gui = eduvpn.ui.__main__:letsconnect',
        ]
    }
)
