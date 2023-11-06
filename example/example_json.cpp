#include <functional>
#include <utility>

#include <fmt/format.h>
#include <nlohmann/json.hpp>

#include "schema.h"

using namespace b3::marketdata::umdf::sbe;

class JsonSerializer {
private:
  nlohmann::json root_;

public:
  using json = nlohmann::json;

  JsonSerializer() = default;

  [[nodiscard]] json result() {
    return root_;
  }

  template <typename Entry>
  JsonSerializer& operator()(Entry entry) {
    root_ = json::object();
    root_["_name"] = entry.name();
    root_["_id"] = entry.id();

    std::invoke(
        [&]<std::size_t... I>(std::index_sequence<I...>) {
          ((*this)(entry[idx<I>], root_), ...);
        },
        std::make_index_sequence<Entry::fieldsCount()>());

    return *this;
  }

  template <typename Entry>
  JsonSerializer& operator()(Entry entry, json& node) {
    if constexpr (Aggregate<Entry>) {
      auto child = json::object();

      std::invoke(
          [&]<std::size_t... I>(std::index_sequence<I...>) {
            ((*this)(entry[idx<I>], child), ...);
          },
          std::make_index_sequence<Entry::fieldsCount()>());

      node[entry.name()] = child;

    } else if constexpr (Sequence<Entry>) {
      auto child = json::array();

      while (entry.hasNext()) {
        entry.next();

        auto element = json::object();

        std::invoke(
            [&]<std::size_t... I>(std::index_sequence<I...>) {
              ((*this)(entry[idx<I>], element), ...);
            },
            std::make_index_sequence<Entry::fieldsCount()>());

        child.push_back(element);
      }

      node[entry.name()] = child;
    } else {
      using ValueT = typename Entry::value_type;

      if constexpr (Enum<ValueT>) {
        node[entry.name()] = ValueT::toString(entry.value());
      } else if constexpr (Set<ValueT>) {
        node[entry.name()] = entry.value().raw();
      } else {
        node[entry.name()] = entry.value();
      }
    }

    return *this;
  }
};

class JsonParser {
private:
  nlohmann::json input_;

public:
  using json = nlohmann::json;

  JsonParser(nlohmann::json input) : input_(input) {}

  JsonParser(std::string_view input) : JsonParser(json::parse(input)) {}

  template <typename Entry>
  Entry parse(char* buffer, std::size_t size) {
    auto result = Entry(buffer, size);

    std::invoke(
        [&]<std::size_t... I>(std::index_sequence<I...>) {
          (this->process(result[idx<I>], input_), ...);
        },
        std::make_index_sequence<Entry::fieldsCount()>());

    return result;
  }

  template <typename Entry>
  void operator()(Entry entry, json const& node) {
    if constexpr (Aggregate<Entry>) {
      std::invoke(
          [&]<std::size_t... I>(std::index_sequence<I...>) {
            (this->process(entry[idx<I>], node), ...);
          },
          std::make_index_sequence<Entry::fieldsCount()>());
    } else if constexpr (Sequence<Entry>) {
      entry.reset(node.size());

      for (auto const& child : node) {
        entry.next();

        std::invoke(
            [&]<std::size_t... I>(std::index_sequence<I...>) {
              (this->process(entry[idx<I>], child), ...);
            },
            std::make_index_sequence<Entry::fieldsCount()>());
      }
    } else {
      using ValueT = typename Entry::value_type;

      if constexpr (requires { entry.value(std::decay_t<ValueT>()); }) {
        if constexpr (requires { entry.value(nullptr); }) {
          if (node.is_null()) {
            entry.value(nullptr);
            return;
          }
        }

        if constexpr (Enum<ValueT>) {
          entry.value(ValueT::fromString(node.template get<std::string_view>()));
        } else if constexpr (Set<ValueT>) {
          entry.value(ValueT(node.template get<typename ValueT::underlying_type>()));
        } else {
          entry.value(node.template get<ValueT>());
        }
      }
    }
  }

private:
  template <class Entry>
  void process(Entry entry, json const& node) {
    auto const found = node.find(entry.name());
    if (found != node.end()) {
      (*this)(entry, *found);
    } else {
      (*this)(entry, nullptr);
    }
  }
};

void jsonSerialize0() {
  char buffer[512];

  auto message = IncrementalRefresh_EmptyBook_9::wrapAndApplyHeader(buffer, 0, sizeof(buffer));
  message["securityID"_name] = 991;
  message["matchEventIndicator"_name] = MatchEventIndicator().clear().lastTradeMsg(true).lastQuoteMsg(true);

  auto node = JsonSerializer()(message).result();
  fmt::print(stdout, "{}\n", node.dump(2));
}

void jsonSerialize1() {
  char buffer[512];

  auto message = SnapshotFullRefresh_Orders_MBO_71(buffer, sizeof(buffer));
  message["securityID"_name].value(5);

  auto group = message["noMDEntries"_name];
  group.reset(1);

  group.next();
  group["mDEntryTimestamp"_name]["time"_name].value(1666875592000000000);
  group["mDInsertTimestamp"_name]["time"_name].value(1666875592000000000);
  group["orderID"_name].value(91998);
  group["mDEntryPx"_name]["mantissa"_name].value(3313388);
  group["mDEntrySize"_name].value(5);
  group["mDEntryPositionNo"_name].value(10);
  group["enteringFirm"_name].value(7767);
  group["mDEntryType"_name].value(MDEntryType::OFFER);
  group["mDStreamID"_name].value(MDStreamID::ELECTRONIC);

  auto node = JsonSerializer()(message.sbeRewind()).result();
  fmt::print(stdout, "{}\n", node.dump(2));
}

void jsonParseAndSerialize0() {
  using namespace std::string_view_literals;

  char buffer[512];

  constexpr auto input = R"(
{
  "securityID": 5551,
  "noMDEntries": []
}
  )"sv;

  auto message = JsonParser(input).parse<SnapshotFullRefresh_Orders_MBO_71>(buffer, sizeof(buffer));

  fmt::print(stdout, "{}\n", JsonSerializer()(message.sbeRewind()).result().dump(4));
}

void jsonParseAndSerialize1() {
  using namespace std::string_view_literals;

  char buffer[512];

  constexpr auto input = R"(
{
  "securityID": 995,
  "noMDEntries": [
    {
      "enteringFirm": 7870,
      "mDEntryPositionNo": 2,
      "mDEntryPx": {
        "exponent": -4,
        "mantissa": 99553400
      },
      "mDEntrySize": 0,
      "mDEntryTimestamp": {
        "time": 1666875592000000000,
        "unit": 9
      },
      "mDEntryType": "",
      "mDInsertTimestamp": {
        "time": 1666875592000000000,
        "unit": 9
      },
      "mDStreamID": "INDEX",
      "orderID": 111111
    }
  ]
}
  )"sv;

  auto message = JsonParser(input).parse<SnapshotFullRefresh_Orders_MBO_71>(buffer, sizeof(buffer));

  fmt::print(stdout, "{}\n", JsonSerializer()(message.sbeRewind()).result().dump(4));
}

int main([[maybe_unused]] int argc, [[maybe_unused]] char* argv[]) {
  try {
    fmt::print("---\n");
    jsonSerialize0();
    fmt::print("---\n");
    jsonSerialize1();
    fmt::print("---\n");
    jsonParseAndSerialize0();
    fmt::print("---\n");
    jsonParseAndSerialize1();
  } catch (std::exception const& e) {
    fmt::print(stderr, "ERROR: {}\n", e.what());
    return EXIT_FAILURE;
  }
  return EXIT_SUCCESS;
}
