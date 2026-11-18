// Copyright (c) Sergey Kovalevich <inndie@gmail.com>

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

#include <doctest/doctest.h>

#include "schema.h"

namespace {

constexpr std::array<std::byte, 2048> makeBuffer() {
    return {};
}

/// Fixed part of the Snapshot message: instrumentId (4) + ts (8) + appId (2)
constexpr std::size_t kSnapshotBlockLength = 14;
constexpr std::size_t kHeaderLength = 8;

/// Price/qty/orders entry of the bids or asks group
struct Order {
    std::int64_t priceMantissa;
    std::int8_t priceExponent;
    std::uint64_t qty;
    std::uint32_t orders{0};
    bool ordersPresent{true};
};

template <typename Group>
void writeOrder(Group& group, Order const& order) {
    group.template get<"price">().template get<"mantissa">().value(order.priceMantissa);
    group.template get<"price">().template get<"exponent">().value(order.priceExponent);
    group.template get<"qty">().value(order.qty);
    if (order.ordersPresent) {
        group.template get<"orders">().value(order.orders);
    } else {
        group.template get<"orders">().reset();
    }
}

template <typename Group>
void checkOrder(Group& group, Order const& order) {
    REQUIRE_EQ(group.template get<"price">().template get<"mantissa">().value(), order.priceMantissa);
    REQUIRE_EQ(group.template get<"price">().template get<"exponent">().value(), order.priceExponent);
    REQUIRE_EQ(group.template get<"qty">().value(), order.qty);
    REQUIRE_EQ(group.template get<"orders">().present(), order.ordersPresent);
    if (order.ordersPresent) {
        REQUIRE_EQ(group.template get<"orders">().value(), order.orders);
    }
}

auto decodeSnapshot(std::span<std::byte> buffer) -> alltypes::Snapshot {
    auto const header = alltypes::MessageHeader{buffer.data()};
    return alltypes::Snapshot{
        buffer, header.sbeEncodedLength(), header.get<"blockLength">().value(), header.get<"version">().value()};
}

/// Encode the full message: fixed part, three repeating groups and the trailing variable length data
auto encodeSnapshot(std::span<std::byte> buffer) -> alltypes::Snapshot {
    auto orders = std::array<Order, 2>{
        Order{101250000000, -9, 10, 3, true},
        Order{100500000000, -9, 5, 0, false},
    };

    auto msg = alltypes::Snapshot::wrapAndApplyHeader(buffer);
    msg.get<"instrumentId">().value(42);
    msg.get<"ts">().value(1'700'000'000'000);
    msg.get<"appId">().reset();

    auto bids = msg.get<"bids">();
    bids.reset(2);
    for (auto const& order : orders) {
        writeOrder(bids.next(), order);
    }
    auto asks = msg.get<"asks">();
    asks.reset(2);
    for (auto const& order : orders) {
        writeOrder(asks.next(), order);
    }

    auto stats = msg.get<"stats">();
    stats.reset(2);
    auto& stat0 = stats.next();
    stat0.get<"type">().value(alltypes::MessageType::NewOrder);
    stat0.get<"value">().get<"mantissa">().value(42);
    stat0.get<"value">().get<"exponent">().value(-2);
    auto& stat1 = stats.next();
    stat1.get<"type">().value(alltypes::MessageType::ExecutionReport);
    stat1.get<"value">().get<"mantissa">().value(7);
    stat1.get<"value">().get<"exponent">().value(0);

    msg.get<"symbol">().value("BTCUSDT");
    return msg;
}

template <typename T>
concept HasGroupName = requires { T::sbeGroupName(); };
template <typename T>
concept HasDataName = requires { T::sbeDataName(); };

} // namespace

TEST_CASE("snapshot: encode/decode with several repeating groups") {
    auto buffer = makeBuffer();

    auto msg = encodeSnapshot(buffer);
    REQUIRE_EQ(msg.position(), kHeaderLength + kSnapshotBlockLength + 6 + 2 * 21 + 6 + 2 * 21 + 4 + 2 * 10 + 8);
    REQUIRE_EQ(msg.encodedSize(), kSnapshotBlockLength + 6 + 2 * 21 + 6 + 2 * 21 + 4 + 2 * 10 + 8);

    auto decoded = decodeSnapshot(buffer);
    REQUIRE_EQ(decoded.position(), kHeaderLength + kSnapshotBlockLength);
    REQUIRE_EQ(decoded.actingBlockLength(), kSnapshotBlockLength);
    REQUIRE_EQ(decoded.get<"instrumentId">().value(), 42);
    REQUIRE_EQ(decoded.get<"ts">().value(), 1'700'000'000'000);
    REQUIRE_FALSE(decoded.get<"appId">().present());

    auto expected = std::array<Order, 2>{
        Order{101250000000, -9, 10, 3, true},
        Order{100500000000, -9, 5, 0, false},
    };

    auto decodedBids = decoded.get<"bids">();
    REQUIRE_EQ(decodedBids.count(), 2);
    std::size_t rows = 0;
    while (decodedBids.hasNext()) {
        checkOrder(decodedBids.next(), expected[rows]);
        ++rows;
    }
    REQUIRE_EQ(rows, 2);

    auto decodedAsks = decoded.get<"asks">();
    REQUIRE_EQ(decodedAsks.count(), 2);
    rows = 0;
    while (decodedAsks.hasNext()) {
        checkOrder(decodedAsks.next(), expected[rows]);
        ++rows;
    }
    REQUIRE_EQ(rows, 2);

    auto decodedStats = decoded.get<"stats">();
    REQUIRE_EQ(decodedStats.count(), 2);
    auto& decodedStat0 = decodedStats.next();
    REQUIRE_EQ(decodedStat0.get<"type">().value(), alltypes::MessageType::NewOrder);
    REQUIRE_EQ(decodedStat0.get<"value">().get<"mantissa">().value(), 42);
    REQUIRE_EQ(decodedStat0.get<"value">().get<"exponent">().value(), -2);
    auto& decodedStat1 = decodedStats.next();
    REQUIRE_EQ(decodedStat1.get<"type">().value(), alltypes::MessageType::ExecutionReport);
    REQUIRE_EQ(decodedStat1.get<"value">().get<"mantissa">().value(), 7);

    REQUIRE_EQ(decoded.get<"symbol">().value(), std::string_view{"BTCUSDT"});
    REQUIRE_EQ(decoded.position(), msg.position());
}

