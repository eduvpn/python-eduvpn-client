# python-eduvpn-client - The GNU/Linux eduVPN client and Python API
#
# Copyright: 2017, The Commons Conservancy eduVPN Programme
# SPDX-License-Identifier: GPL-3.0+

from setuptools import setup, find_packages

__version__ = "1.0.2"


install_requires = [
    'requests',
    'pynacl',
    'requests_oauthlib',
    'future',
    'python-dateutil',
    'six',
    'repoze.lru',
    'qrcode',
    'pillow',
    'cryptography',
]

# sometimes the dbus-python package is not properly registered, triggering a
# reinstall and compile
extras_require = {
    'client': ['dbus-python', 'pygobject'],
    'test-online': ['mechanicalsoup', 'futures'],
}

data_files = [
    ('share/applications', ['share/applications/lets-connect-client.desktop']),
    ('share/eduvpn', [
        'share/eduvpn/eduvpn.png',
        'share/eduvpn/institute.png',
        'share/eduvpn/institute_small.png',
        'share/eduvpn/internet.png',
        'share/eduvpn/internet_small.png',
    ]),
    ('share/letsconnect', [
        'share/letsconnect/connected.png',
        'share/letsconnect/connecting.png',
        'share/letsconnect/disconnected.png',
        'share/letsconnect/fallback.png',
        'share/letsconnect/settings_full.png',
        'share/letsconnect/settings.png',
        'share/letsconnect/tray.png',
    ]),
    ('share/eduvpn/builder', [
        'share/eduvpn/builder/2fa.ui',
        'share/eduvpn/builder/connection_type.ui',
        'share/eduvpn/builder/custom_url.ui',
        'share/eduvpn/builder/fetch.ui',
        'share/eduvpn/builder/instances.ui',
        'share/eduvpn/builder/profiles.ui',
        'share/eduvpn/builder/redirecturl.ui',
        'share/eduvpn/builder/token.ui',
        'share/eduvpn/builder/totp_enroll.ui',
        'share/eduvpn/builder/window.ui',
        'share/eduvpn/builder/yubi_enroll.ui',
    ]),
    ('share/icons/hicolor/48x48/apps', ['share/icons/hicolor/48x48/apps/eduvpn-client.png']),
    ('share/icons/hicolor/128x128/apps', ['share/icons/hicolor/128x128/apps/eduvpn-client.png']),
    ('share/icons/hicolor/256x256/apps', ['share/icons/hicolor/256x256/apps/eduvpn-client.png']),
    ('share/icons/hicolor/512x512/apps', ['share/icons/hicolor/512x512/apps/eduvpn-client.png']),
    ('share/icons/hicolor/48x48/apps', ['share/icons/hicolor/48x48/apps/lets-connect-client.png']),
    ('share/icons/hicolor/128x128/apps', ['share/icons/hicolor/128x128/apps/lets-connect-client.png']),
    ('share/icons/hicolor/256x256/apps', ['share/icons/hicolor/256x256/apps/lets-connect-client.png']),
    ('share/icons/hicolor/512x512/apps', ['share/icons/hicolor/512x512/apps/lets-connect-client.png']),
]


setup(
    name="lets_connect_client",
    version=__version__,
    packages=find_packages(),
    data_files=data_files,
    install_requires=install_requires,
    extras_require=extras_require,
    author="Gijs Molenaar",
    author_email="gijs@pythonic.nl",
    description="Let's Connect! client",
    license="GPL3",
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'mock'],
    test_suite="tests",
    keywords="vpn openvpn networking security",
    url="https://github.com/eduvpn/python-eduvpn-client",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
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
        ],
    entry_points={
        'gui_scripts': [
            'lets-connect-client = eduvpn.main:main_lets_connect',
        ]
}
)
