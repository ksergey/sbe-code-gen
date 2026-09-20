// Copyright (c) Sergey Kovalevich <inndie@gmail.com>

#include <array>
#include <cstddef>
#include <cstdint>
#include <string_view>
#include <tuple>
#include <vector>

#include <doctest/doctest.h>

#include "schema.h"

namespace {

constexpr std::array<std::byte, 2048> makeBuffer() {
    return {};
}

} // namespace

TEST_CASE("all-types-big-endian: metadata") {
    REQUIRE_EQ(alltypes_be::AllTypesMessage::sbeMessageName(), "AllTypesMessage");
    REQUIRE_EQ(alltypes_be::AllTypesMessage::sbeBlockLength(), 134);
    REQUIRE_EQ(alltypes_be::AllTypesMessage::sbeTemplateId(), 1);
    REQUIRE_EQ(alltypes_be::AllTypesMessage::sbeSchemaId(), 1);
    REQUIRE_EQ(alltypes_be::AllTypesMessage::sbeVersion(), 1);

    REQUIRE_EQ(alltypes_be::EmptyMessage::sbeMessageName(), "EmptyMessage");
    REQUIRE_EQ(alltypes_be::EmptyMessage::sbeBlockLength(), 0);
    REQUIRE_EQ(alltypes_be::EmptyMessage::sbeTemplateId(), 2);

    REQUIRE_EQ(alltypes_be::DataOnlyMessage::sbeMessageName(), "DataOnlyMessage");
    REQUIRE_EQ(alltypes_be::DataOnlyMessage::sbeBlockLength(), 0);
    REQUIRE_EQ(alltypes_be::DataOnlyMessage::sbeTemplateId(), 3);
}

TEST_CASE("all-types-big-endian: wire bytes are actually big-endian") {
    // Round-tripping alone doesn't prove byte order: a codec that used
    // little-endian consistently for both encode and decode would
    // round-trip too. Read the raw wire bytes directly instead.
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);
    msg.get<"u32">().value(0x01020304u);

    auto const* raw = reinterpret_cast<std::uint8_t const*>(buffer.data()) + 8 + 26;
    REQUIRE_EQ(raw[0], 0x01);
    REQUIRE_EQ(raw[1], 0x02);
    REQUIRE_EQ(raw[2], 0x03);
    REQUIRE_EQ(raw[3], 0x04);
}

TEST_CASE("all-types-big-endian: header round trip") {
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);
    REQUIRE_EQ(msg.position(), 8 + 134);

    auto header = alltypes_be::MessageHeader{buffer.data()};
    REQUIRE_EQ(header.get<"blockLength">().value(), alltypes_be::AllTypesMessage::sbeBlockLength());
    REQUIRE_EQ(header.get<"templateId">().value(), alltypes_be::AllTypesMessage::sbeTemplateId());
    REQUIRE_EQ(header.get<"schemaId">().value(), alltypes_be::AllTypesMessage::sbeSchemaId());
    REQUIRE_EQ(header.get<"version">().value(), alltypes_be::AllTypesMessage::sbeVersion());
}

