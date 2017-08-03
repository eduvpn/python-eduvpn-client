from setuptools import setup, find_packages

__version__ = "0.2.1"


install_requires = [
    'requests',
    'pynacl',
    'requests_oauthlib',
    'future',
    'configparser',
]

extras_require = {
    'nm': ['python-networkmanager'],
    'ui': ['pygobject'],
}

scripts = [
    'scripts/eduvpn-client',
]

data_files = [
    ('share/applications', ['data/eduvpn-client.desktop']),
    ('share/icons/hicolor/48x48/apps', ['data/icons/hicolor/48x48/apps/eduvpn-client.png']),
    ('share/icons/hicolor/128x128/apps', ['data/icons/hicolor/128x128/apps/eduvpn-client.png']),
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
    description="EduVPN client",
    license="GPL3",
    keywords="vpn openvpn networking security",
    url="https://github.com/gijzelaerr/eduvpn-linux-client",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2.7",
        "Topic :: System :: Operating System Kernels :: Linux",
        ]
)
