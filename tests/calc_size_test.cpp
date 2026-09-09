// Copyright (c) Sergey Kovalevich <inndie@gmail.com>

#include <array>
#include <cstddef>

#include <doctest/doctest.h>

#include "schema.h"

TEST_CASE("calc_size: simple") {
    REQUIRE_EQ(spot_sbe::NonRepresentableMessage::sbeComputeSize(), 0);
    REQUIRE_EQ(spot_sbe::PriceFilter::sbeComputeSize(), 1 + 8 + 8 + 8);
    REQUIRE_EQ(spot_sbe::IcebergPartsFilter::sbeComputeSize(), 8);
    REQUIRE_EQ(spot_sbe::PingResponse::sbeComputeSize(), 0);
}

TEST_CASE("calc_size: repeating groups") {
    REQUIRE_EQ(spot_sbe::WebSocketSessionSubscriptionsResponse::sbeComputeSize({4}), (6 + 4 * (2 + 8)));
    REQUIRE_EQ(spot_sbe::TradesResponse::sbeComputeSize({1}), 1 + 1 + (6 + 1 * (8 + 8 + 8 + 8 + 8 + 1 + 1)));
    REQUIRE_EQ(spot_sbe::TradesResponse::sbeComputeSize({3}), 1 + 1 + (6 + 3 * (8 + 8 + 8 + 8 + 8 + 1 + 1)));
}

TEST_CASE("group: encode/decode round trip") {
    std::array<std::byte, 1024> buffer{};

    auto msg = spot_sbe::KlinesResponse::wrapAndApplyHeader(buffer);
    msg.get<"priceExponent">().value(-8);
    msg.get<"qtyExponent">().value(-6);

    auto klines = msg.get<"klines">();
    klines.reset(2);
    while (klines.hasNext()) {
        auto& entry = klines.next();
        entry.get<"openTime">().value(1'700'000'000'000);
        entry.get<"openPrice">().value(100);
        entry.get<"closePrice">().value(101);
    }

    REQUIRE_EQ(msg.position(), 8 + 2 + 6 + 2 * 120);

    auto header = spot_sbe::MessageHeader{buffer.data()};
    REQUIRE_EQ(header.get<"templateId">().value(), spot_sbe::KlinesResponse::sbeTemplateId());
    auto decoded = spot_sbe::KlinesResponse{buffer,
                                            header.sbeEncodedLength(),
                                            header.get<"blockLength">().value(),
                                            header.get<"version">().value()};
    auto decodedKlines = decoded.get<"klines">();
    REQUIRE_EQ(decodedKlines.count(), 2);
    std::size_t rows = 0;
    while (decodedKlines.hasNext()) {
        auto& entry = decodedKlines.next();
        REQUIRE_EQ(entry.get<"openPrice">().value(), 100);
        ++rows;
    }
    REQUIRE_EQ(rows, 2);
}
