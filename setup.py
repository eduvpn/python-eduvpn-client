import os
from setuptools import setup, find_packages

__version__ = "1.9.0"

tests_require = [
        'pytest',
        'PyGObject-stubs',
        'mypy',
        'pycodestyle',
],

install_requires = [
    'requests',
    'requests_oauthlib',
    'cryptography',
    'pynacl',
    'pygobject',
    'wheel'
]

extras_require = {
    'client': ['pygobject'],
    'test': tests_require,
}

def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths

extra_files = package_files('share')

setup(
    name="eduvpn_client",
    version=__version__,
    packages=find_packages(),
    package_data={'': extra_files},
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
            'eduvpn-client = eduvpn.__main__:eduvpn',
            'letsconnect-client = eduvpn.__main__:letsconnect',
         ],
        'gui_scripts': [
            'eduvpn-gui = eduvpn.ui.__main__:main',
            'letsconnectgui = eduvpn.ui.__main__:letsconnect',
        ]
    }
)
