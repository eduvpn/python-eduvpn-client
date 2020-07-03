import pkg_resources

try:
    __version__: str = pkg_resources.require("eduvpngui")[0].version
except pkg_resources.DistributionNotFound:
    __version__: str = "0.0dev"
