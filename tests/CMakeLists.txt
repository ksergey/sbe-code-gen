include(FetchContent)

if (NOT TARGET doctest::doctest_with_main)
    FetchContent_Declare(doctest
        URL https://github.com/doctest/doctest/archive/refs/tags/v2.4.12.tar.gz
        DOWNLOAD_EXTRACT_TIMESTAMP ON
    )
    FetchContent_MakeAvailable(doctest)
endif()

add_subdirectory(binance EXCLUDE_FROM_ALL)

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
