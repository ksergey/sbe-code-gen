from __future__ import annotations

from enum import Enum

class Presence(Enum):
    REQUIRED = 'required'
    OPTIONAL = 'optional'
    CONSTANT = 'constant'

class ByteOrder(Enum):
    LITTLE_ENDIAN = 'littleEndian'
    BIG_ENDIAN = 'bitEndian'

class PrimitiveType:
    def __init__(self, name: str, size: int, nullValue: str, minValue: str, maxValue: str):
        self.name = name
        self.size = size
        self.nullValue = nullValue
        self.minValue = minValue
        self.maxValue = maxValue
