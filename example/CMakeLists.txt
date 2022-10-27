include(FetchContent)

FetchContent_Declare(fmt
  URL https://github.com/fmtlib/fmt/archive/refs/tags/9.1.0.tar.gz
  DOWNLOAD_EXTRACT_TIMESTAMP ON
)
FetchContent_MakeAvailable(fmt)

SBEMakeCodec(schema
  SCHEMA "${CMAKE_CURRENT_SOURCE_DIR}/../resources/b3-market-data-messages-1.3.1.xml"
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/sbe"
  GENERATOR "cppng"
)

add_executable(example0)
target_compile_features(example0 PRIVATE cxx_std_20)
target_compile_options(example0 PRIVATE -Wall -Wextra -Wattributes -Wpedantic -Wstrict-aliasing -Wcast-align -g)
target_link_libraries(example0 PRIVATE fmt::fmt schema)
target_sources(example0 PRIVATE main.cpp)
