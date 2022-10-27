include(FetchContent)

FetchContent_Declare(fmt
  URL https://github.com/fmtlib/fmt/archive/refs/tags/9.1.0.tar.gz
  DOWNLOAD_EXTRACT_TIMESTAMP ON
)
FetchContent_MakeAvailable(fmt)

FetchContent_Declare(nlohmann_json
  URL https://github.com/ArthurSonzogni/nlohmann_json_cmake_fetchcontent/archive/v3.11.2.tar.gz
  DOWNLOAD_EXTRACT_TIMESTAMP ON
)
FetchContent_MakeAvailable(nlohmann_json)

SBEMakeCodec(schema
  SCHEMA "${CMAKE_CURRENT_SOURCE_DIR}/../resources/b3-market-data-messages-1.3.1.xml"
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/sbe"
  GENERATOR "cppng"
)

add_executable(example)
target_compile_features(example PRIVATE cxx_std_20)
target_compile_options(example PRIVATE -Wall -Wextra -Wattributes -Wpedantic -Wstrict-aliasing -Wcast-align -g)
target_link_libraries(example PRIVATE fmt::fmt schema)
target_sources(example PRIVATE example.cpp)

add_executable(example_json)
target_compile_features(example_json PRIVATE cxx_std_20)
target_compile_options(example_json PRIVATE -Wall -Wextra -Wattributes -Wpedantic -Wstrict-aliasing -Wcast-align -g)
target_link_libraries(example_json PRIVATE fmt::fmt nlohmann_json::nlohmann_json schema)
target_sources(example_json PRIVATE example_json.cpp)
