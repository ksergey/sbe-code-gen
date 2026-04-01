// ------------------------------------------------------------
// Copyright 2022-present Sergey Kovalevich <inndie@gmail.com>
// ------------------------------------------------------------

#include <cstddef>
#include <cstdio>
#include <iostream>
#include <print>
#include <span>
#include <string_view>
#include <type_traits>

#include "schema.h"

namespace content {

#include "Binance_exchangeInfo_data.h"
#include "Binance_ticker_data.h"

} // namespace content

int main([[maybe_unused]] int argc, [[maybe_unused]] char* argv[]) {
    try {
        [[maybe_unused]] auto buffer1 = std::span<std::byte>(
            std::bit_cast<std::byte*>((unsigned char*)content::exchangeInfo), content::exchangeInfo_len);
        [[maybe_unused]] auto buffer2 =
            std::span<std::byte>(std::bit_cast<std::byte*>((unsigned char*)content::ticker), content::ticker_len);

        auto header = spot_sbe::MessageHeader{buffer2.data()};
        if (header.get<"templateId">().value() == spot_sbe::Ticker24hFullResponse::sbeTemplateId()) {
            [[maybe_unused]] auto body = spot_sbe::Ticker24hFullResponse(buffer2, header.sbeEncodedLength(),
                header.get<"blockLength">().value(), header.get<"version">().value());
        }

    } catch (std::exception const& e) {
        std::print(stderr, "ERROR: {}\n", e.what());
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
