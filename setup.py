from setuptools import setup, find_packages

__version__ = "0.1"


install_requires = [
    'requests',
    'pynacl',
    'requests_oauthlib',
    'python-networkmanager',
    'future',
    'configparser',
]

scripts = [
    'scripts/eduvpn-client',
]

setup(
    name="eduvpn_client",
    version=__version__,
    packages=find_packages(),
    scripts=scripts,
    install_requires=install_requires,
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
