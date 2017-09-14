from setuptools import setup, find_packages

__version__ = "0.7.2"


install_requires = [
    'requests',
    'pynacl',
    'requests_oauthlib',
    'future',
    'configparser',
    'dbus-python',
]

extras_require = {
    'nm': ['python-networkmanager'],
    'ui': ['pygobject'],
    'osx': ['pync'],
}

scripts = [
    'scripts/eduvpn-client',
]

data_files = [
    ('share/applications', ['share/applications/eduvpn-client.desktop']),
    ('share/eduvpn', [
        'share/eduvpn/eduvpn.png',
        'share/eduvpn/eduvpn.ui',
        'share/eduvpn/institute.png',
        'share/eduvpn/institute_small.png',
        'share/eduvpn/internet.png',
        'share/eduvpn/internet_small.png',
    ]),
    ('share/icons/hicolor/48x48/apps', ['share/icons/hicolor/48x48/apps/eduvpn-client.png']),
    ('share/icons/hicolor/128x128/apps', ['share/icons/hicolor/128x128/apps/eduvpn-client.png']),
    ('share/icons/hicolor/256x256/apps', ['share/icons/hicolor/256x256/apps/eduvpn-client.png']),
    ('share/icons/hicolor/512x512/apps', ['share/icons/hicolor/512x512/apps/eduvpn-client.png']),
]


setup(
    name="eduvpn_client",
    version=__version__,
    packages=find_packages(),
    scripts=scripts,
    data_files=data_files,
    install_requires=install_requires,
    extras_require=extras_require,
    author="Gijs Molenaar",
    author_email="gijs@pythonic.nl",
    description="eduVPN client",
    license="GPL3",
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'mock'],
    test_suite="tests",
    keywords="vpn openvpn networking security",
    url="https://github.com/eduvpn/eduvpn-linux-client",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: System :: Operating System Kernels :: Linux",
        "Topic :: System :: Networking",
        "Environment :: X11 Applications",
        ]
)
