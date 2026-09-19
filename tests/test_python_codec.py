import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SPOT_SCHEMA = REPO_ROOT / 'resources' / 'spot_3_1.xml'

pytestmark = pytest.mark.usefixtures('generated_schema')


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses needs this to resolve ClassVar annotations
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='session')
def generated_schema(tmp_path_factory):
    # When run through CTest, tests/CMakeLists.txt points this at
    # CMAKE_CURRENT_BINARY_DIR so the generated schema.py lands inside the
    # build tree (inspectable, cleaned up with the rest of build/) instead of
    # an ephemeral pytest tmp dir. Running pytest directly (as CI's
    # standalone python job and local `pytest tests/test_python_codec.py`
    # both do) has no such build dir, so fall back to tmp_path_factory.
    dest_root = os.environ.get('SBE_CODE_GEN_PYTHON_CODEC_DIR')
    if dest_root:
        dest = Path(dest_root) / 'python'
    else:
        dest = tmp_path_factory.mktemp('codec') / 'python'
    subprocess.run(
        [sys.executable, '-m', 'app',
         '--schema', str(SPOT_SCHEMA),
         '--destination', str(dest),
         '--generator', 'python'],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return _load_module(dest / 'schema.py', 'generated_schema')


def _generate_from_xml(tmp_path, xml_text: str):
    schema_path = tmp_path / 'schema.xml'
    schema_path.write_text(xml_text)
    dest = tmp_path / 'python'
    subprocess.run(
        [sys.executable, '-m', 'app',
         '--schema', str(schema_path),
         '--destination', str(dest),
         '--generator', 'python'],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return _load_module(dest / 'schema.py', f'generated_schema_{tmp_path.name}')


def test_field_name_matching_its_own_type_name(tmp_path):
    """Regression test: a <field> named exactly like its own enum/set type
    (a common SBE convention, e.g. name="Side" type="Side") used to raise
    UnboundLocalError on unpack, because the unpack statement's local
    variable had the same name as the class it referenced on its own
    right-hand side."""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<sbe:messageSchema xmlns:sbe="http://fixprotocol.io/2016/sbe" description="name collision check"
                   byteOrder="littleEndian" package="namecheck" id="1" version="0" semanticVersion="5.2">
    <types>
        <composite name="messageHeader">
            <type name="blockLength" primitiveType="uint16"/><type name="templateId" primitiveType="uint16"/>
            <type name="schemaId" primitiveType="uint16"/><type name="version" primitiveType="uint16"/>
        </composite>
        <enum name="Side" encodingType="uint8">
            <validValue name="Buy">1</validValue>
            <validValue name="Sell">2</validValue>
        </enum>
    </types>
    <sbe:message name="Order" id="1">
        <field id="1" name="Side" type="Side"/>
    </sbe:message>
</sbe:messageSchema>'''
    schema = _generate_from_xml(tmp_path, xml)
    message = schema.OrderMessage(Side=schema.Side.Buy)
    buffer = schema.encode(schema.OrderMessage, message)
    result = schema.decode(buffer)
    assert result.message == message


def test_optional_composite_with_optional_first_member(tmp_path):
    """Regression test: a composite whose first member is itself
    presence="optional" (real-world example: SBE's PriceOffset-style
    types). The outer field's "is the whole composite null" check used to
    compare the *already-decoded* first member (which can legitimately be
    None on its own) against the member's raw null value - None never
    equals a number, so an encoded None silently came back as a non-None
    object instead."""
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<sbe:messageSchema xmlns:sbe="http://fixprotocol.io/2016/sbe" description="nested-optional composite check"
                   byteOrder="littleEndian" package="nestedopt" id="1" version="0" semanticVersion="5.2">
    <types>
        <composite name="messageHeader">
            <type name="blockLength" primitiveType="uint16"/><type name="templateId" primitiveType="uint16"/>
            <type name="schemaId" primitiveType="uint16"/><type name="version" primitiveType="uint16"/>
        </composite>
        <composite name="PriceOffsetOptional">
            <type name="mantissa" primitiveType="int64" presence="optional"/>
            <type name="exponent" primitiveType="int8" presence="constant">-4</type>
        </composite>
    </types>
    <sbe:message name="Quote" id="1">
        <field id="1" name="offset" type="PriceOffsetOptional" presence="optional"/>
    </sbe:message>
</sbe:messageSchema>'''
    schema = _generate_from_xml(tmp_path, xml)

    none_message = schema.QuoteMessage(offset=None)
    result = schema.decode(schema.encode(schema.QuoteMessage, none_message))
    assert result.message.offset is None

    present_message = schema.QuoteMessage(offset=schema.PriceOffsetOptional(mantissa=12345))
    result = schema.decode(schema.encode(schema.QuoteMessage, present_message))
    assert result.message == present_message


def test_simple_message_round_trip(generated_schema):
    message = generated_schema.PriceFilterMessage(
        priceExponent=-8,
        minPrice=100000000,
        maxPrice=200000000,
        tickSize=100,
    )
    buffer = generated_schema.encode(generated_schema.PriceFilterMessage, message)
    result = generated_schema.decode(buffer)
    assert result.header.templateId == generated_schema.PriceFilterMessage.TEMPLATE_ID
    assert result.message == message
    assert result.message.filterType == generated_schema.FilterType.PriceFilter


def test_repeating_group_round_trip(generated_schema):
    trades = [
        generated_schema.TradesResponseMessage_Trades(
            id=1, price=100, qty=5, quoteQty=500, time=1700000000000,
            isBuyerMaker=generated_schema.BoolEnum.True_, isBestMatch=generated_schema.BoolEnum.False_),
        generated_schema.TradesResponseMessage_Trades(
            id=2, price=101, qty=6, quoteQty=606, time=1700000000001,
            isBuyerMaker=generated_schema.BoolEnum.False_, isBestMatch=generated_schema.BoolEnum.True_),
    ]
    message = generated_schema.TradesResponseMessage(priceExponent=-8, qtyExponent=-6, trades=trades)
    buffer = generated_schema.encode(generated_schema.TradesResponseMessage, message)
    result = generated_schema.decode(buffer)
    assert result.header.templateId == generated_schema.TradesResponseMessage.TEMPLATE_ID
    assert result.message == message