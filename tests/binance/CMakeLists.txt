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

sbe_make_codec(spot_2_0
    SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/../../resources/spot_3_1.xml
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/spot_3_1
    GENERATOR cpp-min
)

set(Target binance)
add_executable(${Target} main.cpp)
target_compile_features(${Target} PRIVATE cxx_std_20)
target_compile_options(${Target} PRIVATE -Wall -Wextra)
target_link_libraries(${Target} PRIVATE spot_2_0 nlohmann_json::nlohmann_json)
add_test(${Target} ${Target})
