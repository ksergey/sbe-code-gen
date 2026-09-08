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
