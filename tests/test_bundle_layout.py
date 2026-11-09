import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Bundle fixtures: two minimal schemas sharing common_types.xml via xi:include,
# so the bundle constraints (same header type/version/byte order, unique
# fragment type names) are exercised along with the shared-fragment identity.
COMMON_TYPES_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<types xmlns:sbe="http://fixprotocol.io/2016/sbe">
  <composite name="messageHeader">
    <type name="blockLength" primitiveType="uint16"/>
    <type name="templateId" primitiveType="uint16"/>
    <type name="schemaId" primitiveType="uint16"/>
    <type name="version" primitiveType="uint16"/>
  </composite>
  <enum name="Side" encodingType="uint8">
    <validValue name="Buy">1</validValue>
    <validValue name="Sell">2</validValue>
  </enum>
</types>'''

SCHEMA_HEADER = '''<?xml version="1.0" encoding="UTF-8"?>
<sbe:messageSchema xmlns:sbe="http://fixprotocol.io/2016/sbe"
                   xmlns:xi="http://www.w3.org/2001/XInclude"
                   description="bundle-layout fixture" byteOrder="littleEndian"
                   package="{package}" id="{id}" version="0" semanticVersion="5.2">
  <xi:include href="common_types.xml"/>
  <types>
    <composite name="Px">
      <type name="mantissa" primitiveType="int64"/>
      <type name="exponent" primitiveType="int8" presence="constant">-8</type>
    </composite>
  </types>
'''
SCHEMA_FOOTER = '</sbe:messageSchema>'

ORDER_MESSAGE = '''  <sbe:message name="Order" id="1">
    <field id="1" name="quantity" type="uint64"/>
    <field id="2" name="price" type="Px"/>
  </sbe:message>
'''
TRADE_MESSAGE = '''  <sbe:message name="Trade" id="2">
    <field id="3" name="tradePrice" type="Px"/>
  </sbe:message>
'''
HEARTBEAT_MESSAGE = '''  <sbe:message name="Heartbeat" id="1">
    <field id="4" name="sequence" type="uint32"/>
  </sbe:message>
