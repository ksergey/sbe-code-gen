// ------------------------------------------------------------
// Copyright 2022-present Sergey Kovalevich <inndie@gmail.com>
// ------------------------------------------------------------

#include <doctest/doctest.h>

#include <fmt/format.h>
#include <fmt/ranges.h>

#include "schema.h"

namespace content {

#include "Binance_exchangeInfo_data.h"

} // namespace content

namespace spot_sbe {

template <typename T>
constexpr T const& convert(T const& value) {
  return value;
}

template <typename T>
  requires(std::derived_from<T, SBEType_Enum>)
constexpr char const* convert(T const& value) {
  return T::toCString(value);
}

template <typename T>
  requires(std::derived_from<T, SBEType_Composite>)
constexpr char const* convert([[maybe_unused]] T const& value) {
  return "composite here";
}

template <typename T>
  requires(std::derived_from<T, SBEType_Set>)
constexpr char const* convert([[maybe_unused]] T const& value) {
  return "set here";
}

template <typename F>
void view(std::string prefix, F entry) {
  if constexpr (requires { entry.value(); }) {
    if constexpr (requires { entry.present(); }) {
      // SBEType_Enum, SBEType_Set, SBEType_Type
      fmt::print(stdout, "{}: {} ({})\n", prefix, convert(entry.value()), entry.present());
    } else {
      // SBEType_Data
      fmt::print(stdout, "{}: {}\n", prefix, convert(entry.value()));
    }
  } else if constexpr (requires { entry.template field<0>(); }) {
    if constexpr (requires { entry.hasNext(); }) {
      // SBEType_Group
      fmt::print("{} (count={}, blockLength={}):\n", prefix, entry.count(), entry.actingBlockLength());
      std::size_t num = 0;
      while (entry.hasNext()) {
        entry.next();
        // SBEType_Message, SBEType_Composite
        MP_forEach<MP_IndexSeq<MP_Size<typename F::Fields>>>([&](auto I) {
          auto const name = MP_At<typename F::Fields, MP_SizeT<I>>::first_type::value;
          view(prefix + "[" + std::to_string(num) + "]." + std::string(name), entry.template field<I>());
        });
        num++;
      }

    } else {
      // SBEType_Message, SBEType_Composite
      MP_forEach<MP_IndexSeq<MP_Size<typename F::Fields>>>([&](auto I) {
        auto const name = MP_At<typename F::Fields, MP_SizeT<I>>::first_type::value;
        view(prefix + "." + std::string(name), entry.template field<I>());
      });
    }
  } else {
    fmt::print(stdout, "{}: wtf?\n", prefix);
  }
}

TEST_CASE("schema") {
  MessageHeader messageHeader(
      reinterpret_cast<std::byte*>(content::binance_exchangeInfo_sbe), content::binance_exchangeInfo_sbe_len);
  view("MessageHeader", messageHeader);
  REQUIRE_EQ(messageHeader.field<"templateId">().present(), true);
  REQUIRE_EQ(messageHeader.field<"templateId">().value(), ExchangeInfoResponse::sbeTemplateId());

  ExchangeInfoResponse body(messageHeader.buffer(), messageHeader.encodedLength(), messageHeader.bufferLength(),
      messageHeader.field<"blockLength">().value(), messageHeader.field<"version">().value());

  view("ExchangeInfoResponse", body);
}

} // namespace spot_sbe
