"""Python codec tests for resources/all_types_big_endian_1_0.xml.

Mirrors tests/all_types_big_endian_test.cpp (same schema, byteOrder="bigEndian",
minus the fixed-length numeric array field that big-endian doesn't support).
On top of the round-trip coverage, this also checks the raw wire bytes
directly for one field - round-tripping alone would still pass even if
encode and decode agreed on the *wrong* byte order, the way real-logic's own
SBE tests check actual byte sequences rather than only symmetry.
"""

import importlib.util
import struct
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / 'resources' / 'all_types_big_endian_1_0.xml'

HEADER_LENGTH = 8
U32_FIELD_OFFSET = 26  # relative to the message body, right after the header


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='session')
def schema(tmp_path_factory):
    dest = tmp_path_factory.mktemp('all_types_be_codec') / 'python'
    subprocess.run(
        [sys.executable, '-m', 'app',
         '--schema', str(SCHEMA_PATH),
         '--destination', str(dest),
         '--generator', 'python'],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return _load_module(dest / 'schema.py', 'all_types_be_generated_schema')


@pytest.fixture
def make_message(schema):
    def _make(**overrides):
        base = dict(
            id=0, qty=0, price=0, s8=0, s16=0, u8=0, u16=0, u32=0, f32=0.0, f64=0.0,
            mType=schema.MessageType.NewOrder,
            side=schema.Side.Buy,
            bigType=schema.BigType.Alpha,
            flags=schema.Flags(0),
            bigFlags=schema.BigFlags(0),
            symbol='',
            decimal1=schema.Decimal(mantissa=0, exponent=0),
            outerField=schema.OuterComposite(
                qty=0, dec=schema.Decimal(mantissa=0, exponent=0), side=schema.Side.Buy, flags=schema.Flags(0)),
            nestedField=schema.NestedComposite(
                topVal=0, inner=schema.NestedComposite_Inner(innerVal=0, innerTag='')),
            wideEnum32=schema.WideEnum32.ValueA,
            wideEnum64=schema.WideEnum64.BigA,
            bits=schema.Bits8.Off,
        )
        base.update(overrides)
        return schema.AllTypesMessageMessage(**base)

    return _make


def _round_trip(schema, message):
    buffer = schema.encode(schema.AllTypesMessageMessage, message)
    return buffer, schema.decode(buffer)


def test_metadata(schema):
    assert schema.AllTypesMessageMessage.TEMPLATE_ID == 1
    assert schema.AllTypesMessageMessage.BLOCK_LENGTH == 134
    assert schema.EmptyMessageMessage.TEMPLATE_ID == 2
    assert schema.DataOnlyMessageMessage.TEMPLATE_ID == 3


def test_header_round_trip(schema, make_message):
    _, result = _round_trip(schema, make_message())
    assert result.header.blockLength == schema.AllTypesMessageMessage.BLOCK_LENGTH
    assert result.header.templateId == schema.AllTypesMessageMessage.TEMPLATE_ID
    assert result.header.schemaId == schema.Schema.SCHEMA_ID
    assert result.header.version == schema.Schema.VERSION


def test_scalars_and_enums_round_trip(schema, make_message):
    message = make_message(
        id=7, qty=9, price=-3, s8=-8, s16=-16, u8=3, u16=66, u32=66_666,
        f32=1.25, f64=2.5,
        mType=schema.MessageType.ExecutionReport,
        side=schema.Side.Sell,
        bigType=schema.BigType.Gamma,
        bits=schema.Bits8.On,
        wideEnum32=schema.WideEnum32.ValueB,
        wideEnum64=schema.WideEnum64.BigB,
    )
    _, result = _round_trip(schema, message)
    decoded = result.message

    assert decoded.id == 7
    assert decoded.qty == 9
    assert decoded.price == -3
    assert decoded.s8 == -8
    assert decoded.s16 == -16
    assert decoded.u8 == 3
    assert decoded.u16 == 66
    assert decoded.u32 == 66_666
    assert decoded.f32 == pytest.approx(1.25)
    assert decoded.f64 == pytest.approx(2.5)
    assert decoded.mType == schema.MessageType.ExecutionReport
    assert decoded.side == schema.Side.Sell
    assert decoded.bigType == schema.BigType.Gamma
    assert decoded.bits == schema.Bits8.On
    assert decoded.wideEnum32 == schema.WideEnum32.ValueB
    assert decoded.wideEnum64 == schema.WideEnum64.BigB


def test_wire_bytes_are_actually_big_endian(schema, make_message):
    """Round-tripping is not proof of byte order - a codec that encoded and
    decoded as little-endian consistently would round-trip too. Read the
    u32 field straight off the wire with an explicit '>I' struct format and
    compare against what a '<I' read would give, to prove the bytes
    themselves are big-endian, not just that encode/decode agree with
    each other."""
    buffer, _ = _round_trip(schema, make_message(u32=0x01020304))
    field_start = HEADER_LENGTH + U32_FIELD_OFFSET
    raw = buffer[field_start:field_start + 4]

    assert struct.unpack('>I', raw)[0] == 0x01020304
    assert struct.unpack('<I', raw)[0] != 0x01020304
    assert raw == bytes([0x01, 0x02, 0x03, 0x04])


def test_sets_and_composites_round_trip(schema, make_message):
    message = make_message(
        flags=schema.Flags.Bit0 | schema.Flags.Bit7,
        bigFlags=schema.BigFlags.Top,
        symbol='BTC-USD',
        decimal1=schema.Decimal(mantissa=123_456, exponent=-4),
        outerField=schema.OuterComposite(
            qty=5, dec=schema.Decimal(mantissa=11, exponent=-1), side=schema.Side.Sell, flags=schema.Flags(0)),
        nestedField=schema.NestedComposite(
            topVal=3, inner=schema.NestedComposite_Inner(innerVal=-77, innerTag='hi')),
    )
    _, result = _round_trip(schema, message)
    decoded = result.message

    assert schema.Flags.Bit0 in decoded.flags
    assert schema.Flags.Bit7 in decoded.flags
    assert schema.BigFlags.Top in decoded.bigFlags
    assert decoded.symbol == 'BTC-USD'
    assert decoded.decimal1 == schema.Decimal(mantissa=123_456, exponent=-4)
    assert decoded.outerField.side == schema.Side.Sell
    assert decoded.nestedField.inner.innerTag == 'hi'


def test_optional_fields(schema, make_message):
    _, absent = _round_trip(schema, make_message())
    assert absent.message.optSide is None
    assert absent.message.optString is None

    present = make_message(optVal=-100, optSide=schema.Side.Buy, optString='abcdef')
    _, result = _round_trip(schema, present)
    assert result.message.optVal == -100
    assert result.message.optSide == schema.Side.Buy
    assert result.message.optString == 'abcdef'


def test_groups_round_trip(schema, make_message):
    entries = [
        schema.AllTypesMessageMessage_Entries(
            seq=1, amount=100_000, tag='ab', tflags=schema.Flags.Bit0,
            ttype=schema.MessageType.NewOrder,
            tDec=schema.Decimal(mantissa=9_999, exponent=2),
            sub=[schema.AllTypesMessageMessage_Entries_Sub(subId=10, subVal=100)],
            note='note!',
        ),
    ]
    _, result = _round_trip(schema, make_message(entries=entries))
    decoded = result.message

    assert len(decoded.entries) == 1
    assert decoded.entries[0].seq == 1
    assert decoded.entries[0].sub[0].subId == 10
    assert decoded.entries[0].note == 'note!'


def test_variable_length_data_round_trip(schema, make_message):
    message = make_message(traceId='trace-1', summary='spread summary', blob=[1, 2, 3, 4])
    _, result = _round_trip(schema, message)
    decoded = result.message

    assert decoded.traceId == 'trace-1'
    assert decoded.summary == 'spread summary'
    assert decoded.blob == [1, 2, 3, 4]


def test_empty_and_data_only_messages(schema):
    buffer = schema.encode(schema.EmptyMessageMessage, schema.EmptyMessageMessage())
    result = schema.decode(buffer)
    assert result.header.templateId == schema.EmptyMessageMessage.TEMPLATE_ID

    data_only = schema.DataOnlyMessageMessage(payload='hello')
    buffer = schema.encode(schema.DataOnlyMessageMessage, data_only)
    result = schema.decode(buffer)
    assert result.message.payload == 'hello'
