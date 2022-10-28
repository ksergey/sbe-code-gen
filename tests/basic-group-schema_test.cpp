// ------------------------------------------------------------
// Copyright 2022-present Sergey Kovalevich <inndie@gmail.com>
// ------------------------------------------------------------

#include <doctest/doctest.h>

#include "TestMessage1.h"

using namespace SBE_tests;

TEST_CASE("basic-group-schema-test") {
  REQUIRE_EQ(TestMessage1::name(), "TestMessage1");
  REQUIRE_EQ(TestMessage1::id(), 1);
  REQUIRE_EQ(TestMessage1::sbeBlockLength(), 16);
  REQUIRE_EQ(TestMessage1::fieldsCount(), 2);
  REQUIRE_EQ(TestMessage1::Entries::sbeBlockLength(), 28);
  REQUIRE_EQ(TestMessage1::Entries::fieldsCount(), 2);
}
