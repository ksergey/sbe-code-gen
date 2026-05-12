include(FetchContent)

if (NOT TARGET doctest::doctest_with_main)
    FetchContent_Declare(doctest
        URL https://github.com/doctest/doctest/archive/refs/tags/v2.4.12.tar.gz
        DOWNLOAD_EXTRACT_TIMESTAMP ON
    )
    FetchContent_MakeAvailable(doctest)
endif()

if (NOT TARGET fmt::fmt)
    FetchContent_Declare(fmt
        URL https://github.com/fmtlib/fmt/archive/refs/tags/12.1.0.tar.gz
        DOWNLOAD_EXTRACT_TIMESTAMP ON
    )
    FetchContent_MakeAvailable(fmt)
endif()

if (NOT TARGET nlohmann_json::nlohmann_json)
    FetchContent_Declare(json
        URL https://github.com/nlohmann/json/archive/refs/tags/v3.12.0.tar.gz
        DOWNLOAD_EXTRACT_TIMESTAMP ON
    )
    FetchContent_MakeAvailable(json)
endif()

add_subdirectory(binance)

file(GLOB Sources "${CMAKE_CURRENT_SOURCE_DIR}/*.cpp")

sbe_make_codec(spot_3_1
    SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/../resources/spot_3_1.xml
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/spot_3_1
    GENERATOR cpp-min
)

SbeCodeGenAddTestsFromSourceList(Sources
    PREFIX sbe-code-gen
    COMPILE_OPTIONS -Wall -Wextra -g
    LIBS doctest::doctest_with_main spot_3_1
)
