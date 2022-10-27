# sbe-code-gen

Simple Binary Encoding codec generator for C++20 [WIP]

* spec https://github.com/FIXTradingCommunity/fix-simple-binary-encoding
* inspired by https://github.com/real-logic/simple-binary-encoding

# Sample usage

## Generate C++ coder/decoder

```sh
$ python3 -m app --schema=resources/b3-market-data-messages-1.3.1.xml --destination=$PWD/schema --generator=cpp
```

Now encode message in c++ application (`main.cpp`):
```c++
#include <cstdlib>
#include <iostream>

#include "schema/schema.h"

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

## Generate C++ coder/decoder (new)

```sh
$ python3 -m app --schema=resources/b3-market-data-messages-1.3.1.xml --destination=$PWD/schema --generator=cppng
```

Now encode message in c++ application (`main.cpp`):
```c++
#include <cstdlib>
#include <iostream>
#include <utility>

#include "schema/schema.h"

int main([[maybe_unused]] int argc, [[maybe_unused]] char *argv[]) {
  using namespace b3::marketdata::umdf::sbe;

  try {
    char buffer[512];

    auto message = IncrementalRefresh_EmptyBook_9().wrapAndApplyHeader(buffer, 0, sizeof(buffer));
    message["securityID"_name].value(999);
    // or
    message["securityID"_name].value(nullptr);
    // or
    message["securityID"_name] = 333;
    // or
    message["securityID"_name] = nullptr;
    // or
    message[idx<3>] = 555;
    // or
    message[3_idx] = 444;
    // or... you know
    message["matchEventIndicator"_name] = MatchEventIndicator().clear().lastTradeMsg(true).lastQuoteMsg(true);

    auto print = []<typename F>(F const& field) {
      using ValueT = decltype(field.value());
      if (field.present()) {
        if constexpr (requires { field.value().raw(); }) {
          std::cout << "\"" << field.name() << "\": " << std::size_t(field.value().raw()) << '\n';
        } else {
          std::cout << "\"" << field.name() << "\": " << field.value() << '\n';
        }
      } else {
        std::cout << "\"" << field.name() << "\": N/A\n";
      }
    };

    auto printMsg = [&]<typename Msg, std::size_t... I>(Msg const& msg, std::index_sequence<I...>) {
      (print(msg[idx<I>]), ...);
    };

    printMsg(message, std::make_index_sequence<message.fieldsCount()>());

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

# TODO

- [ ] tests
- [ ] ci integration
- [ ] cmake integration
- [ ] rust support?
- [ ] python support?
- [x] (cppng) from/to json serialization ([impl](example/example_json.cpp))
- [ ] (cppng) set/get fixed-length strings as variable length string (trim till '\0')
- [ ] tests
