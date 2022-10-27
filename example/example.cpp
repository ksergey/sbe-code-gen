#include <functional>
#include <utility>

#include <fmt/format.h>

#include "schema.h"

using namespace b3::marketdata::umdf::sbe;

template<typename Entry>
void print(Entry entry, std::size_t pad = 0) {
  if constexpr (isAggregate<Entry>) {
    std::invoke(
        [&]<std::size_t... I>(std::index_sequence<I...>) { (print(entry[idx<I>], pad + 2), ...); },
        std::make_index_sequence<Entry::fieldsCount()>());
  } else if constexpr (isSequence<Entry>) {
    while (entry.hasNext()) {
      entry.next();

      std::invoke(
          [&]<std::size_t... I>(std::index_sequence<I...>) { (print(entry[idx<I>], pad + 2), ...); },
          std::make_index_sequence<Entry::fieldsCount()>());
    }
  } else {
    using ValueT = typename Entry::value_type;

    if constexpr (isTypeEnum<ValueT>) {
      fmt::print("{:{}} \"{}\" = \"{}\"\n", ' ', pad, entry.name(), ValueT::toString(entry.value()));
    } else if constexpr (isTypeSet<ValueT>) {
      fmt::print("{:{}} \"{}\" = {:#04x}\n", ' ', pad, entry.name(), entry.value().raw());
    } else if constexpr (std::is_same_v<ValueT, std::string_view>) {
      fmt::print("{:{}} \"{}\" = \"{}\"\n", ' ', pad, entry.name(), entry.value());
    } else {
      fmt::print("{:{}} \"{}\" = {}\n", ' ', pad, entry.name(), entry.value());
    }
  }
}

int main([[maybe_unused]] int argc, [[maybe_unused]] char* argv[]) {
  try {
    char buffer[512];

    auto message = IncrementalRefresh_EmptyBook_9().wrapAndApplyHeader(buffer, 0, sizeof(buffer));
    message["securityID"_name] = 991;
    message["matchEventIndicator"_name] = MatchEventIndicator().clear().lastTradeMsg(true).lastQuoteMsg(true);

    print(message);
  } catch (std::exception const& e) {
    fmt::print(stderr, "ERROR: {}\n", e.what());
    return EXIT_FAILURE;
  }
  return EXIT_SUCCESS;
}
