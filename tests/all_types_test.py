"""Python codec tests for resources/all_types_1_0.xml.

Mirrors tests/all_types_test.cpp: it exercises every SBE data type and
message construct (scalars, enums, sets, fixed-length arrays, composites,
nested composites, optional fields, constants, repeating groups - including
a group nested inside another group - and variable-length data) through the
generated Python codec, the same way real-logic's own SBE test suites drive
every codec they generate against one "kitchen sink" schema.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / 'resources' / 'all_types_1_0.xml'


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses needs this to resolve ClassVar annotations
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='session')
def schema(tmp_path_factory):
    dest = tmp_path_factory.mktemp('all_types_codec') / 'python'
    subprocess.run(
        [sys.executable, '-m', 'app',
         '--schema', str(SCHEMA_PATH),
         '--destination', str(dest),
         '--generator', 'python'],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return _load_module(dest / 'schema.py', 'all_types_generated_schema')


@pytest.fixture
def make_message(schema):
    """A message with every required (non-optional, non-defaulted) field
    filled in with an innocuous value, so each test only has to spell out
    the field(s) it actually cares about - the same role makeBuffer() (a
    zeroed buffer) plays in the C++ test."""

    def _make(**overrides):
        base = dict(
            id=0, qty=0, price=0, s8=0, s16=0, u8=0, u16=0, u32=0, f32=0.0, f64=0.0,
            mType=schema.MessageType.NewOrder,
            side=schema.Side.Buy,
            bigType=schema.BigType.Alpha,
            flags=schema.Flags(0),
            bigFlags=schema.BigFlags(0),
            symbol='',
            history=[0, 0, 0, 0],
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
    return schema.decode(buffer)


def test_metadata(schema):
    assert schema.AllTypesMessageMessage.TEMPLATE_ID == 1
    assert schema.AllTypesMessageMessage.BLOCK_LENGTH == 150
    assert schema.EmptyMessageMessage.TEMPLATE_ID == 2
    assert schema.EmptyMessageMessage.BLOCK_LENGTH == 0
    assert schema.DataOnlyMessageMessage.TEMPLATE_ID == 3
    assert schema.DataOnlyMessageMessage.BLOCK_LENGTH == 0


def test_header_round_trip(schema, make_message):
    result = _round_trip(schema, make_message())
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
    decoded = _round_trip(schema, message).message

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


def test_sets_and_fixed_arrays_round_trip(schema, make_message):
    message = make_message(
        flags=schema.Flags.Bit0 | schema.Flags.Bit2 | schema.Flags.Bit7,
        bigFlags=schema.BigFlags.First | schema.BigFlags.Top,
        symbol='BTC-USD',
        history=[1, 2, 3, 4],
    )
    decoded = _round_trip(schema, message).message

    assert schema.Flags.Bit0 in decoded.flags
    assert schema.Flags.Bit2 in decoded.flags
    assert schema.Flags.Bit5 not in decoded.flags
    assert schema.Flags.Bit7 in decoded.flags

    assert schema.BigFlags.First in decoded.bigFlags
    assert schema.BigFlags.Top in decoded.bigFlags

    assert decoded.symbol == 'BTC-USD'
    assert decoded.history == [1, 2, 3, 4]


def test_composites_round_trip(schema, make_message):
    message = make_message(
        decimal1=schema.Decimal(mantissa=123_456, exponent=-4),
        outerField=schema.OuterComposite(
            qty=5, dec=schema.Decimal(mantissa=11, exponent=-1), side=schema.Side.Sell, flags=schema.Flags(0)),
        nestedField=schema.NestedComposite(
            topVal=3, inner=schema.NestedComposite_Inner(innerVal=-77, innerTag='hi')),
    )
    decoded = _round_trip(schema, message).message

    assert decoded.decimal1 == schema.Decimal(mantissa=123_456, exponent=-4)

    assert decoded.outerField.qty == 5
    assert decoded.outerField.dec == schema.Decimal(mantissa=11, exponent=-1)
    assert decoded.outerField.side == schema.Side.Sell

    assert decoded.nestedField.topVal == 3
    assert decoded.nestedField.inner.innerVal == -77
    assert decoded.nestedField.inner.innerTag == 'hi'


def test_optional_fields(schema, make_message):
    absent = make_message()
    decoded_absent = _round_trip(schema, absent).message
    assert decoded_absent.optSide is None
    assert decoded_absent.optString is None
    assert decoded_absent.optVal is None
    assert decoded_absent.optPrice is None
    assert decoded_absent.optQty is None
    assert decoded_absent.optDouble is None

    present = make_message(
        optVal=-100, optPrice=123, optQty=42, optDouble=1.5,
        optSide=schema.Side.Buy, optString='abcdef',
    )
    decoded = _round_trip(schema, present).message
    assert decoded.optVal == -100
    assert decoded.optPrice == 123
    assert decoded.optQty == 42
    assert decoded.optDouble == pytest.approx(1.5)
    assert decoded.optSide == schema.Side.Buy
    assert decoded.optString == 'abcdef'


def test_constant_fields(schema, make_message):
    decoded = _round_trip(schema, make_message()).message
    assert decoded.constEnum == schema.MessageType.ExecutionReport
    assert decoded.constStr == '1.0'
    assert decoded.constNum == 42

    # Constant fields are not transmitted on the wire: an explicit value
    # that agrees with the schema constant is fine, a conflicting one is
    # rejected rather than silently ignored.
    schema.encode(schema.AllTypesMessageMessage, make_message(constNum=42))
    with pytest.raises(ValueError):
        schema.encode(schema.AllTypesMessageMessage, make_message(constNum=7))


def test_entries_group_round_trip(schema, make_message):
    entry0 = schema.AllTypesMessageMessage_Entries(
        seq=1, amount=100_000, tag='ab',
        tflags=schema.Flags.Bit0 | schema.Flags.Bit2,
        ttype=schema.MessageType.NewOrder,
        tDec=schema.Decimal(mantissa=9_999, exponent=2),
        sub=[
            schema.AllTypesMessageMessage_Entries_Sub(subId=10, subVal=100),
            schema.AllTypesMessageMessage_Entries_Sub(subId=10, subVal=100),
        ],
        note='note!',
    )
    entry1 = schema.AllTypesMessageMessage_Entries(
        seq=2, amount=-1, tag='',
        tflags=schema.Flags(0),
        ttype=schema.MessageType.ExecutionReport,
        tDec=schema.Decimal(mantissa=0, exponent=-3),
        sub=[],
        note='n',
    )
    message = make_message(entries=[entry0, entry1])
    decoded = _round_trip(schema, message).message

    assert len(decoded.entries) == 2

    d0 = decoded.entries[0]
    assert d0.seq == 1
    assert d0.amount == 100_000
    assert d0.tag == 'ab'
    assert schema.Flags.Bit0 in d0.tflags
    assert schema.Flags.Bit2 in d0.tflags
    assert d0.ttype == schema.MessageType.NewOrder
    assert d0.tDec == schema.Decimal(mantissa=9_999, exponent=2)
    assert [(s.subId, s.subVal) for s in d0.sub] == [(10, 100), (10, 100)]
    assert d0.note == 'note!'

    d1 = decoded.entries[1]
    assert d1.seq == 2
    assert d1.amount == -1
    assert d1.tag == ''
    assert d1.ttype == schema.MessageType.ExecutionReport
    assert d1.tDec.exponent == -3
    assert d1.sub == []
    assert d1.note == 'n'


def test_buckets_group_round_trip(schema, make_message):
    buckets = [
        schema.AllTypesMessageMessage_Buckets(bucketId=1, weight=1.5),
        schema.AllTypesMessageMessage_Buckets(bucketId=2, weight=3.0),
    ]
    decoded = _round_trip(schema, make_message(buckets=buckets)).message

    assert len(decoded.buckets) == 2
    for i, bucket in enumerate(decoded.buckets, start=1):
        assert bucket.bucketId == i
        assert bucket.weight == pytest.approx(1.5 * i)


def test_blob_records_group_round_trip(schema, make_message):
    records = [
        schema.AllTypesMessageMessage_BlobRecords(recordId=77, label='EUR/USD', payload=[0xde, 0xad, 0xbe, 0xef]),
    ]
    decoded = _round_trip(schema, make_message(blobRecords=records)).message

    assert len(decoded.blobRecords) == 1
    record = decoded.blobRecords[0]
    assert record.recordId == 77
    assert record.label == 'EUR/USD'
    assert record.payload == [0xde, 0xad, 0xbe, 0xef]


def test_ticks_group_round_trip(schema, make_message):
    ticks = [
        schema.AllTypesMessageMessage_Ticks(tickValue=-1, tickTag=9),
        schema.AllTypesMessageMessage_Ticks(tickValue=-1, tickTag=9),
    ]
    decoded = _round_trip(schema, make_message(ticks=ticks)).message

    assert len(decoded.ticks) == 2
    for tick in decoded.ticks:
        assert tick.tickValue == -1
        assert tick.tickTag == 9


def test_variable_length_data_round_trip(schema, make_message):
    big_blob = list(range(300))
    message = make_message(
        traceId='trace-1',
        summary='spread summary',
        blob=[1, 2, 3, 4],
        bigBlob=[b & 0xFF for b in big_blob],
    )
    decoded = _round_trip(schema, message).message

    assert decoded.traceId == 'trace-1'
    assert decoded.summary == 'spread summary'
    assert decoded.blob == [1, 2, 3, 4]
    assert decoded.bigBlob == [b & 0xFF for b in big_blob]


def test_full_round_trip(schema, make_message):
    """Every field, every group (including the nested one) and every
    variable-length field populated at once - the Python equivalent of the
    C++ "full round trip sized via sbeComputeSize" test. The Python codec
    has no size to compute up front (the buffer grows on demand), so this
    just confirms nothing tramples anything else when everything is used
    together."""
    message = make_message(
        id=7, qty=9, price=-3, symbol='ABC',
        entries=[
            schema.AllTypesMessageMessage_Entries(
                seq=1, amount=0, tag='', tflags=schema.Flags(0),
                ttype=schema.MessageType.NewOrder,
                tDec=schema.Decimal(mantissa=0, exponent=0),
                sub=[schema.AllTypesMessageMessage_Entries_Sub(subId=10, subVal=0)],
                note='note!',
            ),
        ],
        buckets=[schema.AllTypesMessageMessage_Buckets(bucketId=1, weight=0.0)],
        blobRecords=[
            schema.AllTypesMessageMessage_BlobRecords(recordId=1, label='lbl', payload=[1, 2]),
        ],
        ticks=[
            schema.AllTypesMessageMessage_Ticks(tickValue=-1, tickTag=9),
            schema.AllTypesMessageMessage_Ticks(tickValue=-1, tickTag=9),
        ],
        traceId='tr', summary='sm', blob=[1, 2, 3, 4], bigBlob=[0] * 300,
    )
    decoded = _round_trip(schema, message).message

    assert decoded.id == 7
    assert decoded.qty == 9
    assert decoded.price == -3
    assert decoded.entries[0].sub[0].subId == 10
    assert decoded.entries[0].note == 'note!'
    assert decoded.buckets[0].bucketId == 1
    assert decoded.blobRecords[0].label == 'lbl'
    assert len(decoded.ticks) == 2
    assert decoded.traceId == 'tr'
    assert decoded.summary == 'sm'
    assert len(decoded.blob) == 4
    assert len(decoded.bigBlob) == 300


def test_empty_and_data_only_messages(schema):
    empty = schema.EmptyMessageMessage()
    buffer = schema.encode(schema.EmptyMessageMessage, empty)
    result = schema.decode(buffer)
    assert result.header.templateId == schema.EmptyMessageMessage.TEMPLATE_ID
    assert result.message == empty

    data_only = schema.DataOnlyMessageMessage(payload='hello')
    buffer = schema.encode(schema.DataOnlyMessageMessage, data_only)
    result = schema.decode(buffer)
    assert result.header.templateId == schema.DataOnlyMessageMessage.TEMPLATE_ID
    assert result.message.payload == 'hello'
