include(FetchContent)

if (NOT TARGET doctest_with_main)
  FetchContent_Declare(doctest
    URL https://github.com/doctest/doctest/archive/refs/tags/v2.4.12.tar.gz
    DOWNLOAD_EXTRACT_TIMESTAMP ON
  )
  FetchContent_MakeAvailable(doctest)
endif()

if (NOT TARGET fmt::fmt)
  FetchContent_Declare(fmt
    URL https://github.com/fmtlib/fmt/archive/refs/tags/11.0.2.tar.gz
    DOWNLOAD_EXTRACT_TIMESTAMP ON
  )
  FetchContent_MakeAvailable(fmt)
endif()

add_subdirectory(binance)
add_subdirectory(real-logic)
