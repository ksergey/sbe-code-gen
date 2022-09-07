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
    PrimitiveTypeByName = UniqueKeysDict({
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
    })

    ''' Primitive type names suitable for encodingType of enum '''
    ValidPrimitiveTypeForEnum = [ 'char', 'uint8', 'uint16', 'uint32', 'uint64' ]

    ''' Primitive type names suitable for encodingType of set '''
    ValidPrimitiveTypeForSet = [ 'uint8', 'uint16', 'uint32', 'uint64' ]

    def __init__(self, root: ET.Element) -> None:
        self.root = root

    @staticmethod
    def fromFile(path: str) -> Parser:
        root = loadXMLFromFile(path)
        return Parser(root)

    @staticmethod
    def getPrimitiveType(name: str) -> PrimitiveType:
        if name in Parser.PrimitiveTypeByName:
            return Parser.PrimitiveTypeByName[name]
        else:
            raise Exception(f'primitive type "{name}" not found')

    def getSchema(self) -> Schema:
        headerTypeStr = attr(self.root, 'headerType', 'messageHeader')
        headerType = self.getEncodedTypeByName(headerTypeStr)
        if not isinstance(headerType, Composite) or not headerType.isValidHeaderType():
            raise Exception(f'type "{headerType}" is not valid header type')

        return Schema(
            package = attr(self.root, 'package', default=None),
            id = attr(self.root, 'id', cast=int),
            version = attr(self.root, 'version', cast=int),
            semanticType = attr(self.root, 'semanticType', None),
            byteOrder = attr(self.root, 'byteOrder', 'littleEndian', cast=ByteOrder),
            description = attr(self.root, 'description', None),
            headerType = headerType,
            types = self.getTypes(),
            messages = self.getMessages()
        )

    def getTypes(self) -> Dict[str, EncodedType]:
        types = UniqueKeysDict()

        # add generic types
        for primitiveType in Parser.PrimitiveTypeByName.values():
            type = self.getPrimitiveTypeAsEncodedType(primitiveType)
            types[type.name] = type

        # load types from xml
        for node in self.root.findall('./types/*'):
            type = self.getEncodedType(node)
            types[type.name] = type

        return types

    def getMessages(self) -> Dict[str, Message]:
        messageByName = UniqueKeysDict()
        messageByID = UniqueKeysDict()
        for child in self.root.findall('./message'):
            message = self.getMessage(child)
            messageByName[message.name] = message
            messageByID[message.id] = message
        return messageByName

    @staticmethod
    def getPrimitiveTypeAsEncodedType(primitiveType: PrimitiveType) -> Type:
        return Type(
            name = primitiveType.name,
            description = None,
            presence = Presence.REQUIRED,
            nullValue = None,
            minValue = None,
            maxValue = None,
            length = 1,
            offset = None,
            primitiveType = primitiveType,
            semanticType = None,
            sinceVersion = 0,
            deprecated = None,
            constValue = None
        )

    def getType(self, node: ET.Element, offset: Optional[int] = None) -> Type:
        nameStr = attr(node, 'name')
        presence = attr(node, 'presence', Presence.REQUIRED, cast=Presence)
        length = attr(node, 'length', 1, cast=int)
        primitiveType = Parser.getPrimitiveType(attr(node, 'primitiveType'))
        valueRef = attr(node, 'valueRef', None)
        constValue = None

        '''
        For presence=constant
            constValue = node.text on valueRef not set
            constValue = valueRef on valueRef set
        '''
        if valueRef != None:
            if presence != Presence.CONSTANT:
                raise Exception(f'presence must be constant when valueRef is set (type "{nameStr}")')
            if not self.isValidValueRef(valueRef):
                raise Exception(f'valueRef "{valueRef}" of type "{nameStr}" is not valid')

        if presence == Presence.CONSTANT:
            if valueRef == None:
                constValue = node.text.strip()
                if constValue == '':
                    raise Exception(f'node text is empty and valueRef is not set for constant type "{nameStr}"')
                if primitiveType.name == 'char' and len(constValue) != length:
                    raise Exception(f'node text length is not equal to field length for constant type "{nameStr}"')
            else:
                enumName, enumValueName = valueRef.split('.')
                enumType = self.getEncodedTypeByName(enumName)
                assert (isinstance(enumType, Enum)), "not an enum type"
                constValue = enumType.validValueByName[enumValueName].value

        characterEncoding = None
        if primitiveType.name == 'char':
            characterEncoding = attr(node, 'characterEncoding', "US-ASCII")
        else:
            characterEncoding = attr(node, 'characterEncoding', None)
        if characterEncoding != None:
            characterEncoding.strip()

        return Type(
            name = nameStr,
            description = attr(node, 'description', None),
            presence = presence,
            nullValue = attr(node, 'nullValue', None),
            minValue = attr(node, 'minValue', None),
            maxValue = attr(node, 'maxValue', None),
            length = length,
            offset = attr(node, 'offset', offset, cast=int),
            primitiveType = primitiveType,
            semanticType = attr(node, 'semanticType', None),
            sinceVersion = attr(node, 'sinceVersion', 0, cast=int),
            deprecated = attr(node, 'deprecated', None, cast=int),
            valueRef = valueRef,
            constValue = constValue,
            characterEncoding = characterEncoding
        )

    def getComposite(self, node: ET.Element, offset: Optional[int] = None) -> Composite:
        nameStr = attr(node, 'name')

        # used for compute offset for each type inside composite
        computedOffset = 0

        containedTypes = UniqueKeysDict()
        for child in node:
            type = None
            if child.tag == 'type':
                type = self.getType(child, offset=computedOffset)
            elif child.tag == 'composite':
                type = self.getComposite(child, offset=computedOffset)
            elif child.tag == 'enum':
                type = self.getEnum(child, offset=computedOffset)
            elif child.tag == 'set':
                type = self.getSet(child, offset=computedOffset)
            elif child.tag == 'ref':
                type = self.getRef(child, offset=computedOffset)
            else:
                raise Exception(f'unknown composite type "{nameStr}" child node "{child.tag}"')

            if computedOffset > type.offset:
                raise Exception(f'invalid type offset "{type.name}" inside composite type "{nameStr}"')

            computedOffset = type.offset + type.encodedLength();
            containedTypes[type.name] = type

        return Composite(
            name = nameStr,
            offset = attr(node, 'offset', offset, cast=int),
            description = attr(node, 'description', None),
            semanticType = attr(node, 'semanticType', None),
            sinceVersion = attr(node, 'sinceVersion', 0, cast=int),
            deprecated = attr(node, 'deprecated', None, cast=int),
            containedTypes = containedTypes
        )

    def getValidValue(self, node: ET.Element) -> ValidValue:
        return ValidValue(
            name = attr(node, 'name'),
            description = attr(node, 'description', None),
            sinceVersion = attr(node, 'sinceVersion', 0, cast=int),
            deprecated = attr(node, 'deprecated', None, cast=int),
            value = node.text.strip()
        )

    def getEnum(self, node: ET.Element, offset: Optional[int] = None) -> Enum:
        nameStr = attr(node, 'name')

        validValueByName = UniqueKeysDict()
        for child in node:
            if child.tag == 'validValue':
                validValue = self.getValidValue(child)
                validValueByName[validValue.name] = validValue
            else:
                raise Exception(f'unexpected tag "{child.tag}" inside enum "{nameStr}" ')

        return Enum(
            name = nameStr,
            description = attr(node, 'description', None),
            encodingType = self.getEncodingTypeForEnum(attr(node, 'encodingType')),
            sinceVersion = attr(node, 'sinceVersion', 0, cast=int),
            deprecated = attr(node, 'deprecated', None, cast=int),
            offset = attr(node, 'offset', offset, cast=int),
            nullValue = attr(node, 'nullValue', None),
            validValueByName = validValueByName
        )

    def getChoice(self, node: ET.Element) -> Choice:
        return Choice(
            name = attr(node, 'name'),
            description = attr(node, 'description', None),
            sinceVersion = attr(node, 'sinceVersion', 0, cast=int),
            deprecated = attr(node, 'deprecated', None, cast=int),
            value = node.text.strip()
        )

    def getSet(self, node: ET.Element, offset: Optional[int] = None) -> Set:
        nameStr = attr(node, 'name')

        choiceByName = UniqueKeysDict()
        for child in node:
            if child.tag == 'choice':
                choice = self.getChoice(child)
                choiceByName[choice.name] = choice
            else:
                raise Exception(f'unexpected tag "{child.tag}" inside set "{nameStr}" ')

        return Set(
            name=nameStr,
            description = attr(node, 'description', None),
            encodingType = self.getEncodingTypeForSet(attr(node, 'encodingType')),
            sinceVersion = attr(node, 'sinceVersion', 0, cast=int),
            deprecated = attr(node, 'deprecated', None, cast=int),
            offset = attr(node, 'offset', offset, cast=int),
            choiceByName = choiceByName
        )

    def getRef(self, node: ET.Element, offset: Optional[int] = None) -> Ref:
        return Ref(
            name = attr(node, 'name'),
            type = self.getEncodedTypeByName(attr(node, 'type')),
            offset = attr(node, 'offset', offset, cast=int),
            description = attr(node, 'description', None),
            sinceVersion = attr(node, 'sinceVersion', 0, cast=int),
            deprecated = attr(node, 'deprecated', None, cast=int),
        )

    def getMessage(self, node: ET.Element) -> Message:
        nameStr = attr(node, 'name')

        computedOffset = 0
        groupEncountered = False
        dataEncountered = False

        fieldByName = UniqueKeysDict()
        fieldByID = UniqueKeysDict()
        for child in node:
            field = None
            if child.tag == 'field':
                if groupEncountered or dataEncountered:
                    raise Exception(f'field node specified after group or data node in message "{nameStr}"')
                field = self.getField(child, offset=computedOffset)

                if computedOffset > field.offset:
                    raise Exception(f'invalid field offset "{field.name}" inside message "{nameStr}"')
                computedOffset = field.offset + field.encodedLength()

            elif child.tag == 'group':
                if dataEncountered:
                    raise Exception(f'group node specified after data node in message "{nameStr}"')
                field = self.getGroup(child)
                groupEncountered = True
            elif child.tag == 'data':
                field = self.getData(child)
                dataEncountered = True
            else:
                raise Exception(f'unknown message "{nameStr}" child node "{child.tag}"')

            fieldByName[field.name] = field
            fieldByID[field.id] = field

        blockLength = attr(node, 'blockLength', computedOffset, cast=int)
        if blockLength < computedOffset:
            raise Exception(f'invalid blockLength value for message "{nameStr}"')

        return Message(
            name = nameStr,
            id = attr(node, 'id', cast=int),
            description = attr(node, 'description', None),
            blockLength = blockLength,
            semanticType = attr(node, 'semanticType', None),
            sinceVersion = attr(node, 'sinceVersion', 0, cast=int),
            deprecated = attr(node, 'deprecated', None, cast=int),
            fields = fieldByName
        )

    def getField(self, node: ET.Element, offset: int) -> Field:
        nameStr = attr(node, 'name')
        type = self.getEncodedTypeByName(attr(node, 'type'))
        presence = attr(node, 'presence', type.presence if isinstance(type, Type) else Presence.REQUIRED, cast=Presence)
        valueRef = attr(node, 'valueRef', None)

        if valueRef != None and not self.isValidValueRef(valueRef):
            raise Exception(f'valueRef "{valueRef}" of type "{nameStr}" is not valid')

        if presence == Presence.CONSTANT:
            if isinstance(type, Enum):
                if valueRef == None:
                    raise Exception(f'valueRef not set for constant enum field "{nameStr}"')
                if not self.isValidValueRef(valueRef):
                    raise Exception(f'valueRef "{valueRef}" for type "{nameStr}" is not valid')
            elif isinstance(type, Type):
                if type.constValue == None:
                    raise Exception(f'constValue not set of type for field "{nameStr}"')
            else:
                raise Exception(f'field "{fieldNode}" is constant but encoding type is not enum or type')

        if isinstance(type, Set):
            if presence != Presence.REQUIRED:
                raise Exception(f'field "{nameStr}" of type "{type.name}" should be required')

        if isinstance(type, Composite):
            if presence == Presence.CONSTANT:
                raise Exception(f'field "{nameStr}" of type "{type.name}" should not be constant')

        return Field(
            name = nameStr,
            id = attr(node, 'id', cast=int),
            description = attr(node, 'description', None),
            type = type,
            offset = attr(node, 'offset', offset, cast=int),
            presence = presence,
            valueRef = valueRef,
            semanticType = attr(node, 'semanticType', None),
            sinceVersion = attr(node, 'sinceVersion', 0, cast=int),
            deprecated = attr(node, 'deprecated', None, cast=int)
        )

    def getGroup(self, node: ET.Element) -> Group:
        nameStr = attr(node, 'name')

        computedOffset = 0
        groupEncountered = False
        dataEncountered = False

        fieldByName = UniqueKeysDict()
        fieldByID = UniqueKeysDict()
        for child in node:
            field = None
            if child.tag == 'field':
                if groupEncountered or dataEncountered:
                    raise Exception(f'field node specified after group or data node in group "{nameStr}"')
                field = self.getField(child, offset=computedOffset)

                if computedOffset > field.offset:
                    raise Exception(f'invalid field offset "{field.name}" inside group "{nameStr}"')
                computedOffset = field.offset + field.encodedLength()

            elif child.tag == 'group':
                if dataEncountered:
                    raise Exception(f'group node specified after data node in group "{nameStr}"')
                field = self.getGroup(child)
                groupEncountered = True
            elif child.tag == 'data':
                field = self.getData(child)
                dataEncountered = True
            else:
                raise Exception(f'unknown group "{nameStr}" child node "{child.tag}"')

            fieldByName[field.name] = field
            fieldByID[field.id] = field

        blockLength = attr(node, 'blockLength', computedOffset, cast=int)
        if blockLength < computedOffset:
            raise Exception(f'invalid blockLength value for group "{nameStr}"')

        dimensionTypeStr = attr(node, 'dimensionType', 'groupSizeEncoding')
        dimensionType = self.getEncodedTypeByName(dimensionTypeStr)
        if not isinstance(dimensionType, Composite) or not dimensionType.isValidDimensionType():
            raise Exception(f'type "{dimensionTypeStr}" is not valid dimension type')

        return Group(
            name = nameStr,
            id = attr(node, 'id', cast=int),
            description = attr(node, 'description', None),
            dimensionType = dimensionType,
            blockLength = blockLength,
            fields = fieldByName
        )

    def getData(self, node: ET.Element) -> Data:
        typeStr = attr(node, 'type')
        type = self.getEncodedTypeByName(typeStr)
        if not isinstance(type, Composite) or not type.isValidVariableLength():
            raise Exception(f'type "{typeStr}" is not valid type for data')

        return Data(
            name = attr(node, 'name'),
            id = attr(node, 'id', cast=int),
            description = attr(node, 'description', None),
            type = type,
            semanticType = attr(node, 'semanticType', None),
            sinceVersion = attr(node, 'sinceVersion', 0, cast=int),
            deprecated = attr(node, 'deprecated', None, cast=int)
        )

    def getEncodingTypeForEnum(self, encodingTypeStr: str) -> PrimitiveType:
        if encodingTypeStr in self.ValidPrimitiveTypeForEnum:
            return self.getPrimitiveType(encodingTypeStr)

        encodingTypeNode = self.root.find(f'.//types/type[@name="{encodingTypeStr}"]')
        if encodingTypeNode == None:
            raise Exception(f'encodingType "{encodingTypeStr}" for enum not found')

        encodingType = self.getType(encodingTypeNode)
        primitiveType = encodingType.primitiveType
        if primitiveType.name not in self.ValidPrimitiveTypeForEnum:
            raise Exception(f'type "{encodingTypeStr}" is not suitable for enum encodingType')

        return primitiveType

    def getEncodingTypeForSet(self, encodingTypeStr: str) -> PrimitiveType:
        if encodingTypeStr in self.ValidPrimitiveTypeForSet:
            return self.getPrimitiveType(encodingTypeStr)

        encodingTypeNode = self.root.find(f'.//types/type[@name="{encodingTypeStr}"]')
        if encodingTypeNode == None:
            raise Exception(f'encodingType "{encodingTypeStr}" for set not found')

        encodingType = self.getType(encodingTypeNode)
        primitiveType = encodingType.primitiveType
        if primitiveType.name not in self.ValidPrimitiveTypeForSet:
            raise Exception(f'type "{encodingTypeStr}" is not suitable for set encodingType')

        return primitiveType

    def getEncodedType(self, node: ET.Element) -> EncodedType:
        if node.tag == 'type':
            return self.getType(node)
        elif node.tag == 'composite':
            return self.getComposite(node)
        elif node.tag == 'enum':
            return self.getEnum(node)
        elif node.tag == 'set':
            return self.getSet(node)
        else:
            raise Exception(f'unknown node type definition (node: "{node.tag}")')

    def getEncodedTypeByName(self, name: str) -> EncodedType:
        ''' first check type exist in xml '''
        typeNode = self.root.find(f'.//types/*[@name="{name}"]')
        if typeNode != None:
            return self.getEncodedType(typeNode)

        ''' now check type is primitive type '''
        if name in Parser.PrimitiveTypeByName:
            return self.getPrimitiveTypeAsEncodedType(Parser.PrimitiveTypeByName[name])

        raise Exception(f'type "{name}" not found')

    ''' Return True on valueRef is valid and False otherwise '''
    def isValidValueRef(self, valueRef: str) -> bool:
        enumName, enumValueName = valueRef.split('.')
        enumType = self.getEncodedTypeByName(enumName)
        if not isinstance(enumType, Enum):
            return False
        if enumValueName not in enumType.validValueByName:
            return False
        return True
