# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, Union
import os
from app.schema import *

class GeneratorBase(ABC):
    @abstractmethod
    def _generate_impl(self, schema: dict) -> None:
        pass

    def generate(self, schema: Schema, package: Optional[str] = None) -> None:
        ir = {}
        if not package:
            ir['package'] = schema.package.split('.') if schema.package else None
        else:
            ir['package'] = package.split('.')
        ir['id'] = schema.id
        ir['version'] = schema.version
        ir['byte_order'] = schema.byte_order.value
        ir['description'] = schema.description
        ir['header_type'] = GeneratorBase.make_encoded_type_definition(schema.header_type)
        ir['types'] = [GeneratorBase.make_encoded_type_definition(t) for t in schema.types.values()]
        ir['messages'] = [GeneratorBase.make_message_definition(m) for m in schema.messages.values()]
        self._generate_impl(ir)

    def generate_document(self, document_name: str, template_name: str, **kwargs) -> None:
        template = self.env.get_template(template_name)
        document_path = f'{self.path}/{document_name}'
        document_content = template.render(**kwargs)
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        with open(document_path, mode='w', encoding='utf8') as document:
            document.write(document_content)

    ''' Dispatch an EncodedType (Type | Composite | Enum | Set) to its dict builder '''
    @staticmethod
    def make_encoded_type_definition(encoded_type: EncodedType) -> dict:
        match encoded_type:
            case Type():
                return GeneratorBase.make_type_definition(encoded_type)
            case Composite():
                return GeneratorBase.make_composite_definition(encoded_type)
            case Enum():
                return GeneratorBase.make_enum_definition(encoded_type)
            case Set():
                return GeneratorBase.make_set_definition(encoded_type)
            case _:
                raise TypeError(f'unexpected encoded type: {type(encoded_type)!r}')

    ''' Dispatch a message/group member (Field | Group | Data) to its dict builder '''
    @staticmethod
    def make_message_field_definition(member: Union[Field, Group, Data]) -> dict:
        match member:
            case Field():
                return GeneratorBase.make_field_definition(member)
            case Group():
                return GeneratorBase.make_group_definition(member)
            case Data():
                return GeneratorBase.make_data_definition(member)
            case _:
                raise TypeError(f'unexpected field type: {type(member)!r}')

    @staticmethod
    def make_primitive_type_definition(primitive_type: PrimitiveType) -> dict:
        return asdict(primitive_type)

    @staticmethod
    def make_type_definition(type_type: Type) -> dict:
        entry = asdict(type_type)
        del entry['value_ref']  # not part of the generated IR
        entry['token'] = 'type'
        entry['presence'] = type_type.presence.value
        # null/min/max fall back to the primitive type's own bounds when not overridden
        entry['null_value'] = type_type.null_value if type_type.null_value is not None else type_type.primitive_type.null_value
        entry['min_value'] = type_type.min_value if type_type.min_value is not None else type_type.primitive_type.min_value
        entry['max_value'] = type_type.max_value if type_type.max_value is not None else type_type.primitive_type.max_value
        entry['encoded_length'] = type_type.encoded_length()
        return entry

    @staticmethod
    def make_composite_definition(composite_type: Composite) -> dict:
        contained_types = []
        for contained_type in composite_type.contained_types.values():
            match contained_type:
                case Ref():
                    # a <ref> is flattened into the definition of the type it points to
                    entry = GeneratorBase.make_encoded_type_definition(contained_type.type)
                    entry['name'] = contained_type.type.name
                    entry['offset'] = contained_type.offset
                    entry['description'] = contained_type.description
                    entry['since_version'] = contained_type.since_version
                    entry['deprecated'] = contained_type.deprecated
                case Type() | Composite() | Enum() | Set():
                    entry = GeneratorBase.make_encoded_type_definition(contained_type)
                case _:
                    raise TypeError(f'unexpected contained type: {type(contained_type)!r}')
            entry['reference_name'] = contained_type.name
            contained_types.append(entry)

        entry = asdict(composite_type)
        entry['token'] = 'composite'
        entry['presence'] = Presence.REQUIRED.value
        entry['contained_types'] = contained_types
        entry['encoded_length'] = composite_type.encoded_length()
        return entry

    @staticmethod
    def make_enum_definition(enum_type: Enum) -> dict:
        entry = asdict(enum_type)
        entry['token'] = 'enum'
        entry['presence'] = enum_type.presence.value
        entry['null_value'] = enum_type.null_value if enum_type.null_value is not None else enum_type.encoding_type.null_value
        entry['valid_values'] = list(entry.pop('valid_value_by_name').values())
        entry['encoded_length'] = enum_type.encoded_length()
        return entry

    @staticmethod
    def make_set_definition(set_type: Set) -> dict:
        entry = asdict(set_type)
        entry['token'] = 'set'
        entry['presence'] = set_type.presence.value
        entry['choices'] = list(entry.pop('choice_by_name').values())
        entry['encoded_length'] = set_type.encoded_length()
        return entry

    @staticmethod
    def make_field_definition(field_: Field) -> dict:
        entry = asdict(field_)
        entry['token'] = 'field'
        entry['presence'] = field_.presence.value
        entry['type'] = GeneratorBase.make_encoded_type_definition(field_.type)
        return entry

    @staticmethod
    def make_group_definition(group: Group) -> dict:
        entry = asdict(group)
        entry['token'] = 'group'
        entry['dimension_type'] = GeneratorBase.make_encoded_type_definition(group.dimension_type)
        entry['fields'] = [GeneratorBase.make_message_field_definition(f) for f in group.fields.values()]
        return entry

    @staticmethod
    def make_data_definition(data: Data) -> dict:
        entry = asdict(data)
        entry['token'] = 'data'
        entry['type'] = GeneratorBase.make_encoded_type_definition(data.type)
        return entry

    @staticmethod
    def make_message_definition(message: Message) -> dict:
        entry = asdict(message)
        entry['token'] = 'message'
        entry['fields'] = [GeneratorBase.make_message_field_definition(f) for f in message.fields.values()]
        return entry