TEST_CASE("all-types-big-endian: scalars and enums round trip") {
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);
    msg.get<"id">().value(7);
    msg.get<"qty">().value(9);
    msg.get<"price">().value(-3);
    msg.get<"s8">().value(-8);
    msg.get<"s16">().value(-16);
    msg.get<"u8">().value(3);
    msg.get<"u16">().value(66);
    msg.get<"u32">().value(66'666);
    msg.get<"f32">().value(1.25f);
    msg.get<"f64">().value(2.5);
    msg.get<"mType">().value(alltypes_be::MessageType::ExecutionReport);
    msg.get<"side">().value(alltypes_be::Side::Sell);
    msg.get<"bigType">().value(alltypes_be::BigType::Gamma);
    msg.get<"bits">().value(alltypes_be::Bits8::On);
    msg.get<"wideEnum32">().value(alltypes_be::WideEnum32::ValueB);
    msg.get<"wideEnum64">().value(alltypes_be::WideEnum64::BigB);

    auto header = alltypes_be::MessageHeader{buffer.data()};
    auto decoded = alltypes_be::AllTypesMessage{buffer,
                                                header.sbeEncodedLength(),
                                                header.get<"blockLength">().value(),
                                                header.get<"version">().value()};

    REQUIRE_EQ(decoded.get<"id">().value(), 7);
    REQUIRE_EQ(decoded.get<"qty">().value(), 9);
    REQUIRE_EQ(decoded.get<"price">().value(), -3);
    REQUIRE_EQ(decoded.get<"s8">().value(), -8);
    REQUIRE_EQ(decoded.get<"s16">().value(), -16);
    REQUIRE_EQ(decoded.get<"u8">().value(), 3);
    REQUIRE_EQ(decoded.get<"u16">().value(), 66);
    REQUIRE_EQ(decoded.get<"u32">().value(), 66'666);
    REQUIRE_EQ(decoded.get<"f32">().value(), 1.25f);
    REQUIRE_EQ(decoded.get<"f64">().value(), 2.5);
    REQUIRE_EQ(decoded.get<"mType">().value(), alltypes_be::MessageType::ExecutionReport);
    REQUIRE_EQ(decoded.get<"side">().value(), alltypes_be::Side::Sell);
    REQUIRE_EQ(decoded.get<"bigType">().value(), alltypes_be::BigType::Gamma);
    REQUIRE_EQ(decoded.get<"bits">().value(), alltypes_be::Bits8::On);
    REQUIRE_EQ(decoded.get<"wideEnum32">().value(), alltypes_be::WideEnum32::ValueB);
    REQUIRE_EQ(decoded.get<"wideEnum64">().value(), alltypes_be::WideEnum64::BigB);
}

TEST_CASE("all-types-big-endian: sets and fixed arrays round trip") {
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);

    auto flags = alltypes_be::Flags{};
    flags.bit0(true).bit2(true).bit5(false).bit7(true);
    msg.get<"flags">().value(flags);

    auto bigFlags = alltypes_be::BigFlags{};
    bigFlags.first(true).top(true);
    msg.get<"bigFlags">().value(bigFlags);

    msg.get<"symbol">().value("BTC-USD");

    auto header = alltypes_be::MessageHeader{buffer.data()};
    auto decoded = alltypes_be::AllTypesMessage{buffer,
                                                header.sbeEncodedLength(),
                                                header.get<"blockLength">().value(),
                                                header.get<"version">().value()};

    auto decodedFlags = decoded.get<"flags">().value();
    REQUIRE(decodedFlags.bit0());
    REQUIRE(decodedFlags.bit2());
    REQUIRE_FALSE(decodedFlags.bit5());
    REQUIRE(decodedFlags.bit7());

    auto decodedBigFlags = decoded.get<"bigFlags">().value();
    REQUIRE(decodedBigFlags.first());
    REQUIRE(decodedBigFlags.top());

    REQUIRE_EQ(decoded.get<"symbol">().value(), std::string_view{"BTC-USD"});
}

