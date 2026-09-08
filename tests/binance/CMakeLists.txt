CPMAddPackage("gh:fmtlib/fmt#12.1.0")
CPMAddPackage("gh:nlohmann/json@3.12.0")

SbeMakeCodec(spot_2_0
    SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/../../resources/spot_3_1.xml
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/spot_3_1
    GENERATOR cpp-min
)

set(Target binance)
add_executable(${Target} main.cpp)
target_compile_features(${Target} PRIVATE cxx_std_20)
target_compile_options(${Target} PRIVATE -Wall -Wextra)
target_link_libraries(${Target} PRIVATE spot_2_0 nlohmann_json::nlohmann_json)