TEST_CASE("snapshot: rewind re-reads and rewrites the variable length part") {
    auto buffer = makeBuffer();
    auto msg = encodeSnapshot(buffer);
    auto const encoded = msg.position();

    auto decoded = decodeSnapshot(buffer);
    auto readAll = [&]() {
        auto bids = decoded.get<"bids">();
        REQUIRE_EQ(bids.count(), 2);
        REQUIRE_EQ(bids.next().get<"qty">().value(), 10);
        REQUIRE_EQ(bids.next().get<"qty">().value(), 5);
        auto asks = decoded.get<"asks">();
        REQUIRE_EQ(asks.count(), 2);
        REQUIRE_EQ(asks.next().get<"price">().get<"mantissa">().value(), 101250000000);
        REQUIRE_EQ(asks.next().get<"price">().get<"mantissa">().value(), 100500000000);
        auto stats = decoded.get<"stats">();
        REQUIRE_EQ(stats.count(), 2);
        stats.next();
        stats.next();
        REQUIRE_EQ(decoded.get<"symbol">().value(), std::string_view{"BTCUSDT"});
        REQUIRE_EQ(decoded.position(), encoded);
    };

    readAll();
    // the cursor is at the end of the message: without rewind a group read would be garbage
    REQUIRE_EQ(decoded.rewind().position(), kHeaderLength + kSnapshotBlockLength);
    readAll();

    // rewind the encoder and overwrite the variable length part with a shorter one
    auto const overwritten = std::array<Order, 1>{Order{999, -3, 1, 0, true}};
    REQUIRE_EQ(msg.rewind().position(), kHeaderLength + kSnapshotBlockLength);
    auto bids = msg.get<"bids">();
    bids.reset(1);
    writeOrder(bids.next(), overwritten[0]);
    msg.get<"asks">().reset(0);
    msg.get<"stats">().reset(0);
    msg.get<"symbol">().value("X");
    REQUIRE_EQ(msg.position(), kHeaderLength + kSnapshotBlockLength + 6 + 21 + 6 + 4 + 2);

    auto overwrittenDecoded = decodeSnapshot(buffer);
    auto decodedBids = overwrittenDecoded.get<"bids">();
    REQUIRE_EQ(decodedBids.count(), 1);
    checkOrder(decodedBids.next(), overwritten[0]);
    REQUIRE_EQ(overwrittenDecoded.get<"asks">().count(), 0);
    REQUIRE_EQ(overwrittenDecoded.get<"stats">().count(), 0);
    REQUIRE_EQ(overwrittenDecoded.get<"symbol">().value(), std::string_view{"X"});
}

TEST_CASE("snapshot: empty repeating groups") {
    auto buffer = makeBuffer();

    auto msg = alltypes::Snapshot::wrapAndApplyHeader(buffer);
    msg.get<"appId">().value(7);
    msg.get<"bids">().reset(0);
    msg.get<"asks">().reset(0);
    msg.get<"stats">().reset(0);
    msg.get<"symbol">().value("");
    REQUIRE_EQ(msg.position(), kHeaderLength + kSnapshotBlockLength + 6 + 6 + 4 + 1);

    auto decoded = decodeSnapshot(buffer);
    REQUIRE_EQ(decoded.get<"appId">().value(), 7);
    REQUIRE_EQ(decoded.get<"bids">().count(), 0);
    REQUIRE_EQ(decoded.get<"asks">().count(), 0);
    REQUIRE_EQ(decoded.get<"stats">().count(), 0);
    REQUIRE_EQ(decoded.get<"symbol">().value(), std::string_view{});
    REQUIRE_EQ(decoded.position(), msg.position());
}

TEST_CASE("snapshot: field kind metadata") {
    REQUIRE_EQ(alltypes::Snapshot::sbeMessageName(), "Snapshot");
    REQUIRE_EQ(alltypes::Snapshot::sbeBlockLength(), kSnapshotBlockLength);
    REQUIRE_EQ(alltypes::Snapshot::sbeTemplateId(), 4);

    // groups are recognizable by sbeGroupName(), data fields by sbeDataName()
    REQUIRE_EQ(alltypes::Snapshot::BidsRef::sbeGroupName(), "bids");
    REQUIRE_EQ(alltypes::Snapshot::AsksRef::sbeGroupName(), "asks");
    REQUIRE_EQ(alltypes::Snapshot::StatsRef::sbeGroupName(), "stats");
    REQUIRE_EQ(alltypes::Snapshot::SymbolRef::sbeDataName(), "symbol");

    static_assert(HasGroupName<alltypes::Snapshot::BidsRef>);
    static_assert(!HasDataName<alltypes::Snapshot::BidsRef>);
    static_assert(HasDataName<alltypes::Snapshot::SymbolRef>);
    static_assert(!HasGroupName<alltypes::Snapshot::SymbolRef>);
}
