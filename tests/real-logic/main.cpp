// Copyright (c) Sergey Kovalevich <inndie@gmail.com>
// SPDX-License-Identifier: AGPL-3.0

#include <fmt/format.h>

#include "baseline/Car.h"
#include "baseline/MessageHeader.h"

int main([[maybe_unused]] int argc, [[maybe_unused]] char* argv[]) {
  try {

  } catch (std::exception const& e) {
    fmt::print(stderr, "ERROR: {}\n", e.what());
    return EXIT_FAILURE;
  }
  return EXIT_SUCCESS;
}