'''

BANNER = '// Generated simple binary encoding message codec'
PAST_TIME_NS = int((time.time() - 10000) * 1e9)


@pytest.fixture
def bundle(tmp_path):
    def write(schemas: dict[str, list[str]]) -> None:
        (tmp_path / 'common_types.xml').write_text(COMMON_TYPES_XML)
        for schema_id, (package, messages) in enumerate(schemas.items(), start=1):
            body = ''.join(SCHEMA_HEADER.format(package=package, id=schema_id) + ''.join(messages))
            (tmp_path / f'{package}_schema.xml').write_text(body + SCHEMA_FOOTER)

    def generate(schemas: dict[str, list[str]]) -> None:
        write(schemas)
        args = [sys.executable, '-m', 'app', '--destination', str(tmp_path / 'dest'),
                '--generator', 'cpp-split', '--bundle']
        for package in schemas:
            args += ['--schema', str(tmp_path / f'{package}_schema.xml')]
        subprocess.run(args, cwd=REPO_ROOT, check=True, capture_output=True, text=True)

    return generate


def _mtimes(destination: Path) -> dict[str, int]:
    return {p.relative_to(destination).as_posix(): p.stat().st_mtime_ns
            for p in destination.rglob('*') if p.is_file()}


def _touch_all_back_in_time(destination: Path) -> None:
    for path in destination.rglob('*'):
        if path.is_file():
            os.utime(path, ns=(PAST_TIME_NS, PAST_TIME_NS))


def test_bundle_layout_and_umbrella_schema(bundle, tmp_path):
    bundle({'md': [ORDER_MESSAGE], 'svc': [HEARTBEAT_MESSAGE]})
    dest = tmp_path / 'dest'

    assert sorted(p.relative_to(dest).as_posix() for p in dest.rglob('*') if p.is_file()) == [
        'common_types.h',
        'md/Order.h',
        'md/schema.h',
        'md/types.h',
        'support.h',
        'svc/Heartbeat.h',
        'svc/schema.h',
        'svc/types.h',
    ]

    umbrella = (dest / 'md' / 'schema.h').read_text()
    assert '#include "Order.h"' in umbrella
    assert 'using Messages = TypeList<' in umbrella and 'Order' in umbrella

    order = (dest / 'md' / 'Order.h').read_text()
    assert order.startswith(BANNER) and '#include "types.h"' in order and 'class Order' in order

    types = (dest / 'md' / 'types.h').read_text()
    assert types.startswith(BANNER) and 'class Px' in types and '#include "common_types.h"' in types


def test_regeneration_preserves_unchanged_files(bundle, tmp_path):
    bundle({'md': [ORDER_MESSAGE], 'svc': [HEARTBEAT_MESSAGE]})
    dest = tmp_path / 'dest'
    _touch_all_back_in_time(dest)

    bundle({'md': [ORDER_MESSAGE], 'svc': [HEARTBEAT_MESSAGE]})

    # every file byte-identical, so write-if-different left every mtime alone
    for relative, mtime in _mtimes(dest).items():
        assert mtime == PAST_TIME_NS, f'rewritten: {relative}'


def test_regeneration_prunes_removed_outputs_spares_foreign_files(bundle, tmp_path):
    bundle({'md': [ORDER_MESSAGE], 'svc': [HEARTBEAT_MESSAGE]})
    dest = tmp_path / 'dest'
    foreign = dest / 'notes.txt'
    foreign.write_text('not a generated file at all\n')
    foreign_header = dest / 'common' / 'include.h'
    foreign_header.parent.mkdir()
    foreign_header.write_text('#pragma once // no provenance banner: foreign\n')
    stale = dest / 'md' / 'Stale.h'
    stale.write_text(BANNER + '\n// a file the generator no longer plans to write\n')
    nested_stale = dest / 'legacy' / 'Gone.h'
    nested_stale.parent.mkdir()
    nested_stale.write_text(BANNER + '\n')
    _touch_all_back_in_time(dest)

    bundle({'md': [ORDER_MESSAGE], 'svc': [HEARTBEAT_MESSAGE]})

    assert not stale.exists()
    assert not nested_stale.parent.exists(), 'empty directory left by pruning'
    assert foreign.exists() and foreign.read_text() == 'not a generated file at all\n'
    assert foreign_header.exists()
    for relative, mtime in _mtimes(dest).items():
        assert mtime == PAST_TIME_NS, f'rewritten: {relative}'


def test_message_addition_rewrites_only_affected_files(bundle, tmp_path):
    bundle({'md': [ORDER_MESSAGE], 'svc': [HEARTBEAT_MESSAGE]})
    dest = tmp_path / 'dest'
    _touch_all_back_in_time(dest)

    bundle({'md': [ORDER_MESSAGE, TRADE_MESSAGE], 'svc': [HEARTBEAT_MESSAGE]})

    fresh = {relative for relative, mtime in _mtimes(dest).items() if mtime != PAST_TIME_NS}
    assert fresh == {'md/Trade.h', 'md/schema.h'}
    assert (dest / 'md' / 'Trade.h').read_text().startswith(BANNER) and 'class Trade' in (dest / 'md' / 'Trade.h').read_text()
    umbrella = (dest / 'md' / 'schema.h').read_text()
    assert 'TypeList<' in umbrella and 'Order,' in umbrella and 'Trade' in umbrella

    # and back: removing the message prunes its header, the rest stays cold
    _touch_all_back_in_time(dest)
    bundle({'md': [ORDER_MESSAGE], 'svc': [HEARTBEAT_MESSAGE]})

    assert not (dest / 'md' / 'Trade.h').exists()
    fresh = {relative for relative, mtime in _mtimes(dest).items() if mtime != PAST_TIME_NS}
    assert fresh == {'md/schema.h'}
