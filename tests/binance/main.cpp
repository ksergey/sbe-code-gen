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
void view_set(std::string const& prefix, T value) {
  fmt::print(stdout, "{}: [", prefix);

  bool first = true;
  MP_forEach<MP_IndexSeq<MP_Size<typename T::Choices>>>([&](auto I) {
    auto const name = MP_At<typename T::Choices, MP_SizeT<I>>::first_type::value;
    auto const bit = MP_At<typename T::Choices, MP_SizeT<I>>::second_type::value;
    if (value.test(bit)) {
      if (!first) {
        fmt::print(stdout, ", ");
      }
      first = false;

      fmt::print(stdout, "{}", name);
    }
  });

  fmt::print(stdout, "]\n");
}

template <typename F>
void view(std::string prefix, F entry) {
  if constexpr (std::derived_from<F, SBEType_Type>) {
    if (entry.present()) {
      fmt::print(stdout, "{}: {}\n", prefix, entry.value());
    } else {
      fmt::print(stdout, "{}: N/A\n", prefix);
    }
  }

  if constexpr (std::derived_from<F, SBEType_Enum>) {
    if (entry.present()) {
      auto value = entry.value();
      fmt::print(stdout, "{}: {}\n", prefix, value.toCString(value.value()));
    } else {
      fmt::print(stdout, "{}: N/A\n", prefix);
    }
  }

  if constexpr (std::derived_from<F, SBEType_Set>) {
    view_set(prefix, entry.value());
  }

  if constexpr (std::derived_from<F, SBEType_Data>) {
    fmt::print(stdout, "{}: {}\n", prefix, entry.value());
  }

  if constexpr (std::derived_from<F, SBEType_Composite> or std::derived_from<F, SBEType_Message>) {
    MP_forEach<MP_IndexSeq<MP_Size<typename F::Fields>>>([&](auto I) {
      auto const name = MP_At<typename F::Fields, MP_SizeT<I>>::first_type::value;
      view(prefix + "." + std::string(name), entry.template field<I>());
    });
  }

  if constexpr (std::derived_from<F, SBEType_Group>) {
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
