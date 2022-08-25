from __future__ import annotations
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from typing import List, Any
from app.xml import *
from app.common import *

class Schema:
    primitiveTypes = {
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

    def __init__(self, node: ET.ElementTree) -> None:
        self.package = attr(node, 'package', None)
        self.id = attr(node, 'id', cast=int)
        self.version = attr(node, 'version', 0, cast=int)
        self.semanticType = attr(node, 'semanticType', None)
        self.byteOrder = attr(node, 'byteOrder', ByteOrder.LITTLE_ENDIAN, cast=ByteOrder)
        self.description = attr(node, 'description', None)
        self.headerType = attr(node, 'headerType', 'messageHeader')
        self.types = self._loadTypes(node)
        self.messages = self._loadMessages(node)

        self._validateMessageHeader()

    @staticmethod
    def loadFromFile(path: str) -> Schema:
        root = loadXMLFromFile(path)
        return Schema(root)

    @staticmethod
    def getPrimitiveType(name: str) -> PrimitiveType:
        if name in Schema.primitiveTypes:
            return Schema.primitiveTypes[name]
        else:
            raise Exception(f'PrimitiveType "{name}" not found')

    def getType(self, name: str) -> Any:
        if name not in self.types:
            raise Exception(f'type "{name}" not found in schema')
        return self.types[name]

    def _loadTypes(self, node: ET.Element) -> None:
        types = {}

        def addType(type):
            if type.name in types:
                raise Exception(f'type "{type.name}" already exist in schema')
            types[type.name] = type

        for name in Schema.primitiveTypes.keys():
            addType(EncodedDataType(ET.Element('type', attrib = {'name': name, 'primitiveType': name}), self))

        for typeNode in node.findall('./types/type'):
            addType(EncodedDataType(typeNode, self))

        for typeNode in node.findall('./types/composite'):
            addType(Composite(typeNode, self))

        for typeNode in node.findall('./types/enum'):
            addType(Enum(typeNode, self))

        for typeNode in node.findall('./types/set'):
            addType(Set(typeNode, self))

        return types

    def _loadMessages(self, node: ET.Element) -> dict:
        messageByName = {}
        messageByID = {}

        for messageNode in node.findall('./message'):
            message = Message(messageNode, self)
            if message.name in messageByName:
                raise Exception(f'message "{message.name}" already exists in schema')
            messageByName[message.name] = message
            if message.id in messageByID:
                raise Exception(f'message with id "{message.id}" already exists in schema')
            messageByID[message.name] = message

        return messageByName

    def _validateMessageHeader(self) -> None:
        messageHeader = self.getType(self.headerType)
        if not isinstance(messageHeader, Composite):
            raise Exception(f'message header type {self.headerType} must be composite type')
        messageHeader.checkForWellFormedMessageHeader()

class Type(ABC):
    def __init__(self, node: ET.Element, schema: Schema) -> None:
        self.schema = schema
        self.name = attr(node, 'name')
        self.presence = attr(node, 'presence', Presence.REQUIRED, cast=Presence)
        self.description = attr(node, 'description', None)
        self.sinceVersion = attr(node, 'sinceVersion', 0, cast=int)
        self.deprecated = attr(node, 'deprecated', 0, cast=int)
        self.semanticType = attr(node, 'semanticType', None)
        self.offsetAttr = attr(node, 'offset', None, cast=int)

    @abstractmethod
    def encodedLength(self) -> int:
        pass

class EncodedDataType(Type):
    def __init__(self, node: ET.Element, schema: Schema) -> None:
        super().__init__(node, schema)

        self.primitiveType = schema.getPrimitiveType(attr(node, 'primitiveType'))
        self.length = attr(node, 'length', 1, cast=int)
        self.varLen = False
        self.valueRef = attr(node, 'valueRef', None)

        if self.valueRef != None:
            if self.valueRef.find('.') == -1:
                raise Exception(f'valueRef ({self.valueRef}) format not valid (type: "{self.name}")')
            if self.presence != Presence.CONSTANT:
                raise Exception(f'presence must be "constant" when valueRef is set (type: "{self.name}")')

        if self.presence == Presence.CONSTANT:
            if self.valueRef == None:
                text = node.text.strip() if node.text else None
                if text == None:
                    raise Exception(f'type has declared presence as "constant" but XML node has no data (type: "{self.name}")')
                # TODO:
                # https://github.com/real-logic/simple-binary-encoding/blob/master/sbe-tool/src/main/java/uk/co/real_logic/sbe/xml/EncodedDataType.java#L116-L124
                self.constValue = text
            else:
                self.constValue = self._lookupValueRef(node)
        else:
            self.constValue = None

        self.minValue = attr(node, 'minValue', self.primitiveType.minValue)
        self.maxValue = attr(node, 'maxValue', self.primitiveType.maxValue)
        self.nullValue = attr(node, 'nullValue', self.primitiveType.nullValue)

    def _lookupValueRef(self, node: ET.Element) -> str:
        # TODO:
        # https://github.com/real-logic/simple-binary-encoding/blob/master/sbe-tool/src/main/java/uk/co/real_logic/sbe/xml/EncodedDataType.java#L159-L199
        name, value = self.valueRef.split('.')
        valueRefNode = documentRoot(node).find(f'.//types/enum[@name="{name}"]')

        if valueRefNode is None:
            raise Exception(f'valueRef type "{name}" not found (type: "{self.name}")')

        enum = Enum(valueRefNode, self.schema)
        if enum.encodingType != self.primitiveType:
            raise Exception(f'valueRef type "{name}" does not match type "{self.primitiveType.name}" (type: "{self.name}")')

        if value not in enum.validValues:
            raise Exception(f'valueRef type "{name}" does not have validValue "{value}" (type: "{self.name}")')

        return enum.validValues[value]['value']

    def encodedLength(self) -> int:
        if self.presence == Presence.CONSTANT:
            return 0
        return self.primitiveType.size * self.length

class Enum(Type):
    def __init__(self, node: ET.Element, schema: Schema) -> None:
        super().__init__(node, schema)

        encodingTypeStr = attr(node, 'encodingType')
        if encodingTypeStr in [ 'char', 'int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64' ]:
            self.encodingType = schema.getPrimitiveType(encodingTypeStr)
        else:
            encodingTypeNode = documentRoot(node).find(f'.//types/type[@name="{encodingTypeStr}"]')

            if encodingTypeNode == None:
                raise Exception(f'illegal encodingType "{encodingTypeStr}" for enum (type: "{self.name}")')

            encodingDataType = EncodedDataType(encodingTypeNode, schema)
            if encodingDataType.length != 1:
                raise(f'illegal encodingType "{encodingTypeStr}", length not equal to 1 (type: "{self.name}")')

            self.encodingType = encodingDataType.primitiveType

        self.nullValue = attr(node, 'nullValue', self.encodingType.nullValue)

        validValues = {}
        for validValueNode in node.findall('./validValue'):
            name = attr(validValueNode, 'name')
            if name in validValues:
                raise Exception(f'validValue {name} already exists (type: "{self.type}")')
            validValues[name] = {
                'name': name,
                'value': validValueNode.text.strip(),
                'description': attr(validValueNode, 'description', None),
                'sinceVersion': attr(validValueNode, 'sinceVersion', 0, cast=int),
                'deprecated': attr(validValueNode, 'deprecated', 0, cast=int)
            }

        self.validValues = validValues

    def encodedLength(self) -> int:
        if self.presence == Presence.CONSTANT:
            return 0
        return self.encodingType.size

class Set(Type):
    def __init__(self, node: ET.Element, schema: Schema) -> None:
        super().__init__(node, schema)

        encodingTypeStr = attr(node, 'encodingType')
        if encodingTypeStr in [ 'uint8', 'uint16', 'uint32', 'uint64' ]:
            self.encodingType = schema.getPrimitiveType(encodingTypeStr)
        else:
            encodingTypeNode = documentRoot(node).find(f'.//types/type[@name="{encodingTypeStr}"]')

            if encodingTypeNode == None:
                raise Exception(f'illegal encodingType "{encodingTypeStr}" for set (type: "{self.name}")')

            encodingDataType = EncodedDataType(encodingTypeNode, schema)
            if encodingDataType.length != 1:
                raise(f'illegal encodingType "{encodingTypeStr}", length not equal to 1 (type: "{self.name}")')

            self.encodingType = encodingDataType.primitiveType

        choices = {}
        for choiceNode in node.findall('./choice'):
            name = attr(choiceNode, 'name')
            if name in choices:
                raise Exception(f'choice "{name}" already exists (type: "{self.type}")')
            choices[name] = {
                'name': name,
                'value': choiceNode.text.strip(),
                'description': attr(choiceNode, 'description', None),
                'sinceVersion': attr(choiceNode, 'sinceVersion', 0, cast=int),
                'deprecated': attr(choiceNode, 'deprecated', 0, cast=int)
            }

        self.choices = choices.values()

    def encodedLength(self) -> int:
        return self.encodingType.size

class Composite(Type):
    def __init__(self, node: ET.Element, schema: Schema) -> None:
        super().__init__(node, schema)
        self.containedTypes = self._loadTypes(node)
        self._updateContainedTypesOffset()

    def _loadTypes(self, node: ET.ElementTree) -> None:
        containedTypes = {}
        def addType(type):
            if type.name in containedTypes:
                raise Exception(f'type {type.name} already in composite (type: "{self.name}")')
            containedTypes[type.name] = type

        def processType(typeNode: ET.ElementTree) -> Any:
            if typeNode.tag == 'type':
                return EncodedDataType(typeNode, self.schema)
            elif typeNode.tag == 'enum':
                return Enum(typeNode, self.schema)
            elif typeNode.tag == 'set':
                return Set(typeNode, self.schema)
            elif typeNode.tag == 'composite':
                return Composite(typeNode, self.schema)
            elif typeNode.tag == 'ref':
                refTypeName = attr(typeNode, 'type')
                if refTypeName == self.name:
                    raise Exception(f'ref type cycling dependency (type: "{self.name}")')

                refNode = documentRoot(node).find(f'.//types/*[@name="{refTypeName}"]')
                if refNode is None:
                    raise Exception(f'ref type "{refTypeName}" not found (type: "{self.name}")')

                type = processType(refNode)
                type.name = attr(typeNode, 'name')
                type.sinceVersion = attr(typeNode, 'sinceVersion', 0, cast=int)
                type.deprecated = attr(typeNode, 'deprecated', 0, cast=int)
                type.offsetAttr = attr(typeNode, 'offset', None, cast=int)
                return type
            else:
                raise Exception(f'{childNode.tag} not valid within composite (type: "{self.name}")')

        for childNode in node:
            type = processType(childNode)
            addType(type)

        return containedTypes

    def encodedLength(self) -> int:
        length = 0
        for type in self.containedTypes.values():
            if type.offsetAttr:
                length = type.offsetAttr
            length += type.encodedLength()
        return length

    def getType(self, name: str) -> Any:
        if name not in self.containedTypes.keys():
            raise Exception(f'type "{name}" not found in composite "{self.name}"')
        return self.containedTypes[name]

    def getFirstType(self) -> Any:
        return list(self.containedTypes.values())[0]

    def checkForWellFormedVariableLengthDataEncoding(self) -> None:
        lengthType = self.getType('length')
        # TODO: check lengthType

    def checkForWellFormedGroupSizeEncoding(self) -> None:
        blockLengthType = self.getType('blockLength')
        # TODO: check blockLengthType
        numInGroupType = self.getType('numInGroup')
        # TODO: check numInGroupType

    def checkForWellFormedMessageHeader(self) -> None:
        blockLengthType = self.getType('blockLength')
        # TODO: check blockLengthType
        templateIdType = self.getType('templateId')
        # TODO: check templateIdType
        schemaIdType = self.getType('schemaId')
        # TODO: check schemaIdType
        versionType = self.getType('version')
        # TODO: check versionType

    def _updateContainedTypesOffset(self) -> None:
        offset = 0
        for type in self.containedTypes.values():
            if type.offsetAttr == None:
                type.offsetAttr = offset
            else:
                if type.offsetAttr < offset:
                    raise Exception(f'invalid field offset value (message: "{message.name}", field: "{field.name}")')

            offset += type.encodedLength()

class Message:
    def __init__(self, node: ET.Element, schema: Schema) -> None:
        self.schema = schema
        self.id = attr(node, 'id', cast=int)
        self.name = attr(node, 'name')
        self.description = attr(node, 'description', None)
        self.blockLength = attr(node, 'blockLength', None, cast=int)
        self.sinceVersion = attr(node, 'sinceVersion', 0, cast=int)
        self.deprecated = attr(node, 'deprecated', 0, cast=int)
        self.semanticType = attr(node, 'semanticType', None)
        self.fields = self._loadFields(node)
        self._updateFieldsOffsetAndBlockLength()

    def _loadFields(self, node: ET.Element) -> List[Field]:
        fieldByName = {}
        fieldByID = {}

        groupEncountered = False
        dataEncountered = False

        for fieldNode in node:
            field = None

            if fieldNode.tag == 'group':
                if dataEncountered:
                    raise Exception(f'group node specified after data node (message: "{self.name}")')
                field = Group(fieldNode, self.schema, self._loadFields(fieldNode))
                groupEncountered = True
            elif fieldNode.tag == 'data':
                field = Data(fieldNode, self.schema)
                dataEncountered = True
            elif fieldNode.tag == 'field':
                if groupEncountered or dataEncountered:
                    raise Exception(f'field node specified after group or data node (message: "{self.name}")')
                field = Field(fieldNode, self.schema)
            else:
                raise Exception(f'unknown message member "{fieldNode.tag}" (message: "{self.name}")')

            if field.name in fieldByName:
                raise Exception(f'duplicate name "{field.name}" found (message: "{self.name}")')
            fieldByName[field.name] = field
            if field.id in fieldByID:
                raise Exception(f'duplicate id "{field.id}" found (message: "{self.name}")')
            fieldByID[field.id] = field

        return fieldByName.values()

    def _updateFieldsOffsetAndBlockLength(self) -> None:
        blockLength = 0
        for field in self.fields:
            if not isinstance(field, Field):
                break

            if field.offset == None:
                field.offset = blockLength
            else:
                if field.offset < blockLength:
                    raise Exception(f'invalid field offset value (message: "{self.name}", field: "{field.name}")')

            blockLength += field.type.encodedLength()

        if self.blockLength == None:
            self.blockLength = blockLength
        else:
            if self.blockLength < blockLength:
                raise Exception(f'invalid message blockLength value (message: "{self.name}")')

class Field:
    def __init__(self, node: ET.Element, schema: Schema) -> None:
        self.schema = schema
        self.name = attr(node, 'name')
        self.id = attr(node, 'id', cast=int)
        self.type = schema.getType(attr(node, 'type'))
        self.description = attr(node, 'description', None)
        self.offset = attr(node, 'offset', None, cast=int)
        self.semanticType = attr(node, 'semanticType', None)
        self.presence = attr(node, 'presence', self.type.presence, cast=Presence)
        self.valueRef = attr(node, "valueRef", None)
        self.sinceVersion = attr(node, 'sinceVersion', 0, cast=int)
        self.deprecated = attr(node, 'deprecated', 0, cast=int)
        self._validate()

    def _validate(self) -> None:
        if self.valueRef != None:
            self._validateValueRef()

        if isinstance(self.type, Enum) and self.presence == Presence.CONSTANT:
            if self.valueRef == None:
                raise Exception(f'valueRef not set for constant enum (field: "{self.name}")')

    def _validateValueRef(self) -> None:
        if self.valueRef.find('.') == -1:
            raise Exception(f'valueRef ({self.valueRef}) format not valid (field: "{self.name}")')

        name, value = self.valueRef.split('.')

        valueRefType = self.schema.getType(name)
        if not isinstance(valueRefType, Enum):
            raise Exception(f'valueRef ({self.valueRef}) is not of enum type (field: "{self.name}")')
        if value not in valueRefType.validValues.keys():
            raise Exception(f'valueRef ({self.valueRef}) not found (field: "{self.name}")')


class Group:
    def __init__(self, node: ET.Element, schema: Schema, fields: list[Any]) -> None:
        self.schema = schema
        self.name = attr(node, 'name')
        self.id = attr(node, 'id', cast=int)

        self.dimensionType = schema.getType(attr(node, 'dimensionType', 'groupSizeEncoding'))
        if not isinstance(self.dimensionType, Composite):
            raise Exception(f'dimensionType "{self.dimensionType.name}" should be composite type (field: "{self.name}")')
        self.dimensionType.checkForWellFormedGroupSizeEncoding()

        self.description = attr(node, 'description', None)
        self.blockLength = attr(node, 'blockLength', None, cast=int)
        self.sinceVersion = attr(node, 'sinceVersion', 0, cast=int)
        self.deprecated = attr(node, 'deprecated', 0, cast=int)
        self.fields = fields
        self._updateFieldsOffsetAndBlockLength()

    def _updateFieldsOffsetAndBlockLength(self) -> None:
        blockLength = 0
        for field in self.fields:
            if not isinstance(field, Field):
                break

            if field.offset == None:
                field.offset = blockLength
            else:
                if field.offset < blockLength:
                    raise Exception(f'invalid field offset value (group: "{self.name}", field: "{field.name}")')

            blockLength += field.type.encodedLength()

        if self.blockLength == None:
            self.blockLength = blockLength
        else:
            if self.blockLength < blockLength:
                raise Exception(f'invalid group blockLength value (group: "{self.name}")')

class Data:
    def __init__(self, node: ET.Element, schema: Schema) -> None:
        self.schema = schema
        self.name = attr(node, 'name')
        self.id = attr(node, 'id', cast=int)
        self.type = schema.getType(attr(node, 'type'))

        if not isinstance(self.type, Composite):
            raise Exception(f'dimensionType "{self.type.name}" should be composite type (field: "{self.name}")')
        self.type.checkForWellFormedVariableLengthDataEncoding()

        self.description = attr(node, 'description', None)
        self.offset = attr(node, 'offset', None, cast=int)
        self.semanticType = attr(node, 'semanticType', None)
        self.presence = attr(node, 'presence', self.type.presence, cast=Presence)
        self.sinceVersion = attr(node, 'sinceVersion', 0, cast=int)
        self.deprecated = attr(node, 'deprecated', 0, cast=int)
