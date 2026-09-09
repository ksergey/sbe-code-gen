# Copyright (C) 2024 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

from jinja2 import Environment, FileSystemLoader
import pathlib

from app.generator import GeneratorBase
from app.constants import decode_primitive_constant

class Generator(GeneratorBase):
    def __init__(self, path: str) -> None:
        self.path = path
        self.env = Environment(
            loader = FileSystemLoader(f'{pathlib.Path(__file__).parent.resolve()}/templates'),
            autoescape = False,
            trim_blocks = True,
            lstrip_blocks = True,
            keep_trailing_newline = True
        )
        self.add_filters()

    def _generate_impl(self, schema: dict) -> None:
        self.generate_document('schema.py', 'schema.tmpl', schema=schema)

    def add_filters(self) -> None:
        self.env.filters['format_message_name'] = lambda value: value[0].upper() + value[1:] + 'Message'
        self.env.filters['format_composite_name'] = lambda value: value[0].upper() + value[1:]
        self.env.filters['format_enum_name'] = lambda value: value[0].upper() + value[1:]
        self.env.filters['format_set_name'] = lambda value: value[0].upper() + value[1:]
        self.env.filters['format_constant_name'] = lambda value: value if value not in ('True', 'False', 'None') else value + '_'
        self.env.filters['replace_keyword']  = Generator.filter_replace_keyword
        self.env.filters['bit_to_value'] = lambda value: 1 << int(value)
        self.env.filters['struct_fmt'] = Generator.filter_struct_fmt

    @staticmethod
    def filter_struct_fmt(value: str) -> str:
        return {
            'char': 'c',
            'int': 'i',
            'int8': 'b',
            'int16': 'h',
            'int32': 'i',
            'int64': 'q',
            'uint8': 'B',
            'uint16': 'H',
            'uint32': 'I',
            'uint64': 'Q',
            'float': 'f',
            'double': 'd'
        }.get(value)

    @staticmethod
    def filter_replace_keyword(value: str) -> str:
        return decode_primitive_constant(value)
