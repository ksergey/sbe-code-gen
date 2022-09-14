# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Union

class Presence(enum.Enum):
    REQUIRED = 'required'
    OPTIONAL = 'optional'
    CONSTANT = 'constant'

class ByteOrder(enum.Enum):
    LITTLE_ENDIAN = 'littleEndian'
    BIG_ENDIAN = 'bitEndian'

@dataclass(frozen=True)
class PrimitiveType:
    name: str = field(default_factory=str)
    size: int = field(default_factory=int)
    nullValue: str = field(default_factory=str)
    minValue: str = field(default_factory=str)
    maxValue: str = field(default_factory=str)

@dataclass(frozen=True)
class Type:
    name: str = field(default_factory=str)
    description: Optional[str] = field(default=None)
    presence: Presence = field(default=Presence.REQUIRED)
    nullValue: Optional[str] = field(default=None)
    minValue: Optional[str] = field(default=None)
    maxValue: Optional[str] = field(default=None)
    length: int = field(default=1)
    offset: Optional[int] = field(default=None)
    primitiveType: str = field(default_factory=str)
    semanticType: Optional[str] = field(default=None)
    sinceVersion: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    valueRef: Optional[str] = field(default=None)
    constValue: Optional[str] = field(default=None)
    characterEncoding: Optional[str] = field(default=None)

    def encodedLength(self) -> int:
        if self.presence == Presence.CONSTANT:
            return 0
        else:
            return self.length * self.primitiveType.size

@dataclass(frozen=True)
class Composite:
    name: str = field(default_factory=str)
    offset: Optional[int] = field(default=None)
    description: Optional[str] = field(default=None)
    semanticType: Optional[str] = field(default=None)
    sinceVersion: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    containedTypes: Dict[str, Union[Type, Composite, Enum, Set, Ref]] = field(default_factory=dict)

    def encodedLength(self) -> int:
        length = 0
        for type in self.containedTypes.values():
            assert (type.offset != None), "offset inside composite type must be present"
            if type.offset != None:
                length = type.offset
            length += type.encodedLength()
        return length

    ''' Find contained type by name. Return EncodedType on success and None otherwise '''
    def findType(self, name: str) -> Optional[EncodedType]:
        return self.containedTypes[name] if name in self.containedTypes else None

    ''' Return True on composite is valid dimension type '''
    def isValidDimensionType(self) -> bool:
        if not self.findType('blockLength'):
            return False
        if not self.findType('numInGroup'):
            return False
        return True

    ''' Return True on composite is valid header type '''
    def isValidHeaderType(self) -> bool:
        if not self.findType('blockLength'):
            return False
        if not self.findType('templateId'):
            return False
        if not self.findType('schemaId'):
            return False
        if not self.findType('version'):
            return False
        return True

    ''' Return True on composite is valid variable length type '''
    def isValidVariableLength(self) -> bool:
        lengthType = self.findType('length')
        if lengthType == None:
            return False
        if lengthType.primitiveType.name not in ('uint8', 'uint16', 'uint32', 'uint64'):
            return False

        varDataType = self.findType('varData')
        if varDataType == None:
            return False
        if varDataType.length != 0:
            return False
        if varDataType.primitiveType.name not in ('char', 'uint8'):
            return False

        return True

@dataclass(frozen=True)
class Enum:
    name: str = field(default_factory=str)
    description: Optional[str] = field(default=None)
    encodingType: PrimitiveType = field(default_factory=PrimitiveType)
    sinceVersion: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    offset: Optional[int] = field(default=None)
    nullValue: Optional[str] = field(default=None),
    validValueByName: Dict[str, ValidValue] = field(default_factory=dict)

    def encodedLength(self) -> int:
        return self.encodingType.size

@dataclass(frozen=True)
class ValidValue:
    name: str = field(default_factory=str)
    description: Optional[str] = field(default=None)
    sinceVersion: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    value: str = field(default_factory=str)

@dataclass(frozen=True)
class Set:
    name: str = field(default_factory=str)
    description: Optional[str] = field(default=None)
    encodingType: PrimitiveType = field(default_factory=PrimitiveType)
    sinceVersion: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    offset: Optional[int] = field(default=None)
    choiceByName: Dict[str, Choice] = field(default_factory=dict)

    def encodedLength(self) -> int:
        return self.encodingType.size

@dataclass(frozen=True)
class Choice:
    name: str = field(default_factory=str)
    description: Optional[str] = field(default=None)
    sinceVersion: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    value: str = field(default_factory=str)

@dataclass(frozen=True)
class Ref:
    name: str = field(default_factory=str)
    type: EncodedType = field(default=None)
    offset: Optional[int] = field(default=None)
    description: Optional[str] = field(default=None)
    sinceVersion: int = field(default=0)
    deprecated: Optional[int] = field(default=None)

    def encodedLength(self) -> int:
        return self.type.encodedLength()

@dataclass(frozen=True)
class Message:
    name: str = field(default_factory=str)
    id: int = field(default_factory=int)
    description: Optional[str] = field(default=None)
    blockLength: Optional[int] = field(default=None)
    semanticType: Optional[str] = field(default=None)
    sinceVersion: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    fields: Dict[str, EncodedType] = field(default_factory=dict)

@dataclass(frozen=True)
class Field:
    name: str = field(default_factory=str)
    id: int = field(default_factory=int)
    description: Optional[str] = field(default=None)
    type: EncodedType = field(default=None)
    offset: Optional[int] = field(default=None)
    presence: Presence = field(default=Presence.REQUIRED)
    valueRef: Optional[str] = field(default=None)
    semanticType: Optional[str] = field(default=None)
    sinceVersion: int = field(default=0)
    deprecated: Optional[int] = field(default=None)

    def encodedLength(self) -> int:
        if self.presence == Presence.CONSTANT:
            return 0
        return self.type.encodedLength()

@dataclass(frozen=True)
class Group:
    name: str = field(default_factory=str)
    id: int = field(default_factory=int)
    description: Optional[str] = field(default=None)
    dimensionType: Composite = field(default_factory=Composite)
    blockLength: Optional[int] = field(default=None)
    fields: Dict[str, Union[Field, Group, Data]] = field(default_factory=dict)

@dataclass(frozen=True)
class Data:
    name: str = field(default_factory=str)
    id: int = field(default_factory=int)
    description: Optional[str] = field(default=None)
    type: Composite = field(default_factory=Composite)
    semanticType: Optional[str] = field(default=None)
    sinceVersion: int = field(default=0)
    deprecated: Optional[int] = field(default=None)

@dataclass(frozen=True)
class Schema:
    package: Optional[str] = field(default=None)
    id: int = field(default_factory=int)
    version: int = field(default=0)
    semanticType: Optional[str] = field(default=None)
    byteOrder: ByteOrder = field(default=ByteOrder.LITTLE_ENDIAN)
    description: Optional[str] = field(default=None)
    headerType: Composite = field(default_factory=Composite)
    types: Dict[str, EncodedType] = field(default_factory=dict)
    messages: Dict[str, Message] = field(default_factory=dict)

EncodedType = Union[Type, Composite, Enum, Set]
