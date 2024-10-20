// Copyright (c) Sergey Kovalevich <inndie@gmail.com>
// SPDX-License-Identifier: AGPL-3.0

#include <array>

#include <doctest/doctest.h>

#include "baseline/Car.h"
#include "baseline/MessageHeader.h"

using namespace baseline;

std::size_t encodeMessageHeader(MessageHeader& header) noexcept {
  header.field<"blockLength">().setValue(Car::sbeBlockLength());
  header.field<"templateId">().setValue(Car::sbeTemplateId());
  header.field<"schemaId">().setValue(Car::sbeSchemaId());
  header.field<"version">().setValue(Car::sbeSchemaVersion());
  return header.encodedLength();
}

TEST_CASE("MessageHeader") {
  std::array<std::byte, 4096> storage;

  {
    MessageHeader header(storage.data(), storage.size());

    CHECK(encodeMessageHeader(header) == 8);
    CHECK(header.field<"blockLength">().value() == Car::sbeBlockLength());
    CHECK(header.field<"templateId">().value() == Car::sbeTemplateId());
    CHECK(header.field<"schemaId">().value() == Car::sbeSchemaId());
    CHECK(header.field<"version">().value() == Car::sbeSchemaVersion());
  }

  {
    MessageHeader header(storage.data(), 0, storage.size(), Car::sbeSchemaVersion());

    CHECK(encodeMessageHeader(header) == 8);
    CHECK(header.field<"blockLength">().value() == Car::sbeBlockLength());
    CHECK(header.field<"templateId">().value() == Car::sbeTemplateId());
    CHECK(header.field<"schemaId">().value() == Car::sbeSchemaId());
    CHECK(header.field<"version">().value() == Car::sbeSchemaVersion());
  }
}
