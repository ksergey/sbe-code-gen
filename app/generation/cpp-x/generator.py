# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

from jinja2 import Environment, FileSystemLoader
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

        for encoded_type in schema['types']:
            type_class_name = self.env.filters['fmt_class_type'](encoded_type['name'])
            type_class_h_file = self.env.filters['fmt_header_name'](type_class_name)
            if encoded_type['token'] == 'type':
                pass
            elif encoded_type['token'] == 'composite':
                print(f'Cenerating composite type {type_class_name} (to {type_class_h_file})')
                self.generate_document(type_class_h_file, 'composite.tmpl', type=encoded_type, schema=schema)
            elif encoded_type['token'] == 'enum':
                print(f'Cenerating enum type {type_class_name} (to {type_class_h_file})')
                self.generate_document(type_class_h_file, 'enum.tmpl', type=encoded_type, schema=schema)
            elif encoded_type['token'] == 'set':
                print(f'Cenerating set type {type_class_name} (to {type_class_h_file})')
                self.generate_document(type_class_h_file, 'set.tmpl', type=encoded_type, schema=schema)

        for message in schema['messages']:
            message_class_name = self.env.filters['fmt_class_message'](message['name'])
            message_class_h_file = self.env.filters['fmt_header_name'](message_class_name)
            print(f'Generating message {message_class_name} (to {message_class_h_file})')
            self.generate_document(message_class_h_file, 'message.tmpl', message=message, schema=schema)

        self.generate_document('common.h', 'common.tmpl', schema=schema)

    def make_document_name(self, name: str) -> str:
        return self.env.filters['format_class_name'](name) + '.h'

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
        self.env.filters['format_class_name'] = lambda value: value[0].upper() + value[1:]
        self.env.filters['format_method_name_prefix'] = lambda value: value[0].lower() + value[1:]
        self.env.filters['format_method_name_suffix'] = lambda value: value[0].upper() + value[1:]

        self.env.filters['replace_keyword']  = Generator.filter_replace_keyword
        self.env.filters['fmt_class_name'] = lambda value: value[0].upper() + value[1:]
        self.env.filters['fmt_field_ref'] = lambda value: value[0].upper() + value[1:] + 'Ref'
        self.env.filters['lower_first'] = lambda value: value[0].lower() + value[1:]
        self.env.filters['upper_first'] = lambda value: value[0].upper() + value[1:]

        self.env.filters['fmt_class_type'] = lambda s: s[0].upper() + s[1:]
        self.env.filters['fmt_class_ref'] = lambda s: s[0].upper() + s[1:] + 'Ref'
        self.env.filters['fmt_class_message'] = lambda s: s[0].upper() + s[1:]
        self.env.filters['fmt_class_group'] = lambda s: s[0].upper() + s[1:] + 'Group'
        self.env.filters['fmt_class_data'] = lambda s: s[0].upper() + s[1:] + 'Data'
        self.env.filters['fmt_header_name'] = lambda s: s + '.h'

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
