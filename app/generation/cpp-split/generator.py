# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

import pathlib
import re
from jinja2 import Environment, FileSystemLoader

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
        fragments = self.make_fragments(schema)
        self.generate_document('support.h', 'support.tmpl', schema=schema)
        for fragment in fragments:
            self.generate_document(f'{fragment["stem"]}.h', 'fragment.tmpl', schema=schema, fragment=fragment)
        self.generate_document('schema.h', 'schema.tmpl', schema=schema, schema_types=self.own_types(schema, fragments), fragments=fragments)

    '''
    Split schema types into per-source-file fragments.

    Types defined inside <xi:include>d files become fragments (emitted to
    <stem>.h in namespace <stem>), everything else stays in schema.h:
    - types defined in the main schema file (source_file == schema.source_file)
    - primitive types with no source file at all (source_file == '')

    NOTE: included files are expected to be self-contained: a type inside a
    fragment may only reference support types and types from the same
    fragment (included types are inlined into their parent encoding, so this
    is rarely a restriction in practice).
    '''
    @staticmethod
    def make_fragments(schema: dict) -> list:
        fragments = []
        fragment_by_file = {}
        seen = set()
        enclosing_types = list(schema['types'])
        if schema['header_type'].get('source_file') not in (None, '', schema['source_file']):
            # header type is normally already present in types, but guard anyway
            enclosing_types = [schema['header_type']] + enclosing_types
        for encoded_type in enclosing_types:
            source_file = encoded_type.get('source_file')
            if encoded_type.get('token') not in ('enum', 'set', 'composite'):
                continue
            if source_file in (None, '', schema['source_file']):
                continue
            key = (source_file, encoded_type['name'])
            if key in seen:
                continue
            seen.add(key)
            if source_file not in fragment_by_file:
                stem = Generator.fragment_stem(source_file)
                fragment = {
                    'source_file': source_file,
                    'stem': stem,
                    'namespace': stem,
                    'types': []
                }
                fragment_by_file[source_file] = fragment
                fragments.append(fragment)
            fragment_by_file[source_file]['types'].append(encoded_type)
        return fragments

    ''' Type definitions that stay in schema.h (own-schema and primitive types) '''
    @staticmethod
    def own_types(schema: dict, fragments: list) -> list:
        fragment_files = {f['source_file'] for f in fragments}
        return [t for t in schema['types'] if t.get('source_file') not in fragment_files]

    '''
    Convert a source file basename into a C++ identifier used for both the
    fragment header name ("common_types.xml" -> "common_types.h") and the
    fragment namespace.
    '''
    @staticmethod
    def fragment_stem(source_file: str) -> str:
        stem = source_file.removesuffix('.xml') if source_file.lower().endswith('.xml') else source_file
        stem = re.sub(r'[^A-Za-z0-9_]', '_', stem)
        if stem == '' or not re.match(r'[A-Za-z_]', stem[0]):
            stem = 'fragment_' + stem
        return stem


    def add_filters(self) -> None:
        self.env.filters['fmt_class_type'] = lambda s: s[0].upper() + s[1:]
        self.env.filters['fmt_class_ref'] = lambda s: s[0].upper() + s[1:] + 'Ref'
        self.env.filters['fmt_class_message'] = lambda s: s[0].upper() + s[1:]
        self.env.filters['fmt_class_group'] = lambda s: s[0].upper() + s[1:] + 'Group'
        self.env.filters['fmt_class_data'] = lambda s: s[0].upper() + s[1:] + 'Data'
        self.env.filters['fmt_enum_value'] = lambda s: s
        self.env.filters['to_cpp_type']  = Generator.to_cpp_type
        self.env.filters['to_cpp_value']  = Generator.to_cpp_value

    @staticmethod
    def to_cpp_type(primitive_type: dict) -> str:
        return {
            'int8':     'std::int8_t',
            'int16':    'std::int16_t',
            'int32':    'std::int32_t',
            'int64':    'std::int64_t',
            'uint8':    'std::uint8_t',
            'uint16':   'std::uint16_t',
            'uint32':   'std::uint32_t',
            'uint64':   'std::uint64_t',
            'double':   'double',
            'float':    'float',
            'char':     'char'
        }.get(primitive_type['name'])

    @staticmethod
    def to_cpp_value(value: str, primitive_type: dict) -> str:
        result = {
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
        }.get(value)
        if result:
            return result
        if primitive_type['name'] in ['uint8', 'uint16', 'uint32', 'uint64']:
            return value + 'u'
        return value




