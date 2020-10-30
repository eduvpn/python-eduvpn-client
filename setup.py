import os

from setuptools import setup, find_packages

__version__ = "1.9.1"

tests_require = [
    'pytest',
    'PyGObject-stubs',
    'mypy',
    'pycodestyle',
]

install_requires = [
    'requests',
    'requests_oauthlib',
    'cryptography',
    'pynacl',
    'wheel',
]

extras_require = {
    'gui': ['dbus-python', 'pygobject'],
    'test': tests_require,
}


def extra_files_line(dir_: str):
    return dir_, [os.path.join(dir_, i) for i in os.listdir(dir_) if os.path.isfile(os.path.join(dir_, i))]


data_files = [
    extra_files_line('share/applications'),
    extra_files_line('share/eduvpn'),
    extra_files_line('share/eduvpn/builder'),
    extra_files_line('share/eduvpn/images'),
    extra_files_line('share/eduvpn/images/flags'),
    extra_files_line('share/letsconnect/images'),
    extra_files_line('share/icons/hicolor/48x48/apps'),
    extra_files_line('share/icons/hicolor/128x128/apps'),
    extra_files_line('share/icons/hicolor/256x256/apps'),
    extra_files_line('share/icons/hicolor/512x512/apps'),
]

setup(
    name="eduvpn_client",
    version=__version__,
    packages=find_packages(),
    data_files=data_files,
    install_requires=install_requires,
    extras_require=extras_require,
    author="Gijs Molenaar",
    author_email="gijs@pythonic.nl",
    description="eduVPN client",
    license="GPL3",
    setup_requires=['pytest-runner'],
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
