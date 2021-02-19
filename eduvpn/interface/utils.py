from ..server import SecureInternetServer, OrganisationServer


class SecureInternetLocation:
    def __init__(self,
                 server: OrganisationServer,
                 location: SecureInternetServer):
        self.server = server
        self.location = location
