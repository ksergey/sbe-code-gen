# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

from jinja2 import Environment, FileSystemLoader
from typing import Optional
import pathlib
import os

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

        self.generate_document('mp.h', 'mp.h')
        self.generate_document('typing.h', 'typing.h')
        self.generate_document('schema.h', 'schema.tmpl', schema=schema, includes=self.generate_includes(schema))

        for encoded_type in schema['types']:
            document_name = self.make_document_name(encoded_type['name'])
            if encoded_type['token'] == 'type':
                pass
            elif encoded_type['token'] == 'composite':
                self.generate_document(document_name, 'composite.tmpl', type=encoded_type, schema=schema,
                                       includes=self.generate_includes_for_composite(encoded_type))
            elif encoded_type['token'] == 'enum':
                self.generate_document(document_name, 'enum.tmpl', type=encoded_type, schema=schema)
            elif encoded_type['token'] == 'set':
                self.generate_document(document_name, 'set.tmpl', type=encoded_type, schema=schema)

        for message in schema['messages']:
            document_name = self.make_document_name(message['name'])
            self.generate_document(document_name, 'message.tmpl', message=message, schema=schema,
                                  includes=self.generate_includes_for_message(message, schema))

    def make_document_name(self, name: str) -> str:
        return self.env.filters['format_class_name'](name) + '.h'

    def generate_document(self, document_name: str, template_name: str, **kwargs) -> None:
        template = self.env.get_template(template_name)
        document_path = f'{self.path}/{document_name}'
        document_content = template.render(**kwargs)
        with open(document_path, mode='w', encoding='utf8') as document:
            document.write(document_content)

    def generate_includes_for_message(self, message: dict, schema: dict = None) -> list:
        includes = set()
        for field in message['fields']:
            if field['token'] == 'field':
                if field['type']['token'] in ('composite', 'enum', 'set'):
                    includes.add(self.make_document_name(field['type']['name']))
            elif field['token'] == 'group':
                includes.add(self.make_document_name(field['dimension_type']['name']))
                # this func could be used for iterate over group fields
                includes = includes.union(self.generate_includes_for_message(field))
            elif field['token'] == 'data':
                includes.add(self.make_document_name(field['type']['name']))
        if schema != None:
            includes.add(self.make_document_name(schema['header_type']['name']))
        includes.add('typing.h')

        return list(includes)

    def generate_includes_for_composite(self, composite: dict) -> list:
        includes = set()
        for field in composite['contained_types']:
            if field['token'] in ('composite', 'enum', 'set') and not field['inplace']:
                includes.add(self.make_document_name(field['name']))
        includes.add('typing.h')

        return list(includes)

    def generate_includes(self, schema: dict) -> list:
        includes = set()
        for message in schema['messages']:
            includes.add(self.make_document_name(message['name']))

        return list(includes)

    def ensure_path_exists(self) -> None:
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def add_filters(self) -> None:
        self.env.filters['format_class_name'] = lambda value: value[0].upper() + value[1:]
        self.env.filters['replace_keyword']  = Generator.filter_replace_keyword
        self.env.filters['format_group_name'] = lambda value: value[0].upper() + value[1:] + 'Group'
        self.env.filters['format_data_name'] = lambda value: value[0].upper() + value[1:] + 'Data'

        self.env.filters['format_encoding_class_name'] = lambda value: value[0].upper() + value[1:] + 'Encoding'

    @staticmethod
    def filter_replace_keyword(value: str) -> str:
        return {
            'int8':         'std::int8_t',
            'int16':        'std::int16_t',
            'int32':        'std::int32_t',
            'int64':        'std::int64_t',
            'uint8':        'std::uint8_t',
            'uint16':       'std::uint16_t',
            'uint32':       'std::uint32_t',
            'uint64':       'std::uint64_t',
            'CHAR_NULL':    '0',
            'CHAR_MIN':     '0x20',
            'CHAR_MAX':     '0x7e',
            'INT8_NULL':    'std::numeric_limits<std::int8_t>::min()',
            'INT8_MIN':     'std::numeric_limits<std::int8_t>::min() + 1',
            'INT8_MAX':     'std::numeric_limits<std::int8_t>::max()',
            'INT16_NULL':   'std::numeric_limits<std::int16_t>::min()',
            'INT16_MIN':    'std::numeric_limits<std::int16_t>::min() + 1',
            'INT16_MAX':    'std::numeric_limits<std::int16_t>::max()',
            'INT32_NULL':   'std::numeric_limits<std::int32_t>::min()',
            'INT32_MIN':    'std::numeric_limits<std::int32_t>::min() + 1',
            'INT32_MAX':    'std::numeric_limits<std::int32_t>::max()',
            'INT64_NULL':   'std::numeric_limits<std::int64_t>::min()',
            'INT64_MIN':    'std::numeric_limits<std::int64_t>::min() + 1',
            'INT64_MAX':    'std::numeric_limits<std::int64_t>::max()',
            'UINT8_NULL':   'std::numeric_limits<std::uint8_t>::max()',
            'UINT8_MIN':    'std::numeric_limits<std::uint8_t>::min()',
            'UINT8_MAX':    'std::numeric_limits<std::uint8_t>::max() - 1',
            'UINT16_NULL':  'std::numeric_limits<std::uint16_t>::max()',
            'UINT16_MIN':   'std::numeric_limits<std::uint16_t>::min()',
            'UINT16_MAX':   'std::numeric_limits<std::uint16_t>::max() - 1',
            'UINT32_NULL':  'std::numeric_limits<std::uint32_t>::max()',
            'UINT32_MIN':   'std::numeric_limits<std::uint32_t>::min()',
            'UINT32_MAX':   'std::numeric_limits<std::uint32_t>::max() - 1',
            'UINT64_NULL':  'std::numeric_limits<std::uint64_t>::max()',
            'UINT64_MIN':   'std::numeric_limits<std::uint64_t>::min()',
            'UINT64_MAX':   'std::numeric_limits<std::uint64_t>::max() - 1',
            'FLOAT_NULL':   'std::numeric_limits<float>::quiet_NaN()',
            'FLOAT_MIN':    'std::numeric_limits<float>::min()',
            'FLOAT_MAX':    'std::numeric_limits<float>::max()',
            'DOUBLE_NULL':  'std::numeric_limits<double>::quiet_NaN()',
            'DOUBLE_MIN':   'std::numeric_limits<double>::min()',
            'DOUBLE_MAX':   'std::numeric_limits<double>::max()'
        }.get(value, value)
