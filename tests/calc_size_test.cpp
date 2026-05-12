// Copyright (c) Sergey Kovalevich <inndie@gmail.com>

#include <doctest/doctest.h>

#include "schema.h"

TEST_CASE("calc_size: simple") {
    REQUIRE_EQ(spot_sbe::NonRepresentableMessage::calcBufferSize(), 0);
    REQUIRE_EQ(spot_sbe::PriceFilter::calcBufferSize(), 1 + 8 + 8 + 8);
    REQUIRE_EQ(spot_sbe::IcebergPartsFilter::calcBufferSize(), 8);
    REQUIRE_EQ(spot_sbe::PingResponse::calcBufferSize(), 0);
}

TEST_CASE("calc_size: repeating groups") {
    REQUIRE_EQ(spot_sbe::WebSocketSessionSubscriptionsResponse::calcBufferSize({4}), (6 + 4 * (2 + 8)));
    REQUIRE_EQ(spot_sbe::TradesResponse::calcBufferSize({1}), 1 + 1 + (6 + 1 * (8 + 8 + 8 + 8 + 8 + 1 + 1)));
    REQUIRE_EQ(spot_sbe::TradesResponse::calcBufferSize({3}), 1 + 1 + (6 + 3 * (8 + 8 + 8 + 8 + 8 + 1 + 1)));
}