TEST_CASE("all-types-big-endian: composites round trip") {
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);

    msg.get<"decimal1">().get<"mantissa">().value(123'456);
    msg.get<"decimal1">().get<"exponent">().value(-4);

    msg.get<"outerField">().get<"qty">().value(5);
    msg.get<"outerField">().get<"dec">().get<"mantissa">().value(11);
    msg.get<"outerField">().get<"dec">().get<"exponent">().value(-1);
    msg.get<"outerField">().get<"side">().value(alltypes_be::Side::Sell);

    msg.get<"nestedField">().get<"topVal">().value(3);
    msg.get<"nestedField">().get<"inner">().get<"innerVal">().value(-77);
    msg.get<"nestedField">().get<"inner">().get<"innerTag">().value("hi");

    auto header = alltypes_be::MessageHeader{buffer.data()};
    auto decoded = alltypes_be::AllTypesMessage{buffer,
                                                header.sbeEncodedLength(),
                                                header.get<"blockLength">().value(),
                                                header.get<"version">().value()};

    REQUIRE(decoded.get<"decimal1">().present());
    REQUIRE_EQ(decoded.get<"decimal1">().get<"mantissa">().value(), 123'456);
    REQUIRE_EQ(decoded.get<"decimal1">().get<"exponent">().value(), -4);

    REQUIRE(decoded.get<"outerField">().present());
    REQUIRE_EQ(decoded.get<"outerField">().get<"qty">().value(), 5);
    REQUIRE_EQ(decoded.get<"outerField">().get<"dec">().get<"mantissa">().value(), 11);
    REQUIRE_EQ(decoded.get<"outerField">().get<"dec">().get<"exponent">().value(), -1);
    REQUIRE_EQ(decoded.get<"outerField">().get<"side">().value(), alltypes_be::Side::Sell);

    REQUIRE(decoded.get<"nestedField">().present());
    REQUIRE_EQ(decoded.get<"nestedField">().get<"topVal">().value(), 3);
    REQUIRE_EQ(decoded.get<"nestedField">().get<"inner">().get<"innerVal">().value(), -77);
    REQUIRE_EQ(decoded.get<"nestedField">().get<"inner">().get<"innerTag">().value(), std::string_view{"hi"});
}

TEST_CASE("all-types-big-endian: optional fields") {
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);

    REQUIRE_FALSE(msg.get<"optSide">().present());
    REQUIRE_FALSE(msg.get<"optString">().present());

    msg.get<"optVal">().value(-100);
    msg.get<"optPrice">().value(123);
    msg.get<"optQty">().value(42);
    msg.get<"optDouble">().value(1.5);
    msg.get<"optSide">().value(alltypes_be::Side::Buy);
    msg.get<"optString">().value("abcdef");

    auto header = alltypes_be::MessageHeader{buffer.data()};
    auto decoded = alltypes_be::AllTypesMessage{buffer,
                                                header.sbeEncodedLength(),
                                                header.get<"blockLength">().value(),
                                                header.get<"version">().value()};

    REQUIRE(decoded.get<"optVal">().present());
    REQUIRE(decoded.get<"optPrice">().present());
    REQUIRE(decoded.get<"optQty">().present());
    REQUIRE(decoded.get<"optDouble">().present());
    REQUIRE(decoded.get<"optSide">().present());
    REQUIRE(decoded.get<"optString">().present());

    REQUIRE_EQ(decoded.get<"optVal">().value(), -100);
    REQUIRE_EQ(decoded.get<"optPrice">().value(), 123);
    REQUIRE_EQ(decoded.get<"optQty">().value(), 42);
    REQUIRE_EQ(decoded.get<"optDouble">().value(), 1.5);
    REQUIRE_EQ(decoded.get<"optSide">().value(), alltypes_be::Side::Buy);
    REQUIRE_EQ(decoded.get<"optString">().value(), std::string_view{"abcdef"});

    msg.get<"optVal">().reset();
    msg.get<"optPrice">().reset();
    msg.get<"optQty">().reset();
    msg.get<"optDouble">().reset();
    msg.get<"optSide">().reset();
    msg.get<"optString">().reset();
    REQUIRE_FALSE(msg.get<"optVal">().present());
    REQUIRE_FALSE(msg.get<"optPrice">().present());
    REQUIRE_FALSE(msg.get<"optQty">().present());
    REQUIRE_FALSE(msg.get<"optDouble">().present());
    REQUIRE_FALSE(msg.get<"optSide">().present());
    REQUIRE_FALSE(msg.get<"optString">().present());
}

TEST_CASE("all-types-big-endian: constant fields") {
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);
    REQUIRE_EQ(msg.get<"constEnum">().value(), alltypes_be::MessageType::ExecutionReport);
    REQUIRE_EQ(msg.get<"constStr">().value(), std::string_view{"1.0"});
    REQUIRE_EQ(msg.get<"constNum">().value(), 42);
}

