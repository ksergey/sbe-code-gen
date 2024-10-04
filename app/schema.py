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
    null_value: str = field(default_factory=str)
    min_value: str = field(default_factory=str)
    max_value: str = field(default_factory=str)

@dataclass(frozen=True)
class Type:
    name: str = field(default_factory=str)
    description: Optional[str] = field(default=None)
    presence: Presence = field(default=Presence.REQUIRED)
    null_value: Optional[str] = field(default=None)
    min_value: Optional[str] = field(default=None)
    max_value: Optional[str] = field(default=None)
    length: int = field(default=1)
    offset: Optional[int] = field(default=None)
    primitive_type: str = field(default_factory=str)
    semantic_type: Optional[str] = field(default=None)
    since_version: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    value_ref: Optional[str] = field(default=None)
    const_value: Optional[str] = field(default=None)
    character_encoding: Optional[str] = field(default=None)

    def encoded_length(self) -> int:
        if self.presence == Presence.CONSTANT:
            return 0
        else:
            return self.length * self.primitive_type.size

@dataclass(frozen=True)
class Composite:
    name: str = field(default_factory=str)
    offset: Optional[int] = field(default=None)
    description: Optional[str] = field(default=None)
    semantic_type: Optional[str] = field(default=None)
    since_version: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    contained_types: Dict[str, Union[Type, Composite, Enum, Set, Ref]] = field(default_factory=dict)

    def encoded_length(self) -> int:
        length = 0
        for contained_type in self.contained_types.values():
            assert (contained_type.offset != None), "offset inside composite type must be present"
            if contained_type.offset != None:
                length = contained_type.offset
            length += contained_type.encoded_length()
        return length

    ''' Find contained type by name. Return EncodedType on success and None otherwise '''
    def find_type(self, name: str) -> Optional[EncodedType]:
        return self.contained_types[name] if name in self.contained_types else None

    ''' Return True on composite is valid dimension type '''
    def is_valid_dimension_type(self) -> bool:
        if not self.find_type('blockLength'):
            return False
        if not self.find_type('numInGroup'):
            return False
        return True

    ''' Return True on composite is valid header type '''
    def is_valid_header_type(self) -> bool:
        if not self.find_type('blockLength'):
            return False
        if not self.find_type('templateId'):
            return False
        if not self.find_type('schemaId'):
            return False
        if not self.find_type('version'):
            return False
        return True

    ''' Return True on composite is valid variable length type '''
    def is_valid_variable_length(self) -> bool:
        length_type = self.find_type('length')
        if length_type == None:
            return False
        if length_type.primitive_type.name not in ('uint8', 'uint16', 'uint32', 'uint64'):
            return False
        var_data_type = self.find_type('varData')
        if var_data_type == None:
            return False
        if var_data_type.length != 0:
            return False
        if var_data_type.primitive_type.name not in ('char', 'uint8'):
            return False
        return True

@dataclass(frozen=True)
class Enum:
    name: str = field(default_factory=str)
    description: Optional[str] = field(default=None)
    presence: Presence = field(default=Presence.REQUIRED)
    encoding_type: PrimitiveType = field(default_factory=PrimitiveType)
    since_version: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    offset: Optional[int] = field(default=None)
    null_value: Optional[str] = field(default=None)
    valid_value_by_name: Dict[str, ValidValue] = field(default_factory=dict)

    def encoded_length(self) -> int:
        return self.encoding_type.size

@dataclass(frozen=True)
class ValidValue:
    name: str = field(default_factory=str)
    description: Optional[str] = field(default=None)
    since_version: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    value: str = field(default_factory=str)

@dataclass(frozen=True)
class Set:
    name: str = field(default_factory=str)
    description: Optional[str] = field(default=None)
    presence: Presence = field(default=Presence.REQUIRED)
    encoding_type: PrimitiveType = field(default_factory=PrimitiveType)
    since_version: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    offset: Optional[int] = field(default=None)
    choice_by_name: Dict[str, Choice] = field(default_factory=dict)

    def encoded_length(self) -> int:
        return self.encoding_type.size

@dataclass(frozen=True)
class Choice:
    name: str = field(default_factory=str)
    description: Optional[str] = field(default=None)
    since_version: int = field(default=0)
    deprecated: Optional[int] = field(default=None)
    value: str = field(default_factory=str)

@dataclass(frozen=True)
class Ref:
    name: str = field(default_factory=str)
    type: EncodedType = field(default=None)
    offset: Optional[int] = field(default=None)
    description: Optional[str] = field(default=None)
    since_version: int = field(default=0)
    deprecated: Optional[int] = field(default=None)

    def encoded_length(self) -> int:
        return self.type.encoded_length()

@dataclass(frozen=True)
class Message:
    name: str = field(default_factory=str)
    id: int = field(default_factory=int)
    description: Optional[str] = field(default=None)
    block_length: Optional[int] = field(default=None)
    semantic_type: Optional[str] = field(default=None)
    since_version: int = field(default=0)
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
    value_ref: Optional[str] = field(default=None)
    semantic_type: Optional[str] = field(default=None)
    since_version: int = field(default=0)
    deprecated: Optional[int] = field(default=None)

    def encoded_length(self) -> int:
        if self.presence == Presence.CONSTANT:
            return 0
        return self.type.encoded_length()

@dataclass(frozen=True)
class Group:
    name: str = field(default_factory=str)
    id: int = field(default_factory=int)
    description: Optional[str] = field(default=None)
    dimension_type: Composite = field(default_factory=Composite)
    block_length: Optional[int] = field(default=None)
    fields: Dict[str, Union[Field, Group, Data]] = field(default_factory=dict)

@dataclass(frozen=True)
class Data:
    name: str = field(default_factory=str)
    id: int = field(default_factory=int)
    description: Optional[str] = field(default=None)
    type: Composite = field(default_factory=Composite)
    semantic_type: Optional[str] = field(default=None)
    since_version: int = field(default=0)
    deprecated: Optional[int] = field(default=None)

@dataclass(frozen=True)
class Schema:
    package: Optional[str] = field(default=None)
    id: int = field(default_factory=int)
    version: int = field(default=0)
    semantic_type: Optional[str] = field(default=None)
    byte_order: ByteOrder = field(default=ByteOrder.LITTLE_ENDIAN)
    description: Optional[str] = field(default=None)
    header_type: Composite = field(default_factory=Composite)
    types: Dict[str, EncodedType] = field(default_factory=dict)
    messages: Dict[str, Message] = field(default_factory=dict)

EncodedType = Union[Type, Composite, Enum, Set]
