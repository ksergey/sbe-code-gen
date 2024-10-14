include(FetchContent)

if (NOT TARGET doctest_with_main)
  FetchContent_Declare(doctest
    URL https://github.com/doctest/doctest/archive/refs/tags/v2.4.11.tar.gz
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

enable_testing()

SBEMakeCodec(basic-group-schema
  SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/basic-group-schema.xml
  OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/basic-group-schema
  GENERATOR cppng
)

set(Target basic-group-schema_test)
add_executable(${Target} basic-group-schema_test.cpp)
target_compile_features(${Target} PRIVATE cxx_std_20)
target_compile_options(${Target} PRIVATE -Wall -Wextra)
target_link_libraries(${Target} PRIVATE doctest_with_main basic-group-schema)
add_test(${Target} ${Target})

SBEMakeCodec(spot_2_0
  SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/../resources/spot_2_0.xml
  OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/spot_2_0
  GENERATOR cppng
)

set(Target Binance_exchangeInfo_test)
add_executable(${Target} Binance_exchangeInfo_test.cpp)
target_compile_features(${Target} PRIVATE cxx_std_20)
target_compile_options(${Target} PRIVATE -Wall -Wextra)
target_link_libraries(${Target} PRIVATE doctest_with_main fmt::fmt spot_2_0)
add_test(${Target} ${Target})
