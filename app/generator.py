from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from app.schema import *

class Generator(ABC):
    primitiveTypeByName = {
        'char':     PrimitiveType('char',   1,  "CHAR_NULL",    "CHAR_MIN",     "CHAR_MAX"),
        'int8':     PrimitiveType('int8',   1,  "INT8_NULL",    "INT8_MIN",     "INT8_MAX"),
        'int16':    PrimitiveType('int16',  2,  "INT16_NULL",   "INT16_MIN",    "INT16_MAX"),
        'int32':    PrimitiveType('int32',  4,  "INT32_NULL",   "INT32_MIN",    "INT32_MAX"),
        'int64':    PrimitiveType('int64',  8,  "INT64_NULL",   "INT64_MIN",    "INT64_MAX"),
        'uint8':    PrimitiveType('uint8',  1,  "UINT8_NULL",   "UINT8_MIN",    "UINT8_MAX"),
        'uint16':   PrimitiveType('uint16', 2,  "UINT16_NULL",  "UINT16_MIN",   "UINT16_MAX"),
        'uint32':   PrimitiveType('uint32', 4,  "UINT32_NULL",  "UINT32_MIN",   "UINT32_MAX"),
        'uint64':   PrimitiveType('uint64', 8,  "UINT64_NULL",  "UINT64_MIN",   "UINT64_MAX"),
        'float':    PrimitiveType('float',  4,  "FLOAT_NULL",   "FLOAT_MIN",    "FLOAT_MAX"),
        'double':   PrimitiveType('double', 8,  "DOUBLE_NULL",  "DOUBLE_MIN",   "DOUBLE_MAX")
    }

    @abstractmethod
    def _generateImpl(self, schema: dict) -> None:
        pass

    def generate(self, schema: Schema) -> None:
        ir = {}

        if schema.package != None:
            ir['package'] = schema.package.split('.')
        else:
            ir['package'] = None

        ir['id'] = schema.id
        ir['version'] = schema.version
        ir['byteOrder'] = schema.byteOrder.value
        ir['description'] = schema.description
        ir['headerType'] = Generator.makeEncodedTypeDefinition(schema.headerType)

        ir['types'] = []
        for type in schema.types.values():
            ir['types'].append(Generator.makeEncodedTypeDefinition(type))

        ir['messages'] = []
        for message in schema.messages.values():
            ir['messages'].append(Generator.makeMessageDefinition(message))

        self._generateImpl(ir)

    @staticmethod
    def makeEncodedTypeDefinition(type: EncodedType) -> dict:
        assert (isinstance(type, (Type, Composite, Enum, Set))), "unknown type"
        if isinstance(type, Type):
            return Generator.makeTypeDefinition(type)
        if isinstance(type, Composite):
            return Generator.makeCompositeDefinition(type)
        if isinstance(type, Enum):
            return Generator.makeEnumDefinition(type)
        if isinstance(type, Set):
            return Generator.makeSetDefinition(type)

    @staticmethod
    def makeTypeDefinition(type: Type) -> dict:
        return {
            'token': 'type',
            'name': type.name,
            'description': type.description,
            'presence': type.presence.value,
            'nullValue': type.nullValue if type.nullValue != None else type.primitiveType.nullValue,
            'minValue': type.minValue if type.minValue != None else type.primitiveType.minValue,
            'maxValue': type.maxValue if type.maxValue != None else type.primitiveType.maxValue,
            'length': type.length,
            'offset': type.offset,
            'primitiveType': type.primitiveType.name,
            'semanticType': type.semanticType,
            'sinceVersion': type.sinceVersion,
            'deprecated': type.deprecated,
            'constValue': type.constValue,
            'encodedLength': type.encodedLength()
        }

    @staticmethod
    def makeCompositeDefinition(type: Composite) -> dict:
        containedTypes = []
        for containedType in type.containedTypes.values():
            assert (isinstance(containedType, (Type, Composite, Enum, Set, Ref))), "unknown type"
            entry = None
            if isinstance(containedType, Type):
                entry = Generator.makeTypeDefinition(containedType)
            elif isinstance(containedType, Composite):
                entry = Generator.makeCompositeDefinition(containedType)
            elif isinstance(containedType, Enum):
                entry = Generator.makeEnumDefinition(containedType)
            elif isinstance(containedType, Set):
                entry = Generator.makeSetDefinition(containedType)
            elif isinstance(containedType, Ref):
                entry = Generator.makeEncodedTypeDefinition(containedType.type)
                entry['name'] = containedType.name
                entry['offset'] = containedType.offset
                entry['description'] = containedType.description
                entry['sinceVersion'] = containedType.sinceVersion
                entry['deprecated'] = containedType.deprecated
            containedTypes.append(entry)

        return {
            'token': 'composite',
            'name': type.name,
            'offset': type.offset,
            'description': type.description,
            'semanticType': type.semanticType,
            'sinceVersion': type.sinceVersion,
            'deprecated': type.deprecated,
            'containedTypes': containedTypes,
            'encodedLength': type.encodedLength()
        }

    @staticmethod
    def makeEnumDefinition(type: Enum) -> dict:
        validValues = []
        for validValue in type.validValueByName.values():
            validValues.append({
                'name': validValue.name,
                'value': validValue.value,
                'description': validValue.description,
                'sinceVersion': validValue.sinceVersion,
                'deprecated': validValue.deprecated
            })
        return {
            'token': 'enum',
            'name': type.name,
            'description': type.description,
            'encodingType': type.encodingType.name,
            'sinceVersion': type.sinceVersion,
            'deprecated': type.deprecated,
            'offset': type.offset,
            'nullValue': type.nullValue if type.nullValue != None else type.encodingType.nullValue,
            'validValues': validValues,
            'encodedLength': type.encodedLength()
        }

    @staticmethod
    def makeSetDefinition(type: Set) -> dict:
        choices = []
        for choice in type.choiceByName.values():
            choices.append({
                'name': choice.name,
                'value': choice.value,
                'description': choice.description,
                'sinceVersion': choice.sinceVersion,
                'deprecated': choice.deprecated
            })
        return {
            'token': 'set',
            'name': type.name,
            'description': type.description,
            'encodingType': type.encodingType.name,
            'sinceVersion': type.sinceVersion,
            'deprecated': type.deprecated,
            'offset': type.offset,
            'choices': choices,
            'encodedLength': type.encodedLength()
        }

    @staticmethod
    def makeFieldDefinition(field: Field) -> dict:
        return {
            'token': 'field',
            'name': field.name,
            'id': field.id,
            'description': field.description,
            'type': Generator.makeEncodedTypeDefinition(field.type),
            'offset': field.offset,
            'presence': field.presence.value,
            'valueRef': field.valueRef,
            'semanticType': field.semanticType,
            'sinceVersion': field.sinceVersion,
            'deprecated': field.deprecated
        }

    @staticmethod
    def makeGroupDefinition(group: Group) -> dict:
        fields = []
        for field in group.fields.values():
            assert (isinstance(field, (Field, Group, Data))), "unknown group field"
            entry = None
            if isinstance(field, Field):
                entry = Generator.makeFieldDefinition(field)
            elif isinstance(field, Group):
                entry = Generator.makeGroupDefinition(field)
            elif isinstance(field, Data):
                entry = Generator.makeDataDefinition(field)
            fields.append(entry)

        return {
            'token': 'group',
            'name': group.name,
            'id': group.id,
            'description': group.description,
            'dimensionType': Generator.makeEncodedTypeDefinition(group.dimensionType),
            'blockLength': group.blockLength,
            'fields': fields
        }

    @staticmethod
    def makeDataDefinition(data: Data) -> dict:
        return {
            'token': 'data',
            'name': data.name,
            'id': data.id,
            'description': data.description,
            'type': Generator.makeEncodedTypeDefinition(data.type),
            'semanticType': data.semanticType,
            'sinceVersion': data.sinceVersion,
            'deprecated': data.deprecated
        }

    @staticmethod
    def makeMessageDefinition(message: Message) -> dict:
        fields = []
        for field in message.fields.values():
            assert (isinstance(field, (Field, Group, Data))), "unknown message field"
            entry = None
            if isinstance(field, Field):
                entry = Generator.makeFieldDefinition(field)
            elif isinstance(field, Group):
                entry = Generator.makeGroupDefinition(field)
            elif isinstance(field, Data):
                entry = Generator.makeDataDefinition(field)
            fields.append(entry)

        return {
            'token': 'message',
            'name': message.name,
            'id': message.id,
            'description': message.description,
            'blockLength': message.blockLength,
            'semanticType': message.semanticType,
            'sinceVersion': message.sinceVersion,
            'deprecated': message.deprecated,
            'fields': fields
        }
