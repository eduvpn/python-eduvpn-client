from io import StringIO
from typing import Optional, Callable, Iterable, List
from gettext import gettext as _


class Item:
    def to_string(self) -> str:
        raise NotImplementedError

    def write(self, file):
        line = self.to_string()
        file.write(f'{line}\n')

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.__dict__ == other.__dict__

    def __repr__(self):
        fields = ','.join(f' {k}={v!r}' for k, v in self.__dict__.items())
        return f'<{self.__class__.__name__}{fields}>'


class Field(Item):
    def __init__(self, name: str, arguments: List[str]):
        self.name = name
        self.arguments = arguments

    def to_string(self):
        return f'{self.name} {" ".join(self.arguments)}'


class Section(Item):
    def __init__(self, tag: str, content: List[str]):
        self.tag = tag
        self.content = content

    def to_string(self):
        lines = []
        lines.append(f'<{self.tag}>')
        lines.extend(self.content)
        lines.append(f'</{self.tag}>')
        return '\n'.join(lines)


class Comment(Item):
    def __init__(self, content: str):
        self.content = content

    def to_string(self):
        return f'#{self.content}'


class Empty(Item):
    def to_string(self):
        return ''


class InvalidOVPN(Exception):
    pass


def parse_ovpn(lines: Iterable[str]) -> Iterable[Item]:
    current_section = None
    for lineno, line in enumerate(lines):
        if current_section is not None:
            if line.strip() == f'</{current_section.tag}>':
                yield current_section
                current_section = None
            else:
                current_section.content.append(line)
        elif line.startswith('#'):
            yield Comment(line.rstrip()[1:])
        elif line.startswith('<'):
            line = line.rstrip()
            assert line.endswith('>')
            section = Section(line[1:-1], [])
            current_section = section
        elif line.rstrip() == '':
            yield Empty()
        else:
            field_name, *arguments = line.rstrip().split()
            yield Field(field_name, arguments)
    assert current_section is None


class Ovpn:
    def __init__(self, content: List[Item]):
        self.content = content

    @classmethod
    def parse(cls, content: str) -> 'Ovpn':
        return cls(list(parse_ovpn(content.splitlines())))

    def write(self, file):
        for item in self.content:
            item.write(file)

    def to_string(self) -> str:
        file = StringIO()
        self.write(file)
        return file.getvalue()

    def contains_field(self, field_name: str) -> bool:
        for item in self.content:
            if isinstance(item, Field):
                if item.name == field_name:
                    return True
        return False

    def replace_fields(self, replace: Callable[[Field], Optional[Item]]):
        new_content = []
        for item in self.content:
            if isinstance(item, Field):
                replacement = replace(item)
                if replacement is not None:
                    new_content.append(replacement)
            else:
                new_content.append(item)
        self.content = new_content

    def force_tcp(self):
        def replacement(field):
            if field.name == 'remote' and field.arguments[2] == 'udp':
                return Comment(f' omitted to force tcp: {field.to_string()}')
            else:
                return field

        self.replace_fields(replacement)
        if not self.contains_field('remote'):
            raise InvalidOVPN(_(
                "This connection does not provide TCP connections. "
                "Disable the setting 'force-tcp' to use it."
            ))
