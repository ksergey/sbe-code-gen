from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# One schema exercising every field kind: plain scalar (required and
# optional), enum (required and optional), set, composite (required and
# optional). Every field ref must carry the value type of its field as a
# `using ValueType` declaration; a composite ref inherits the composite class
# and reports exactly that class. Nullable fields (presence="optional") also
# carry `static constexpr NullValue` matching the schema's null value, while
# non-nullable fields must not have one.
SCHEMA_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<sbe:messageSchema xmlns:sbe="http://fixprotocol.io/2016/sbe"
                   description="field value type check" byteOrder="littleEndian"
                   package="fieldtype" id="7" version="0" semanticVersion="5.2">
    <types>
        <composite name="messageHeader">
            <type name="blockLength" primitiveType="uint16"/><type name="templateId" primitiveType="uint16"/>
            <type name="schemaId" primitiveType="uint16"/><type name="version" primitiveType="uint16"/>
        </composite>
        <enum name="Side" encodingType="uint8">
            <validValue name="Buy">1</validValue>
            <validValue name="Sell">2</validValue>
        </enum>
        <set name="Flags" encodingType="uint8">
            <choice name="Fast">1</choice>
            <choice name="Slow">2</choice>
        </set>
        <composite name="Px">
            <type name="mantissa" primitiveType="int64"/>
            <type name="exponent" primitiveType="int8" presence="constant">-8</type>
        </composite>
    </types>
    <sbe:message name="Order" id="1">
        <field id="1" name="quantity" type="uint64"/>
        <field id="2" name="stamp" type="uint32" presence="optional"/>
        <field id="3" name="side" type="Side"/>
        <field id="4" name="flags" type="Flags"/>
        <field id="5" name="price" type="Px"/>
        <field id="6" name="action" type="Side" presence="optional"/>
        <field id="7" name="askPrice" type="Px" presence="optional"/>
    </sbe:message>
</sbe:messageSchema>'''


@pytest.fixture(scope='module')
def generated(tmp_path_factory):
    import subprocess
    import sys
    tmp = tmp_path_factory.mktemp('fieldtype')
    (tmp / 'schema.xml').write_text(SCHEMA_XML)
    dest = tmp / 'codec'
    subprocess.run(
        [sys.executable, '-m', 'app', '--schema', str(tmp / 'schema.xml'),
         '--destination', str(dest), '--generator', 'cpp-split'],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return dest / 'schema.h'


def _ref_body(schema: Path, ref_name: str) -> str:
    text = schema.read_text()
    header = next(line for line in text.splitlines()
                  if line.strip().startswith(f'struct {ref_name} '))
    brace = text.index('{', text.index(f'struct {ref_name} ')) + 1
    depth = 1
    cursor = brace
    while depth:
        if text[cursor] == '{':
            depth += 1
        elif text[cursor] == '}':
            depth -= 1
        cursor += 1
    return header + text[brace:cursor]


def test_scalar_value_type(generated):
    body = _ref_body(generated, 'QuantityRef')
    assert 'using ValueType = std::uint64_t;' in body


def test_optional_scalar_value_type(generated):
    body = _ref_body(generated, 'StampRef')
    assert 'using ValueType = std::uint32_t;' in body


def test_enum_value_type(generated):
    body = _ref_body(generated, 'SideRef')
    assert 'using ValueType = Side;' in body


def test_set_value_type(generated):
    body = _ref_body(generated, 'FlagsRef')
    assert 'using ValueType = Flags;' in body


def test_composite_value_type_names_the_embedded_composite(generated):
    body = _ref_body(generated, 'PriceRef')
    assert body.strip().startswith('struct PriceRef : public Px')
    assert 'using ValueType = Px;' in body
    assert body.index('using ValueType = Px;') < body.index('std::byte* bufferPtr')


def test_message_header_refs_carry_value_types_without_field_wrappers(generated):
    body = _ref_body(generated, 'BlockLengthRef')
    assert 'using ValueType = std::uint16_t;' in body


def test_optional_scalar_null_value(generated):
    body = _ref_body(generated, 'StampRef')
    assert 'static constexpr ValueType NullValue = std::numeric_limits<std::uint32_t>::max();' in body


def test_required_scalar_has_no_null_value(generated):
    body = _ref_body(generated, 'QuantityRef')
    assert 'NullValue' not in body


def test_optional_enum_null_value(generated):
    body = _ref_body(generated, 'ActionRef')
    assert 'static constexpr ValueType NullValue = Side::SBE_NULL;' in body


def test_required_enum_has_no_null_value(generated):
    body = _ref_body(generated, 'SideRef')
    assert 'NullValue' not in body


def test_optional_composite_null_value(generated):
    body = _ref_body(generated, 'AskPriceRef')
    assert body.strip().startswith('struct AskPriceRef : public Px')
    assert 'static constexpr ValueType NullValue{};' in body


def test_required_composite_has_no_null_value(generated):
    body = _ref_body(generated, 'PriceRef')
    assert 'NullValue' not in body


def test_set_has_no_null_value(generated):
    body = _ref_body(generated, 'FlagsRef')
    assert 'NullValue' not in body


def test_message_header_refs_have_no_null_value(generated):
    body = _ref_body(generated, 'BlockLengthRef')
    assert 'NullValue' not in body
