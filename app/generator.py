# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from app.schema import *

class GeneratorBase(ABC):
    @abstractmethod
    def _generate_impl(self, schema: dict) -> None:
        pass

    def generate(self, schema: Schema) -> None:
        ir = {}
        if schema.package != None:
            ir['package'] = schema.package.split('.')
        else:
            ir['package'] = None
        ir['id'] = schema.id
        ir['version'] = schema.version
        ir['byte_order'] = schema.byte_order.value
        ir['description'] = schema.description
        ir['header_type'] = GeneratorBase.make_encoded_type_definition(schema.header_type)
        ir['types'] = []
        for encoded_type in schema.types.values():
            ir['types'].append(GeneratorBase.make_encoded_type_definition(encoded_type))
        ir['messages'] = []
        for message in schema.messages.values():
            ir['messages'].append(GeneratorBase.make_message_definition(message))
        self._generate_impl(ir)

    @staticmethod
    def make_encoded_type_definition(encoded_type: EncodedType) -> dict:
        assert isinstance(encoded_type, (Type, Composite, Enum, Set))
        if isinstance(encoded_type, Type):
            return GeneratorBase.make_type_definition(encoded_type)
        if isinstance(encoded_type, Composite):
            return GeneratorBase.make_composite_definition(encoded_type)
        if isinstance(encoded_type, Enum):
            return GeneratorBase.make_enum_definition(encoded_type)
        if isinstance(encoded_type, Set):
            return GeneratorBase.make_set_definition(encoded_type)

    @staticmethod
    def make_type_definition(type_type: Type) -> dict:
        return {
            'token': 'type',
            'name': type_type.name,
            'description': type_type.description,
            'presence': type_type.presence.value,
            'null_value': type_type.null_value if type_type.null_value != None else type_type.primitive_type.null_value,
            'min_value': type_type.min_value if type_type.min_value != None else type_type.primitive_type.min_value,
            'max_value': type_type.max_value if type_type.max_value != None else type_type.primitive_type.max_value,
            'length': type_type.length,
            'offset': type_type.offset,
            'primitive_type': type_type.primitive_type.name, # if type_type.character_encoding != None else 'char',
            'semantic_type': type_type.semantic_type,
            'since_version': type_type.since_version,
            'deprecated': type_type.deprecated,
            'const_value': type_type.const_value,
            'character_encoding': type_type.character_encoding,
            'encoded_length': type_type.encoded_length(),
            'inplace': type_type.inplace
        }

    @staticmethod
    def make_composite_definition(composite_type: Composite) -> dict:
        contained_types = []
        for contained_type in composite_type.contained_types.values():
            assert isinstance(contained_type, (Type, Composite, Enum, Set, Ref))
            entry = None
            if isinstance(contained_type, Type):
                entry = GeneratorBase.make_type_definition(contained_type)
            elif isinstance(contained_type, Composite):
                entry = GeneratorBase.make_composite_definition(contained_type)
            elif isinstance(contained_type, Enum):
                entry = GeneratorBase.make_enum_definition(contained_type)
            elif isinstance(contained_type, Set):
                entry = GeneratorBase.make_set_definition(contained_type)
            elif isinstance(contained_type, Ref):
                entry = GeneratorBase.make_encoded_type_definition(contained_type.type)
                entry['name'] = contained_type.type.name
                entry['offset'] = contained_type.offset
                entry['description'] = contained_type.description
                entry['since_version'] = contained_type.since_version
                entry['deprecated'] = contained_type.deprecated
            entry['reference_name'] = contained_type.name
            contained_types.append(entry)

        return {
            'token': 'composite',
            'name': composite_type.name,
            'offset': composite_type.offset,
            'description': composite_type.description,
            'semantic_type': composite_type.semantic_type,
            'since_version': composite_type.since_version,
            'deprecated': composite_type.deprecated,
            'contained_types': contained_types,
            'encoded_length': composite_type.encoded_length(),
            'inplace': composite_type.inplace
        }

    @staticmethod
    def make_enum_definition(enum_type: Enum) -> dict:
        valid_values = []
        for valid_value in enum_type.valid_value_by_name.values():
            valid_values.append({
                'name': valid_value.name,
                'value': valid_value.value,
                'description': valid_value.description,
                'since_version': valid_value.since_version,
                'deprecated': valid_value.deprecated
            })
        return {
            'token': 'enum',
            'name': enum_type.name,
            'description': enum_type.description,
            'presence': enum_type.presence.value,
            'encoding_type': enum_type.encoding_type.name,
            'since_version': enum_type.since_version,
            'deprecated': enum_type.deprecated,
            'offset': enum_type.offset,
            'null_value': enum_type.null_value if enum_type.null_value != None else enum_type.encoding_type.null_value,
            'valid_values': valid_values,
            'encoded_length': enum_type.encoded_length(),
            'inplace': enum_type.inplace
        }

    @staticmethod
    def make_set_definition(set_type: Set) -> dict:
        choices = []
        for choice in set_type.choice_by_name.values():
            choices.append({
                'name': choice.name,
                'value': choice.value,
                'description': choice.description,
                'since_version': choice.since_version,
                'deprecated': choice.deprecated
            })
        return {
            'token': 'set',
            'name': set_type.name,
            'description': set_type.description,
            'presence': set_type.presence.value,
            'encoding_type': set_type.encoding_type.name,
            'since_version': set_type.since_version,
            'deprecated': set_type.deprecated,
            'offset': set_type.offset,
            'choices': choices,
            'encoded_length': set_type.encoded_length(),
            'inplace': set_type.inplace
        }

    @staticmethod
    def make_field_definition(field: Field) -> dict:
        return {
            'token': 'field',
            'name': field.name,
            'id': field.id,
            'description': field.description,
            'type': GeneratorBase.make_encoded_type_definition(field.type),
            'offset': field.offset,
            'presence': field.presence.value,
            'value_ref': field.value_ref,
            'semantic_type': field.semantic_type,
            'since_version': field.since_version,
            'deprecated': field.deprecated
        }

    @staticmethod
    def make_group_definition(group: Group) -> dict:
        fields = []
        for field in group.fields.values():
            assert isinstance(field, (Field, Group, Data))
            entry = None
            if isinstance(field, Field):
                entry = GeneratorBase.make_field_definition(field)
            elif isinstance(field, Group):
                entry = GeneratorBase.make_group_definition(field)
            elif isinstance(field, Data):
                entry = GeneratorBase.make_data_definition(field)
            fields.append(entry)

        return {
            'token': 'group',
            'name': group.name,
            'id': group.id,
            'description': group.description,
            'dimension_type': GeneratorBase.make_encoded_type_definition(group.dimension_type),
            'block_length': group.block_length,
            'fields': fields
        }

    @staticmethod
    def make_data_definition(data: Data) -> dict:
        return {
            'token': 'data',
            'name': data.name,
            'id': data.id,
            'description': data.description,
            'type': GeneratorBase.make_encoded_type_definition(data.type),
            'semantic_type': data.semantic_type,
            'since_version': data.since_version,
            'deprecated': data.deprecated
        }

    @staticmethod
    def make_message_definition(message: Message) -> dict:
        fields = []
        for field in message.fields.values():
            assert isinstance(field, (Field, Group, Data))
            entry = None
            if isinstance(field, Field):
                entry = GeneratorBase.make_field_definition(field)
            elif isinstance(field, Group):
                entry = GeneratorBase.make_group_definition(field)
            elif isinstance(field, Data):
                entry = GeneratorBase.make_data_definition(field)
            fields.append(entry)

        return {
            'token': 'message',
            'name': message.name,
            'id': message.id,
            'description': message.description,
            'block_length': message.block_length,
            'semantic_type': message.semantic_type,
            'since_version': message.since_version,
            'deprecated': message.deprecated,
            'fields': fields
        }
