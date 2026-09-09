[<img src="https://img.shields.io/github/license/ksergey/sbe-code-gen">](https://opensource.org/license/gpl-3-0)
[<img src="https://img.shields.io/github/actions/workflow/status/ksergey/sbe-code-gen/on_push.yml?logo=linux">](https://github.com/ksergey/sbe-code-gen/actions/workflows/on_push.yml)
[<img src="https://img.shields.io/badge/language-python3-yellow">](https://en.wikipedia.org/wiki/Python_(programming_language))
[<img src="https://img.shields.io/badge/language-C%2B%2B23-red">](https://en.wikipedia.org/wiki/C%2B%2B23)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ksergey/sbe-code-gen)

# sbe-code-gen (WIP)

A code generator that produces high-performance binary codecs from [Simple Binary Encoding](https://github.com/FIXTradingCommunity/fix-simple-binary-encoding) (SBE) XML schemas.
Given a schema, the generator emits codecs that encode and decode binary messages according to the SBE specification.

* spec https://github.com/FIXTradingCommunity/fix-simple-binary-encoding
* inspired by https://github.com/real-logic/simple-binary-encoding

## Supported generators

| Generator | Output | Target |
|-----------|--------|--------|
| `cpp-min` | `schema.h` | Single-header C++23 codec |
| `python`  | `schema.py` | Python codec with zero runtime dependencies (uses only the standard library) |

## Requirements

* Python 3.10+ and `pip install -r requirements.txt` (Jinja2, pytest).
* For the `cpp-min` codec: a C++23 compiler and CMake 3.19+.

## Code generation (CLI)

```console
$ python -m app --schema=resources/spot_3_1.xml --destination=out/cpp --generator=cpp-min
$ python -m app --schema=resources/spot_3_1.xml --destination=out/py  --generator=python
```

`--package=<name>` overrides the `package` attribute of the schema (it defines the C++ namespace / Python module structure).

## CMake integration

`SbeMakeCodec()` generates a codec from an XML schema and exposes it as an `INTERFACE` library:

```cmake
include(cmake/SbeMakeCodec.cmake)

SbeMakeCodec(spot_codec
    SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/resources/spot_3_1.xml
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/sbe
    GENERATOR cpp-min       # cpp-min | python
    # INCLUDE_BASE spot_sbe # header is placed at OUTPUT/INCLUDE_BASE/schema.h
    # PACKAGE spot_sbe      # override the schema package attribute
)

target_link_libraries(my_app PRIVATE spot_codec)
```

Without `INCLUDE_BASE`, the generated `schema.h` is written to `OUTPUT/schema.h` and included as `"schema.h"`; with `INCLUDE_BASE`, it is included as `<spot_sbe/schema.h>`. The python virtualenv used by the generator is created once per top-level project (under `${PROJECT_BINARY_DIR}/venv`).

## C++ codec usage

All C++ API is `consteval`/`constexpr`-friendly and is generated into a single header.

### Encode

```cpp
#include "schema.h"

#include <array>
#include <cstddef>

int main() {
    std::array<std::byte, 128> buffer{};

    auto msg = spot_sbe::PriceFilter::wrapAndApplyHeader(buffer);
    msg.get<"priceExponent">().value(-8);
    msg.get<"minPrice">().value(100'000'000);
    msg.get<"maxPrice">().value(200'000'000);
    msg.get<"tickSize">().value(100);

    // total message size in bytes (message header + body)
    auto totalBytes = msg.position();
}
```

### Decode

```cpp
std::array<std::byte, 128> buffer{}; // payload received from the wire

auto header = spot_sbe::MessageHeader{buffer.data()};
if (header.get<"templateId">().value() == spot_sbe::PriceFilter::sbeTemplateId()) {
    auto msg = spot_sbe::PriceFilter{buffer,
                                     header.sbeEncodedLength(),
                                     header.get<"blockLength">().value(),
                                     header.get<"version">().value()};
    auto minPrice = msg.get<"minPrice">().value();
    // ...
}
```

### Repeating groups

```cpp
std::array<std::byte, 1024> buffer{};

auto msg = spot_sbe::KlinesResponse::wrapAndApplyHeader(buffer);
msg.get<"priceExponent">().value(-8);
msg.get<"qtyExponent">().value(-6);

auto klines = msg.get<"klines">();
klines.reset(2); // number of group entries

while (klines.hasNext()) {
    auto& entry = klines.next();
    entry.get<"openTime">().value(1'700'000'000'000);
    entry.get<"openPrice">().value(100);
    entry.get<"closePrice">().value(101);
    // ... remaining entry fields
}

auto totalBytes = msg.position();
```

Decoding a group is symmetric:

```cpp
auto klines = msg.get<"klines">();
while (klines.hasNext()) {
    auto& entry = klines.next();
    auto openTime = entry.get<"openTime">().value();
}
```

### Buffer size estimation

`sbeComputeSize()` returns the required payload size (excluding the message header) for a given number of group entries:

```cpp
auto required = spot_sbe::KlinesResponse::sbeComputeSize({4}); // 4 kline entries
```

## Python codec usage

The generated `schema.py` exposes a `Schema` class plus module-level `encode()`/`decode()` helpers.

### Encode

```python
import sys
sys.path.append('out/py')
import schema

data = {
    'priceExponent': -8,
    'minPrice': 100_000_000,
    'maxPrice': 200_000_000,
    'tickSize': 100,
}
buffer = schema.encode(schema.PriceFilterMessage, data)
```

### Decode

```python
codec_cls, decoded = schema.decode(buffer)
assert codec_cls is schema.PriceFilterMessage
print(decoded['minPrice'])  # 100000000
```

### Repeating groups

```python
data = {
    'priceExponent': -8,
    'qtyExponent': -6,
    'trades': [
        {'id': 1, 'price': 100, 'qty': 5, 'quoteQty': 500, 'time': 1_700_000_000_000,
         'isBuyerMaker': schema.BoolEnum.True_, 'isBestMatch': schema.BoolEnum.False_},
        {'id': 2, 'price': 101, 'qty': 6, 'quoteQty': 606, 'time': 1_700_000_000_001,
         'isBuyerMaker': schema.BoolEnum.False_, 'isBestMatch': schema.BoolEnum.True_},
    ],
}

buffer = schema.encode(schema.TradesResponseMessage, data)
codec_cls, decoded = schema.decode(buffer)
assert len(decoded['trades']) == 2
```

### Custom buffer and template id

```python
ctx = schema.CodecContext(bytearray(256))
schema.Schema.encode(ctx, data, cls=schema.TradesResponseMessage)  # or template_id=201
wire_size = ctx.offset

ctx.offset = 0
codec_cls, decoded = schema.Schema.decode(ctx)
```

## Running tests

```console
$ pytest -q tests/test_python_codec.py   # python codec round-trip tests
$ ctest --test-dir build --output-on-failure  # C++ codec tests
```