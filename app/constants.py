# Copyright (C) 2026 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

from typing import Any, Dict

# Decoded values of primitive type min/max/null constants, i.e.
#     UINT8_MIN  -> 0
#     UINT8_MAX  -> 254
#     UINT8_NULL -> 255
PRIMITIVE_CONSTANTS: Dict[str, Any] = {
    'CHAR_NULL':    0,
    'CHAR_MIN':     0x20,
    'CHAR_MAX':     0x7e,
    'INT8_NULL':    -128,
    'INT8_MIN':     -127,
    'INT8_MAX':     127,
    'INT16_NULL':   -32768,
    'INT16_MIN':    -32767,
    'INT16_MAX':    32767,
    'INT32_NULL':   -2147483648,
    'INT32_MIN':    -2147483647,
    'INT32_MAX':    2147483647,
    'INT64_NULL':   -9223372036854775808,
    'INT64_MIN':    -9223372036854775807,
    'INT64_MAX':    9223372036854775807,
    'UINT8_NULL':   255,
    'UINT8_MIN':    0,
    'UINT8_MAX':    254,
    'UINT16_NULL':  65535,
    'UINT16_MIN':   0,
    'UINT16_MAX':   65534,
    'UINT32_NULL':  4294967295,
    'UINT32_MIN':   0,
    'UINT32_MAX':   4294967294,
    'UINT64_NULL':  18446744073709551615,
    'UINT64_MIN':   0,
    'UINT64_MAX':   18446744073709551614,
    'FLOAT_NULL':   float('nan'),
    'FLOAT_MIN':    1.1754943508222875e-38,
    'FLOAT_MAX':    3.4028234663852886e+38,
    'DOUBLE_NULL':  float('nan'),
    'DOUBLE_MIN':   2.2250738585072014e-308,
    'DOUBLE_MAX':   1.7976931348623157e+308
}

def decode_primitive_constant(value: str):
    return PRIMITIVE_CONSTANTS.get(value, value)