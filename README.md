# sbe-code-gen

Simple Binary Encoding codec generator for C++20 [WIP]

* spec https://github.com/FIXTradingCommunity/fix-simple-binary-encoding
* inspired by https://github.com/real-logic/simple-binary-encoding

## Sample usage

Generate C++ coder/decoder:

```sh
$ python3 -m app --schema=resources/b3-market-data-messages-1.3.1.xml --destination=$PWD/schema
```

Now encode message in c++ application (`main.cpp`):
```c++
#include <cstdlib>
#include <iostream>

#include "schema/Schema.h"

int main([[maybe_unused]] int argc, [[maybe_unused]] char *argv[]) {
  namespace sbe = b3::marketdata::umdf::sbe;

  try {
    char buffer[512];
    sbe::IncrementalRefresh_EmptyBook_9 msg;
    msg.wrapAndApplyHeader(buffer, 0, sizeof(buffer));
    msg.matchEventIndicator(
        sbe::MatchEventIndicator().lastTradeMsg(true).lastQuoteMsg(true));

    std::cout << "encoded length: " << msg.encodedLength() << '\n';

  } catch (std::exception const &e) {
    return EXIT_FAILURE;
  }
  return EXIT_SUCCESS;
}

```

Compilation:
```sh
g++ main.cpp -o main -std=c++2a
```
