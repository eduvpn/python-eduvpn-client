import re


# matches for example: remote vpn.example.com 1234 udp
# NOTE: multiline-mode does not consider \r
#       so we must match for that explicitly.
FIND_REMOTE_UDP_LINES = re.compile(
    r'^(remote +\S+ +[0-9]+ +udp\r?)$',
    re.MULTILINE
)


class Ovpn:
    def __init__(self, content: str):
        self.content = content

    def write(self, file):
        file.write(self.content)

    def force_tcp(self):
        self.content = FIND_REMOTE_UDP_LINES.sub(
            r'# omitted to force tcp: \1',
            self.content,
        )
