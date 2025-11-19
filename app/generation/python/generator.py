# Copyright (C) 2024 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

from jinja2 import Environment, FileSystemLoader
from typing import Optional
import pathlib
import os
import re
import numpy as np

from app.generator import GeneratorBase

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
        self.ensure_path_exists()
        self.generate_document('schema.py', 'schema.tmpl', schema=schema)

    def generate_document(self, document_name: str, template_name: str, **kwargs) -> None:
        template = self.env.get_template(template_name)
        document_path = f'{self.path}/{document_name}'
        document_content = template.render(**kwargs)
        with open(document_path, mode='w', encoding='utf8') as document:
            document.write(document_content)

    def ensure_path_exists(self) -> None:
        if not os.path.exists(self.path):
            os.makedirs(self.path)

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
        return {
            'CHAR_NULL':    0,
            'CHAR_MIN':     0x20,
            'CHAR_MAX':     0x7e,
            'INT8_NULL':    np.iinfo(np.int8).min,
            'INT8_MIN':     np.iinfo(np.int8).min + 1,
            'INT8_MAX':     np.iinfo(np.int8).max,
            'INT16_NULL':   np.iinfo(np.int16).min,
            'INT16_MIN':    np.iinfo(np.int16).min + 1,
            'INT16_MAX':    np.iinfo(np.int16).max,
            'INT32_NULL':   np.iinfo(np.int32).min,
            'INT32_MIN':    np.iinfo(np.int32).min + 1,
            'INT32_MAX':    np.iinfo(np.int32).max,
            'INT64_NULL':   np.iinfo(np.int64).min,
            'INT64_MIN':    np.iinfo(np.int64).min + 1,
            'INT64_MAX':    np.iinfo(np.int64).max,
            'UINT8_NULL':   np.iinfo(np.uint8).max,
            'UINT8_MIN':    np.iinfo(np.uint8).min,
            'UINT8_MAX':    np.iinfo(np.uint8).max - 1,
            'UINT16_NULL':  np.iinfo(np.uint16).max,
            'UINT16_MIN':   np.iinfo(np.uint16).min,
            'UINT16_MAX':   np.iinfo(np.uint16).max - 1,
            'UINT32_NULL':  np.iinfo(np.uint32).max,
            'UINT32_MIN':   np.iinfo(np.uint32).min,
            'UINT32_MAX':   np.iinfo(np.uint32).max - 1,
            'UINT64_NULL':  np.iinfo(np.uint64).max,
            'UINT64_MIN':   np.iinfo(np.uint64).min,
            'UINT64_MAX':   np.iinfo(np.uint64).max - 1,
            'FLOAT_NULL':   np.float32(np.nan),
            'FLOAT_MIN':    np.finfo(np.float32).min,
            'FLOAT_MAX':    np.finfo(np.float32).max,
            'DOUBLE_NULL':  np.float64(np.nan),
            'DOUBLE_MIN':   np.finfo(np.float64).min,
            'DOUBLE_MAX':   np.finfo(np.float64).max
        }.get(value, value)
