# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

from __future__ import annotations
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Union, Tuple
from collections import UserDict
from app.schema import *
from app.xml import *

class UniqueKeysDict(UserDict):
    def __setitem__(self, key, value):
        if key in self.data:
            raise Exception(f'duplicate key "{key}"')
        self.data[key] = value

class Parser:
    ''' Primitive types '''
    PRIMITIVE_TYPE_BY_NAME = UniqueKeysDict({
        'char':     PrimitiveType('char',   1,  'CHAR_NULL',    'CHAR_MIN',     'CHAR_MAX'),
        'int8':     PrimitiveType('int8',   1,  'INT8_NULL',    'INT8_MIN',     'INT8_MAX'),
        'int16':    PrimitiveType('int16',  2,  'INT16_NULL',   'INT16_MIN',    'INT16_MAX'),
        'int32':    PrimitiveType('int32',  4,  'INT32_NULL',   'INT32_MIN',    'INT32_MAX'),
        'int64':    PrimitiveType('int64',  8,  'INT64_NULL',   'INT64_MIN',    'INT64_MAX'),
        'uint8':    PrimitiveType('uint8',  1,  'UINT8_NULL',   'UINT8_MIN',    'UINT8_MAX'),
        'uint16':   PrimitiveType('uint16', 2,  'UINT16_NULL',  'UINT16_MIN',   'UINT16_MAX'),
        'uint32':   PrimitiveType('uint32', 4,  'UINT32_NULL',  'UINT32_MIN',   'UINT32_MAX'),
        'uint64':   PrimitiveType('uint64', 8,  'UINT64_NULL',  'UINT64_MIN',   'UINT64_MAX'),
        'float':    PrimitiveType('float',  4,  'FLOAT_NULL',   'FLOAT_MIN',    'FLOAT_MAX'),
        'double':   PrimitiveType('double', 8,  'DOUBLE_NULL',  'DOUBLE_MIN',   'DOUBLE_MAX')
    })

    ''' Primitive type names suitable for encodingType of enum '''
    VALID_PRIMITIVE_TYPE_FOR_ENUM = [ 'char', 'uint8', 'uint16', 'uint32', 'uint64' ]

    ''' Primitive type names suitable for encodingType of set '''
    VALID_PRIMITIVE_TYPE_FOR_SET = [ 'uint8', 'uint16', 'uint32', 'uint64' ]

    def __init__(self, root: ET.Element) -> None:
        self.root = root

    @staticmethod
    def from_file(path: str) -> Parser:
        root = load_xml_from_file(path)
        return Parser(root)

    @staticmethod
    def get_primitive_type(name: str) -> PrimitiveType:
        if name in Parser.PRIMITIVE_TYPE_BY_NAME:
            return Parser.PRIMITIVE_TYPE_BY_NAME[name]
        else:
            raise Exception(f'primitive type "{name}" not found')

    def get_schema(self) -> Schema:
        header_type_str = attr(self.root, 'headerType', 'messageHeader')
        header_type = self.get_encoded_type_by_name(header_type_str)
        if not isinstance(header_type, Composite) or not header_type.is_valid_header_type():
            raise Exception(f'type "{header_type_str}" is not valid header type')

        return Schema(
            package=attr(self.root, 'package', default=None),
            id=attr(self.root, 'id', cast=int),
            version=attr(self.root, 'version', 0, cast=int),
            semantic_type=attr(self.root, 'semanticType', None),
            byte_order=attr(self.root, 'byteOrder', ByteOrder.LITTLE_ENDIAN, cast=ByteOrder),
            description=attr(self.root, 'description', None),
            header_type=header_type,
            types=self.get_types(),
            messages=self.get_messages()
        )

    def get_types(self) -> Dict[str, EncodedType]:
        types = UniqueKeysDict()
        # add generic types
        for primitive_type in Parser.PRIMITIVE_TYPE_BY_NAME.values():
            encoded_type = Parser.get_primitive_type_as_encoded_type(primitive_type)
            types[encoded_type.name] = encoded_type
        # load types from xml
        for node in self.root.findall('./types/*'):
            encoded_type = self.parse_encoded_type_from_node(node)
            types[encoded_type.name] = encoded_type
        return types

    def get_messages(self) -> Dict[str, Message]:
        message_by_name = UniqueKeysDict()
        message_by_id = UniqueKeysDict()
        for child in self.root.findall('./message'):
            message = self.parse_message_from_node(child)
            message_by_name[message.name] = message
            message_by_id[message.id] = message
        return message_by_name

    @staticmethod
    def get_primitive_type_as_encoded_type(primitive_type: PrimitiveType) -> Type:
        return Type(
            name=primitive_type.name,
            description=None,
            presence=Presence.REQUIRED,
            null_value=None,
            min_value=None,
            max_value=None,
            length=1,
            offset=None,
            primitive_type=primitive_type,
            semantic_type=None,
            since_version=0,
            deprecated=None,
            const_value=None
        )

    def parse_type_from_node(self, node: ET.Element, offset: Optional[int] = None, inplace: bool = False) -> Type:
        name_str = attr(node, 'name')
        presence = attr(node, 'presence', Presence.REQUIRED, cast=Presence)
        length = attr(node, 'length', None)
        primitive_type = Parser.get_primitive_type(attr(node, 'primitiveType'))
        value_ref = attr(node, 'valueRef', None)
        const_value = None

        # For presence=constant
        #     constValue = node.text on valueRef not set
        #     constValue = valueRef on valueRef set
        if value_ref != None:
            if presence != Presence.CONSTANT:
                raise Exception(f'presence must be constant when valueRef is set (type "{name_str}")')
            if not self.is_valid_value_ref(value_ref):
                raise Exception(f'valueRef "{value_ref}" of type "{name_str}" is not valid')

        if presence == Presence.CONSTANT:
            if value_ref == None:
                const_value = node.text.strip()
                if const_value == '':
                    raise Exception(f'node text is empty and value_ref is not set for constant type "{name_str}"')
                if primitive_type.name == 'char':
                    # Set length to constant size in case of string constants and length attr not set
                    if length == None:
                        length = len(const_value)
                    elif len(const_value) != int(length):
                        raise Exception(f'node text length is not equal to field length for constant type "{name_str}"')
            else:
                enum_name, enum_value_name = value_ref.split('.')
                enum_type = self.get_encoded_type_by_name(enum_name)
                if not isinstance(enum_type, Enum):
                    raise Exception(f'"{name_str}" is not enum type')
                const_value = enum_type.valid_value_by_name[enum_value_name].value

        character_encoding = None
        if primitive_type.name == 'char':
            character_encoding = attr(node, 'characterEncoding', "US-ASCII")
        else:
            character_encoding = attr(node, 'characterEncoding', None)
        if character_encoding != None:
            character_encoding.strip()

        # Set default length to 1
        if length == None:
            length = 1

        return Type(
            name=name_str,
            description=attr(node, 'description', None),
            presence=presence,
            null_value=attr(node, 'nullValue', None),
            min_value=attr(node, 'minValue', None),
            max_value=attr(node, 'maxValue', None),
            length=int(length),
            offset=attr(node, 'offset', offset, cast=int),
            primitive_type=primitive_type,
            semantic_type=attr(node, 'semanticType', None),
            since_version=attr(node, 'sinceVersion', 0, cast=int),
            deprecated=attr(node, 'deprecated', None, cast=int),
            value_ref=value_ref,
            const_value=const_value,
            character_encoding=character_encoding,
            inplace=inplace
        )

    def parse_composite_from_node(self, node: ET.Element, offset: Optional[int] = None, inplace: bool = False) -> Composite:
        name_str = attr(node, 'name')
        # used for compute offset for each type inside composite
        computed_offset = 0
        contained_types = UniqueKeysDict()

        for child in node:
            contained_type = None
            if child.tag == 'type':
                contained_type = self.parse_type_from_node(child, offset=computed_offset, inplace=True)
            elif child.tag == 'composite':
                contained_type = self.parse_composite_from_node(child, offset=computed_offset, inplace=True)
            elif child.tag == 'enum':
                contained_type = self.parse_enum_from_node(child, offset=computed_offset, inplace=True)
            elif child.tag == 'set':
                contained_type = self.parse_set_from_node(child, offset=computed_offset, inplace=True)
            elif child.tag == 'ref':
                contained_type = self.parse_ref_from_node(child, offset=computed_offset)
            else:
                raise Exception(f'unknown composite type "{name_str}" child node "{child.tag}"')

            if computed_offset > contained_type.offset:
                raise Exception(f'invalid offset of type "{contained_type.name}" inside composite type "{name_str}"')

            computed_offset = contained_type.offset + contained_type.encoded_length();
            contained_types[contained_type.name] = contained_type

        return Composite(
            name=name_str,
            offset=attr(node, 'offset', offset, cast=int),
            description=attr(node, 'description', None),
            semantic_type=attr(node, 'semanticType', None),
            since_version=attr(node, 'sinceVersion', 0, cast=int),
            deprecated=attr(node, 'deprecated', None, cast=int),
            contained_types=contained_types,
            inplace=inplace
        )

    def parse_valid_value_from_node(self, node: ET.Element) -> ValidValue:
        return ValidValue(
            name=attr(node, 'name'),
            description=attr(node, 'description', None),
            since_version=attr(node, 'sinceVersion', 0, cast=int),
            deprecated=attr(node, 'deprecated', None, cast=int),
            value=node.text.strip()
        )

    def parse_enum_from_node(self, node: ET.Element, offset: Optional[int] = None, inplace: bool = False) -> Enum:
        name_str = attr(node, 'name')
        valid_value_by_name = UniqueKeysDict()

        for child in node:
            if child.tag == 'validValue':
                valid_value = self.parse_valid_value_from_node(child)
                valid_value_by_name[valid_value.name] = valid_value
            else:
                raise Exception(f'unexpected tag "{child.tag}" inside enum "{name_str}"')

        return Enum(
            name=name_str,
            description=attr(node, 'description', None),
            presence=attr(node, 'presence', Presence.REQUIRED, cast=Presence),
            encoding_type=self.get_encoding_type_for_enum(attr(node, 'encodingType')),
            since_version=attr(node, 'sinceVersion', 0, cast=int),
            deprecated=attr(node, 'deprecated', None, cast=int),
            offset=attr(node, 'offset', offset, cast=int),
            null_value=attr(node, 'nullValue', None),
            valid_value_by_name=valid_value_by_name,
            inplace=inplace
        )

    def parse_choice_from_node(self, node: ET.Element) -> Choice:
        return Choice(
            name=attr(node, 'name'),
            description=attr(node, 'description', None),
            since_version=attr(node, 'sinceVersion', 0, cast=int),
            deprecated=attr(node, 'deprecated', None, cast=int),
            value=node.text.strip()
        )

    def parse_set_from_node(self, node: ET.Element, offset: Optional[int] = None, inplace: bool = False) -> Set:
        name_str = attr(node, 'name')
        choice_by_name = UniqueKeysDict()

        for child in node:
            if child.tag != 'choice':
                raise Exception(f'unexpected tag "{child.tag}" inside set "{name_str}" ')
            choice = self.parse_choice_from_node(child)
            choice_by_name[choice.name] = choice

        return Set(
            name=name_str,
            description=attr(node, 'description', None),
            presence=attr(node, 'presence', Presence.REQUIRED, cast=Presence),
            encoding_type=self.get_encoding_type_for_set(attr(node, 'encodingType')),
            since_version=attr(node, 'sinceVersion', 0, cast=int),
            deprecated=attr(node, 'deprecated', None, cast=int),
            offset=attr(node, 'offset', offset, cast=int),
            choice_by_name=choice_by_name,
            inplace=inplace
        )

    def parse_ref_from_node(self, node: ET.Element, offset: Optional[int] = None) -> Ref:
        return Ref(
            name=attr(node, 'name'),
            type=self.get_encoded_type_by_name(attr(node, 'type')),
            offset=attr(node, 'offset', offset, cast=int),
            description=attr(node, 'description', None),
            since_version=attr(node, 'sinceVersion', 0, cast=int),
            deprecated=attr(node, 'deprecated', None, cast=int),
        )

    def parse_message_from_node(self, node: ET.Element) -> Message:
        name_str = attr(node, 'name')
        computed_offset = 0
        group_encountered = False
        data_encountered = False
        field_by_name = UniqueKeysDict()
        field_by_id = UniqueKeysDict()

        for child in node:
            field = None
            if child.tag == 'field':
                if group_encountered or data_encountered:
                    raise Exception(f'"field" specified after "group" or "data" node in message "{name_str}"')
                field = self.parse_field_from_node(child, offset=computed_offset)
                if computed_offset > field.offset:
                    raise Exception(f'invalid field offset "{field.name}" inside message "{name_str}"')
                computed_offset = field.offset + field.encoded_length()
            elif child.tag == 'group':
                if data_encountered:
                    raise Exception(f'"group" specified after "data" in message "{name_str}"')
                field = self.parse_group_from_node(child)
                group_encountered = True
            elif child.tag == 'data':
                field = self.parse_data_from_node(child)
                data_encountered = True
            else:
                raise Exception(f'unknown message "{name_str}" child node "{child.tag}"')
            field_by_name[field.name] = field
            field_by_id[field.id] = field

        block_length = attr(node, 'blockLength', computed_offset, cast=int)
        if block_length < computed_offset:
            raise Exception(f'invalid blockLength value for message "{name_str}"')

        return Message(
            name=name_str,
            id=attr(node, 'id', cast=int),
            description=attr(node, 'description', None),
            block_length=block_length,
            semantic_type=attr(node, 'semanticType', None),
            since_version=attr(node, 'sinceVersion', 0, cast=int),
            deprecated=attr(node, 'deprecated', None, cast=int),
            fields=field_by_name
        )

    def parse_field_from_node(self, node: ET.Element, offset: int) -> Field:
        name_str = attr(node, 'name')
        encoded_type = self.get_encoded_type_by_name(attr(node, 'type'))
        presence = attr(node, 'presence', encoded_type.presence if isinstance(encoded_type, Type) else Presence.REQUIRED, cast=Presence)
        value_ref = attr(node, 'valueRef', None)

        if value_ref != None and not self.is_valid_value_ref(value_ref):
            raise Exception(f'valueRef "{value_ref}" of type "{name_str}" is not valid')
        if presence == Presence.CONSTANT:
            if isinstance(encoded_type, Enum):
                if value_ref == None:
                    raise Exception(f'valueRef not set for constant enum field "{name_str}"')
                if not self.is_valid_value_ref(value_ref):
                    raise Exception(f'valueRef "{value_ref}" for type "{name_str}" is not valid')
            elif isinstance(encoded_type, Type):
                if encoded_type.const_value == None:
                    raise Exception(f'"constValue" not set of type for field "{name_str}"')
            else:
                raise Exception(f'field "{name_str}" is constant but encoding type is not "enum" or "type"')
        if isinstance(encoded_type, Set):
            if presence != Presence.REQUIRED:
                raise Exception(f'field "{name_str}" of type "{encoded_type.name}" should be required')
        if isinstance(encoded_type, Composite):
            if presence == Presence.CONSTANT:
                raise Exception(f'field "{name_str}" of type "{encoded_type.name}" should not be constant')

        return Field(
            name=name_str,
            id=attr(node, 'id', cast=int),
            description=attr(node, 'description', None),
            type=encoded_type,
            offset=attr(node, 'offset', offset, cast=int),
            presence=presence,
            value_ref=value_ref,
            semantic_type=attr(node, 'semanticType', None),
            since_version=attr(node, 'sinceVersion', 0, cast=int),
            deprecated=attr(node, 'deprecated', None, cast=int)
        )

    def parse_group_from_node(self, node: ET.Element) -> Group:
        name_str = attr(node, 'name')
        computed_offset = 0
        group_encountered = False
        data_encountered = False
        field_by_name = UniqueKeysDict()
        field_by_id = UniqueKeysDict()

        for child in node:
            field = None
            if child.tag == 'field':
                if group_encountered or data_encountered:
                    raise Exception(f'<field> specified after <group> or <data> in group "{name_str}"')
                field = self.parse_field_from_node(child, offset=computed_offset)
                if computed_offset > field.offset:
                    raise Exception(f'invalid field offset of "{field.name}" inside group "{name_str}"')
                computed_offset = field.offset + field.encoded_length()
            elif child.tag == 'group':
                if data_encountered:
                    raise Exception(f'<group> specified after <data> in group "{name_str}"')
                field = self.parse_group_from_node(child)
                group_encountered = True
            elif child.tag == 'data':
                field = self.parse_data_from_node(child)
                data_encountered = True
            else:
                raise Exception(f'unknown child node "{child.tag}" in group "{name_str}"')
            field_by_name[field.name] = field
            field_by_id[field.id] = field

        block_length = attr(node, 'blockLength', computed_offset, cast=int)
        if block_length < computed_offset:
            raise Exception(f'invalid blockLength value for group "{name_str}"')
        dimension_type_str = attr(node, 'dimensionType', 'groupSizeEncoding')
        dimension_type = self.get_encoded_type_by_name(dimension_type_str)
        if not isinstance(dimension_type, Composite) or not dimension_type.is_valid_dimension_type():
            raise Exception(f'type "{dimension_type_str}" is not valid dimension type')

        return Group(
            name=name_str,
            id=attr(node, 'id', cast=int),
            description=attr(node, 'description', None),
            dimension_type=dimension_type,
            block_length=block_length,
            fields=field_by_name
        )

    def parse_data_from_node(self, node: ET.Element) -> Data:
        type_str = attr(node, 'type')
        encoded_type = self.get_encoded_type_by_name(type_str)
        if not isinstance(encoded_type, Composite) or not encoded_type.is_valid_variable_length():
            raise Exception(f'type "{type_str}" is not valid type for <data>')

        return Data(
            name=attr(node, 'name'),
            id=attr(node, 'id', cast=int),
            description=attr(node, 'description', None),
            type=encoded_type,
            semantic_type=attr(node, 'semanticType', None),
            since_version=attr(node, 'sinceVersion', 0, cast=int),
            deprecated=attr(node, 'deprecated', None, cast=int)
        )

    def get_encoding_type_for_enum(self, encoding_type_str: str) -> PrimitiveType:
        if encoding_type_str in Parser.VALID_PRIMITIVE_TYPE_FOR_ENUM:
            return Parser.get_primitive_type(encoding_type_str)
        encoding_type_node = self.root.find(f'.//types/type[@name="{encoding_type_str}"]')
        if encoding_type_node == None:
            raise Exception(f'encodingType "{encoding_type_str}" for <enum> not found')
        encoding_type = self.parse_type_from_node(encoding_type_node)
        primitive_type = encoding_type.primitive_type
        if primitive_type.name not in Parser.VALID_PRIMITIVE_TYPE_FOR_ENUM:
            raise Exception(f'type "{encoding_type_str}" is not valid for <enum> encodingType')
        return primitive_type

    def get_encoding_type_for_set(self, encoding_type_str: str) -> PrimitiveType:
        if encoding_type_str in Parser.VALID_PRIMITIVE_TYPE_FOR_SET:
            return Parser.get_primitive_type(encoding_type_str)
        encoding_type_node = self.root.find(f'.//types/type[@name="{encoding_type_str}"]')
        if encoding_type_node == None:
            raise Exception(f'encodingType "{encoding_type_str}" for <set> not found')
        encoding_type = self.parse_type_from_node(encoding_type_node)
        primitive_type = encoding_type.primitive_type
        if primitive_type.name not in Parser.VALID_PRIMITIVE_TYPE_FOR_SET:
            raise Exception(f'type "{encoding_type_str}" is not valid for <set> encodingType')
        return primitive_type

    def parse_encoded_type_from_node(self, node: ET.Element) -> EncodedType:
        if node.tag == 'type':
            return self.parse_type_from_node(node)
        elif node.tag == 'composite':
            return self.parse_composite_from_node(node)
        elif node.tag == 'enum':
            return self.parse_enum_from_node(node)
        elif node.tag == 'set':
            return self.parse_set_from_node(node)
        else:
            raise Exception(f'unknown node type definition (node: "{node.tag}", line: {node.sourceline})')

    def get_encoded_type_by_name(self, name: str) -> EncodedType:
        # first check type exist in xml
        node = self.root.find(f'.//types/*[@name="{name}"]')
        if node != None:
            return self.parse_encoded_type_from_node(node)
        # check type is primitive type
        if name in Parser.PRIMITIVE_TYPE_BY_NAME:
            return Parser.get_primitive_type_as_encoded_type(Parser.PRIMITIVE_TYPE_BY_NAME[name])
        raise Exception(f'encoded type "{name}" not found')

    def is_valid_value_ref(self, value_ref: str) -> bool:
        enum_name, enum_value_name = value_ref.split('.')
        enum_type = self.get_encoded_type_by_name(enum_name)
        if not isinstance(enum_type, Enum):
            return False
        if enum_value_name not in enum_type.valid_value_by_name:
            return False
        return True
