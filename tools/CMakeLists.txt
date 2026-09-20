CPMAddPackage("gh:jarro2783/cxxopts@3.3.1")
CPMAddPackage("gh:nlohmann/json@3.12.0")

SbeMakeCodec(sbe::FixBinary
    SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/../resources/FixBinary.xml
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/FixBinary
    INCLUDE_BASE sbe/FixBinary
    PACKAGE FixBinary
)

SbeMakeCodec(sbe::b3-market-data-messages-1.3.1
    SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/../resources/b3-market-data-messages-1.3.1.xml
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/b3-market-data-messages-1.3.1
    INCLUDE_BASE sbe/b3-market-data-messages-1.3.1
    PACKAGE b3_market_data_messages_1_3_1
)

SbeMakeCodec(sbe::spot_2_0
    SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/../resources/spot_2_0.xml
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/spot_2_0
    INCLUDE_BASE sbe/spot_2_0
    PACKAGE spot_2_0
)

SbeMakeCodec(sbe::spot_3_1
    SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/../resources/spot_3_1.xml
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/spot_3_1
    INCLUDE_BASE sbe/spot_3_1
    PACKAGE spot_3_1
)

add_executable(sbe-tool sbe-tool.cpp)
target_compile_features(sbe-tool
    PUBLIC cxx_std_23)
set_target_properties(sbe-tool
    PROPERTIES
        CXX_STANDARD_REQUIRED ON
        CXX_EXTENSIONS OFF
        POSITION_INDEPENDENT_CODE ON)
target_compile_options(sbe-tool
    PRIVATE -Wall -Wextra -Wattributes -Wpedantic -Wstrict-aliasing -Wcast-align -g)
target_compile_definitions(sbe-tool
    PRIVATE -DCXXOPTS_NO_RTTI)
target_link_libraries(sbe-tool
    PRIVATE cxxopts::cxxopts nlohmann_json::nlohmann_json sbe::FixBinary sbe::b3-market-data-messages-1.3.1 sbe::spot_2_0 sbe::spot_3_1)
