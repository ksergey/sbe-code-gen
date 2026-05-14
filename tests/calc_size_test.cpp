// Copyright (c) Sergey Kovalevich <inndie@gmail.com>

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
