"""Registry for source parser and converter implementations."""


class ComponentRegistry:
    def __init__(self):
        self.parsers = {}
        self.converters = {}

    def register_parser(self, dialect, parser):
        self.parsers[dialect.lower()] = parser

    def get_parser(self, dialect):
        return self.parsers[dialect.lower()]