TEST_CASE("all-types-big-endian: ticks group round trip") {
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);

    auto ticks = msg.get<"ticks">();
    ticks.reset(2);
    while (ticks.hasNext()) {
        auto& tick = ticks.next();
        tick.get<"tickValue">().value(-1);
        tick.get<"tickTag">().value(9);
    }
    REQUIRE_EQ(msg.position(), 8 + 134 + 2 + 2 * 5);

    auto header = alltypes_be::MessageHeader{buffer.data()};
    auto decoded = alltypes_be::AllTypesMessage{buffer,
                                                header.sbeEncodedLength(),
                                                header.get<"blockLength">().value(),
                                                header.get<"version">().value()};
    auto decodedTicks = decoded.get<"ticks">();
    REQUIRE_EQ(decodedTicks.count(), 2);
    std::size_t rows = 0;
    while (decodedTicks.hasNext()) {
        auto& tick = decodedTicks.next();
        REQUIRE_EQ(tick.get<"tickValue">().value(), -1);
        REQUIRE_EQ(tick.get<"tickTag">().value(), 9);
        ++rows;
    }
    REQUIRE_EQ(rows, 2);
}

TEST_CASE("all-types-big-endian: buckets group round trip") {
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);

    auto buckets = msg.get<"buckets">();
    buckets.reset(2);
    REQUIRE_EQ(msg.position(), 8 + 134 + 4);
    uint64_t bucketId = 1;
    while (buckets.hasNext()) {
        auto& bucket = buckets.next();
        bucket.get<"bucketId">().value(bucketId);
        bucket.get<"weight">().value(1.5f * static_cast<float>(bucketId));
        ++bucketId;
    }

    auto header = alltypes_be::MessageHeader{buffer.data()};
    auto decoded = alltypes_be::AllTypesMessage{buffer,
                                                header.sbeEncodedLength(),
                                                header.get<"blockLength">().value(),
                                                header.get<"version">().value()};
    auto decodedBuckets = decoded.get<"buckets">();
    REQUIRE_EQ(decodedBuckets.count(), 2);
    std::size_t rows = 0;
    while (decodedBuckets.hasNext()) {
        auto& bucket = decodedBuckets.next();
        REQUIRE_EQ(bucket.get<"bucketId">().value(), uint64_t(rows + 1));
        REQUIRE_EQ(bucket.get<"weight">().value(), 1.5f * static_cast<float>(rows + 1));
        ++rows;
    }
    REQUIRE_EQ(rows, 2);
}