''' Bundle generation: several schemas into one destination via the cpp-split
    generator. Only cpp-split supports it because only it can split out the
    shared types. The resulting layout:

      <destination>/support.h         support types shared by every schema,
                                      namespace "sbe_code_gen"
      <destination>/<stem>.h          fragment header per unique xi:include'd
                                      file, namespace <stem>
      <destination>/<package>/schema.h
                                      one schema header per schema; <package>
                                      is the schema's package attribute with
                                      path components joined by '_' (a schema
                                      without a package is an error)

    Shared fragment headers are emitted once and included by every schema
    header, so types XIncluded by several schemas are the very same C++ types
    everywhere; a translation unit that uses two schemas of the bundle gets
    one shared copy of them.

    Constraints (checked, error out otherwise):
    - every schema must have a package attribute (it names its schema header)
    - all schemas must share the same byte order (support types depend on it)
    - all schemas must have the same version
    - all schemas must have the same message header type (fragment classes
      carry its field widths in their constructors)
    - every included file must be self-contained (same rule as for
      single-schema cpp-split) and a type name must be unique across all
      fragments of the bundle
'''
def generate_bundle(schemas: list, destination: str) -> None:
    irs = [GeneratorBase.make_ir(schema) for schema in schemas]

    if any(ir['package'] is None for ir in irs):
        raise Exception('bundle generation requires a package attribute on every schema')
    if len({ir['byte_order'] for ir in irs}) != 1:
        raise Exception('bundle generation requires all schemas to share the same byte order')
    if len({ir['version'] for ir in irs}) != 1:
        raise Exception('bundle generation requires all schemas to share the same version')
    if len({_header_type_key(ir['header_type']) for ir in irs}) != 1:
        raise Exception('bundle generation requires all schemas to share the same message header type')

    fragments = merge_fragment_lists([Generator.make_fragments(ir) for ir in irs])
    fragment_files = {f['source_file'] for f in fragments}

    bundle = Generator(destination)
    bundle.generate_document('support.h', 'support.tmpl', schema=irs[0])
    for fragment in fragments:
        bundle.generate_document(f'{fragment["stem"]}.h', 'fragment.tmpl', schema=irs[0], fragment=fragment)
    for ir in irs:
        package_dir = '_'.join(c.replace(' ', '_') for c in ir['package'])
        bundle.generate_document(
            f'{package_dir}/schema.h', 'schema.tmpl', schema=ir,
            schema_types=[t for t in ir['types'] if t.get('source_file') not in fragment_files],
            fragments=[f for f in fragments if f['source_file'] in referenced_fragment_files(ir, fragment_files)]
        )


''' header type definition with provenance-carrying attributes cleared, for
    comparing the header types of different schemas. Schemas may describe the
    same shared header through their own file or through an included file, so
    source_file must not participate in the comparison; everything else must
    be identical. '''
def _header_type_key(header_type: dict) -> str:
    def scrub(node):
        if isinstance(node, dict):
            return {k: scrub(v) for k, v in node.items() if k not in ('source_file', 'inplace')}
        if isinstance(node, list):
            return [scrub(v) for v in node]
        return node

    import json
    return json.dumps(scrub(header_type), sort_keys=True)


''' Files referenced by a schema ir (its types and its header type) that
    actually have fragments in the bundle '''
def referenced_fragment_files(schema_ir: dict, fragment_files: set) -> set:
    files = {t.get('source_file') for t in schema_ir['types']}
    files.add(schema_ir['header_type'].get('source_file'))
    return files & fragment_files


''' Merge per-schema fragment lists (one list per schema ir) into a single
    list of fragments. Fragments of the same included file are merged; type
    definitions with the same name must be identical, and type names must be
    unique across the whole bundle. '''
def merge_fragment_lists(fragment_lists: list) -> list:
    merged = {}
    order = []
    all_names = {}
    for fragments in fragment_lists:
        for fragment in fragments:
            existing = merged.get(fragment['source_file'])
            if existing is None:
                merged[fragment['source_file']] = fragment
                order.append(fragment['source_file'])
                existing = fragment
            else:
                if existing['stem'] != fragment['stem']:
                    raise Exception(
                        f'fragment stem clash for "{fragment["source_file"]}": '
                        f'"{existing["stem"]}" vs "{fragment["stem"]}"')
            for encoded_type in fragment['types']:
                name = encoded_type['name']
                known = all_names.get(name)
                if known is not None and known['source_file'] != existing['source_file']:
                    raise Exception(
                        f'type name "{name}" is defined in two included files of the bundle: '
                        f'"{known["source_file"]}" and "{existing["source_file"]}"')
                stored = next((t for t in existing['types'] if t['name'] == name), None)
                if stored is None:
                    existing['types'].append(encoded_type)
                    all_names[name] = encoded_type
                elif stored != encoded_type:
                    raise Exception(
                        f'type "{name}" from "{existing["source_file"]}" differs between schemas in the bundle')
    return [merged[file] for file in order]
