import pkg_resources

try:
    __version__: str = pkg_resources.require("eduvpn")[0].version
except pkg_resources.DistributionNotFound:
    __version__ = "0.0dev"