TEST_CASE("all-types-big-endian: entries group round trip") {
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);

    auto entries = msg.get<"entries">();
    entries.reset(2);

    auto& entry0 = entries.next();
    entry0.get<"seq">().value(1);
    entry0.get<"amount">().value(100'000);
    entry0.get<"tag">().value("ab");
    auto flags = alltypes_be::Flags{};
    flags.bit0(true).bit2(true);
    entry0.get<"tflags">().value(flags);
    entry0.get<"ttype">().value(alltypes_be::MessageType::NewOrder);
    entry0.get<"tDec">().get<"mantissa">().value(9'999);
    entry0.get<"tDec">().get<"exponent">().value(2);
    auto sub0 = entry0.get<"sub">();
    sub0.reset(2);
    while (sub0.hasNext()) {
        auto& sub = sub0.next();
        sub.get<"subId">().value(10);
        sub.get<"subVal">().value(100);
    }
    entry0.get<"note">().value("note!");

    auto& entry1 = entries.next();
    entry1.get<"seq">().value(2);
    entry1.get<"amount">().value(-1);
    entry1.get<"tag">().value("");
    entry1.get<"ttype">().value(alltypes_be::MessageType::ExecutionReport);
    entry1.get<"tDec">().get<"exponent">().value(-3);
    entry1.get<"sub">().reset(0);
    entry1.get<"note">().value("n");

    auto header = alltypes_be::MessageHeader{buffer.data()};
    auto decoded = alltypes_be::AllTypesMessage{buffer,
                                                header.sbeEncodedLength(),
                                                header.get<"blockLength">().value(),
                                                header.get<"version">().value()};
    auto decodedEntries = decoded.get<"entries">();
    REQUIRE_EQ(decodedEntries.count(), 2);

    auto& decodedEntry0 = decodedEntries.next();
    REQUIRE_EQ(decodedEntry0.get<"seq">().value(), 1);
    REQUIRE_EQ(decodedEntry0.get<"amount">().value(), 100'000);
    REQUIRE_EQ(decodedEntry0.get<"tag">().value(), std::string_view{"ab"});
    auto decodedFlags = decodedEntry0.get<"tflags">().value();
    REQUIRE(decodedFlags.bit0());
    REQUIRE(decodedFlags.bit2());
    REQUIRE_EQ(decodedEntry0.get<"ttype">().value(), alltypes_be::MessageType::NewOrder);
    REQUIRE_EQ(decodedEntry0.get<"tDec">().get<"mantissa">().value(), 9'999);
    REQUIRE_EQ(decodedEntry0.get<"tDec">().get<"exponent">().value(), 2);
    auto decodedSub0 = decodedEntry0.get<"sub">();
    REQUIRE_EQ(decodedSub0.count(), 2);
    while (decodedSub0.hasNext()) {
        auto& sub = decodedSub0.next();
        REQUIRE_EQ(sub.get<"subId">().value(), 10);
        REQUIRE_EQ(sub.get<"subVal">().value(), 100);
    }
    REQUIRE_EQ(decodedEntry0.get<"note">().value(), std::string_view{"note!"});

    auto& decodedEntry1 = decodedEntries.next();
    REQUIRE_EQ(decodedEntry1.get<"seq">().value(), 2);
    REQUIRE_EQ(decodedEntry1.get<"amount">().value(), -1);
    REQUIRE_EQ(decodedEntry1.get<"tag">().value(), std::string_view{""});
    REQUIRE_EQ(decodedEntry1.get<"ttype">().value(), alltypes_be::MessageType::ExecutionReport);
    REQUIRE_EQ(decodedEntry1.get<"tDec">().get<"exponent">().value(), -3);
    REQUIRE_EQ(decodedEntry1.get<"sub">().count(), 0);
    REQUIRE_EQ(decodedEntry1.get<"note">().value(), std::string_view{"n"});
}

TEST_CASE("all-types-big-endian: blobRecords group round trip") {
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);

    auto records = msg.get<"blobRecords">();
    records.reset(1);
    auto& record = records.next();
    record.get<"recordId">().value(77);
    record.get<"label">().value("EUR/USD");
    std::array<std::uint8_t, 4> payload = {0xde, 0xad, 0xbe, 0xef};
    record.get<"payload">().value(payload);

    auto header = alltypes_be::MessageHeader{buffer.data()};
    auto decoded = alltypes_be::AllTypesMessage{buffer,
                                                header.sbeEncodedLength(),
                                                header.get<"blockLength">().value(),
                                                header.get<"version">().value()};
    auto decodedRecords = decoded.get<"blobRecords">();
    REQUIRE_EQ(decodedRecords.count(), 1);
    auto& decodedRecord = decodedRecords.next();
    REQUIRE_EQ(decodedRecord.get<"recordId">().value(), 77);
    REQUIRE_EQ(decodedRecord.get<"label">().value(), std::string_view{"EUR/USD"});
    auto decodedPayload = decodedRecord.get<"payload">().value();
    REQUIRE_EQ(decodedPayload.size(), 4u);
    REQUIRE_EQ(decodedPayload[0], 0xde);
    REQUIRE_EQ(decodedPayload[1], 0xad);
    REQUIRE_EQ(decodedPayload[2], 0xbe);
    REQUIRE_EQ(decodedPayload[3], 0xef);
}

TEST_CASE("all-types-big-endian: variable length data round trip") {
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);

    msg.get<"traceId">().value("trace-1");
    msg.get<"summary">().value("spread summary");
    std::array<std::uint8_t, 4> blob = {1, 2, 3, 4};
    msg.get<"blob">().value(blob);
    std::array<std::uint8_t, 300> bigBlob{};
    for (std::size_t i = 0; i < bigBlob.size(); ++i) {
        bigBlob[i] = static_cast<std::uint8_t>(i);
    }
    msg.get<"bigBlob">().value(bigBlob);

    auto header = alltypes_be::MessageHeader{buffer.data()};
    auto decoded = alltypes_be::AllTypesMessage{buffer,
                                                header.sbeEncodedLength(),
                                                header.get<"blockLength">().value(),
                                                header.get<"version">().value()};

    REQUIRE_EQ(decoded.get<"traceId">().value(), std::string_view{"trace-1"});
    REQUIRE_EQ(decoded.get<"summary">().value(), std::string_view{"spread summary"});
    auto decodedBlob = decoded.get<"blob">().value();
    REQUIRE_EQ(decodedBlob.size(), 4u);
    REQUIRE_EQ(decodedBlob[0], 1u);
    REQUIRE_EQ(decodedBlob[1], 2u);
    REQUIRE_EQ(decodedBlob[2], 3u);
    REQUIRE_EQ(decodedBlob[3], 4u);
    auto decodedBigBlob = decoded.get<"bigBlob">().value();
    REQUIRE_EQ(decodedBigBlob.size(), 300u);
    for (std::size_t i = 0; i < decodedBigBlob.size(); ++i) {
        REQUIRE_EQ(decodedBigBlob[i], static_cast<std::uint8_t>(i));
    }
}

TEST_CASE("all-types-big-endian: compute sizes") {
    REQUIRE_EQ(alltypes_be::EmptyMessage::sbeComputeSize(), 0);
    REQUIRE_EQ(alltypes_be::DataOnlyMessage::sbeComputeSize({5}), 5 + 1);

    auto hint = std::make_tuple(
        std::vector<std::tuple<std::size_t, std::size_t>>{}, // entries
        std::size_t{0},                                        // buckets
        std::vector<std::tuple<std::size_t, std::size_t>>{}, // blobRecords
        std::size_t{2},                                        // ticks
        std::size_t{0},                                        // traceId
        std::size_t{0},                                        // summary
        std::size_t{0},                                        // blob
        std::size_t{0}                                         // bigBlob
    );
    REQUIRE_EQ(alltypes_be::AllTypesMessage::sbeComputeSize(hint), 134 + 6 + 4 + 6 + (2 * 5 + 2) + 1 + 2 + 2 + 4);
}

TEST_CASE("all-types-big-endian: full round trip sized via sbeComputeSize") {
    auto buffer = makeBuffer();

    auto msg = alltypes_be::AllTypesMessage::wrapAndApplyHeader(buffer);

    msg.get<"id">().value(7);
    msg.get<"qty">().value(9);
    msg.get<"price">().value(-3);
    msg.get<"symbol">().value("ABC");

    auto entries = msg.get<"entries">();
    entries.reset(1);
    auto& entry = entries.next();
    entry.get<"seq">().value(1);
    auto sub = entry.get<"sub">();
    sub.reset(1);
    sub.next().get<"subId">().value(10);
    entry.get<"note">().value("note!");

    auto buckets = msg.get<"buckets">();
    buckets.reset(1);
    buckets.next().get<"bucketId">().value(1);

    auto records = msg.get<"blobRecords">();
    records.reset(1);
    auto& record = records.next();
    record.get<"recordId">().value(1);
    record.get<"label">().value("lbl");
    std::array<std::uint8_t, 2> payload = {1, 2};
    record.get<"payload">().value(payload);

    auto ticks = msg.get<"ticks">();
    ticks.reset(2);
    while (ticks.hasNext()) {
        auto& tick = ticks.next();
        tick.get<"tickValue">().value(-1);
        tick.get<"tickTag">().value(9);
    }

    msg.get<"traceId">().value("tr");
    msg.get<"summary">().value("sm");
    std::array<std::uint8_t, 4> blob = {1, 2, 3, 4};
    msg.get<"blob">().value(blob);
    std::array<std::uint8_t, 300> bigBlob{};
    msg.get<"bigBlob">().value(bigBlob);

    auto hint = std::make_tuple(
        std::vector<std::tuple<std::size_t, std::size_t>>{
            std::tuple<std::size_t, std::size_t>{1, 5}    // sub count, note length
        },
        std::size_t{1},                                    // buckets
        std::vector<std::tuple<std::size_t, std::size_t>>{
            std::tuple<std::size_t, std::size_t>{3, 2}     // label length, payload length
        },
        std::size_t{2},                                    // ticks
        std::size_t{2},                                    // traceId
        std::size_t{2},                                    // summary
        std::size_t{4},                                    // blob
        std::size_t{300}                                   // bigBlob
    );
    std::size_t const expectedBody = alltypes_be::AllTypesMessage::sbeComputeSize(hint);
    REQUIRE_EQ(msg.position(), 8 + expectedBody);
    REQUIRE_EQ(msg.encodedSize(), expectedBody);

    auto header = alltypes_be::MessageHeader{buffer.data()};
    auto decoded = alltypes_be::AllTypesMessage{buffer,
                                                header.sbeEncodedLength(),
                                                header.get<"blockLength">().value(),
                                                header.get<"version">().value()};
    REQUIRE_EQ(decoded.get<"id">().value(), 7);
    REQUIRE_EQ(decoded.get<"qty">().value(), 9);
    REQUIRE_EQ(decoded.get<"price">().value(), -3);
    auto decodedEntries = decoded.get<"entries">();
    REQUIRE_EQ(decodedEntries.count(), 1);
    auto& decodedEntry = decodedEntries.next();
    REQUIRE_EQ(decodedEntry.get<"seq">().value(), 1);
    auto decodedSub = decodedEntry.get<"sub">();
    REQUIRE_EQ(decodedSub.count(), 1);
    REQUIRE_EQ(decodedSub.next().get<"subId">().value(), 10);
    REQUIRE_EQ(decodedEntry.get<"note">().value(), std::string_view{"note!"});
    auto decodedBuckets = decoded.get<"buckets">();
    REQUIRE_EQ(decodedBuckets.count(), 1);
    REQUIRE_EQ(decodedBuckets.next().get<"bucketId">().value(), 1);
    auto decodedRecords = decoded.get<"blobRecords">();
    REQUIRE_EQ(decodedRecords.count(), 1);
    auto& decodedRecord = decodedRecords.next();
    REQUIRE_EQ(decodedRecord.get<"recordId">().value(), 1);
    REQUIRE_EQ(decodedRecord.get<"label">().value(), std::string_view{"lbl"});
    REQUIRE_EQ(decodedRecord.get<"payload">().value().size(), 2u);
    auto decodedTicks = decoded.get<"ticks">();
    REQUIRE_EQ(decodedTicks.count(), 2);
    while (decodedTicks.hasNext()) {
        auto& tick = decodedTicks.next();
        REQUIRE_EQ(tick.get<"tickValue">().value(), -1);
        REQUIRE_EQ(tick.get<"tickTag">().value(), 9);
    }
    REQUIRE_EQ(decoded.get<"traceId">().value(), std::string_view{"tr"});
    REQUIRE_EQ(decoded.get<"summary">().value(), std::string_view{"sm"});
    REQUIRE_EQ(decoded.get<"blob">().value().size(), 4u);
    REQUIRE_EQ(decoded.get<"bigBlob">().value().size(), 300u);
}

TEST_CASE("all-types-big-endian: empty and data-only messages") {
    auto buffer = makeBuffer();

    auto empty = alltypes_be::EmptyMessage::wrapAndApplyHeader(buffer);
    REQUIRE_EQ(empty.position(), 8);
    REQUIRE(empty.encodedSize() == 0);
    auto header = alltypes_be::MessageHeader{buffer.data()};
    REQUIRE_EQ(header.get<"templateId">().value(), alltypes_be::EmptyMessage::sbeTemplateId());

    auto dataOnly = alltypes_be::DataOnlyMessage::wrapAndApplyHeader(buffer);
    dataOnly.get<"payload">().value("hello");
    REQUIRE_EQ(dataOnly.encodedSize(), 1 + 5);
    auto dataOnlyHeader = alltypes_be::MessageHeader{buffer.data()};
    REQUIRE_EQ(dataOnlyHeader.get<"templateId">().value(), alltypes_be::DataOnlyMessage::sbeTemplateId());
    auto decoded = alltypes_be::DataOnlyMessage{buffer,
                                                dataOnlyHeader.sbeEncodedLength(),
                                                dataOnlyHeader.get<"blockLength">().value(),
                                                dataOnlyHeader.get<"version">().value()};
    REQUIRE_EQ(decoded.get<"payload">().value(), std::string_view{"hello"});
}