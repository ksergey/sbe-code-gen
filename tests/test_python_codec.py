import importlib.util
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
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='session')
def generated_schema(tmp_path_factory):
    dest = tmp_path_factory.mktemp('codec') / 'python'
    subprocess.run(
        [sys.executable, '-m', 'app',
         '--schema', str(SPOT_SCHEMA),
         '--destination', str(dest),
         '--generator', 'python'],
        cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return _load_module(dest / 'schema.py', 'generated_schema')


def test_simple_message_round_trip(generated_schema):
    data = {
        'priceExponent': -8,
        'minPrice': 100000000,
        'maxPrice': 200000000,
        'tickSize': 100,
    }
    buffer = generated_schema.encode(generated_schema.PriceFilterMessage, data)
    codec_cls, decoded = generated_schema.decode(buffer)
    assert codec_cls is generated_schema.PriceFilterMessage
    assert decoded['filterType'] == generated_schema.FilterType.PriceFilter
    assert decoded['priceExponent'] == data['priceExponent']
    assert decoded['minPrice'] == data['minPrice']
    assert decoded['maxPrice'] == data['maxPrice']
    assert decoded['tickSize'] == data['tickSize']


def test_repeating_group_round_trip(generated_schema):
    data = {
        'priceExponent': -8,
        'qtyExponent': -6,
        'trades': [
            {'id': 1, 'price': 100, 'qty': 5, 'quoteQty': 500,
             'time': 1700000000000, 'isBuyerMaker': generated_schema.BoolEnum.True_,
             'isBestMatch': generated_schema.BoolEnum.False_},
            {'id': 2, 'price': 101, 'qty': 6, 'quoteQty': 606,
             'time': 1700000000001, 'isBuyerMaker': generated_schema.BoolEnum.False_,
             'isBestMatch': generated_schema.BoolEnum.True_},
        ],
    }
    buffer = generated_schema.encode(generated_schema.TradesResponseMessage, data)
    codec_cls, decoded = generated_schema.decode(buffer)
    assert codec_cls is generated_schema.TradesResponseMessage
    assert decoded['priceExponent'] == data['priceExponent']
    assert decoded['qtyExponent'] == data['qtyExponent']
    assert decoded['trades'] == data['trades']