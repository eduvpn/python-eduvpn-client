import pkg_resources

try:
    __version__ = pkg_resources.require("kliko")[0].version
except pkg_resources.DistributionNotFound:
    __version__ = "0.0dev"