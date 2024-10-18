sbe_make_codec(baseline
  SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/example-schema.xml
  OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/sbe
  INCLUDE_BASE baseline
  GENERATOR cppng
)

set(Target real-logic)
add_executable(${Target} main.cpp)
target_compile_features(${Target} PRIVATE cxx_std_20)
target_compile_options(${Target} PRIVATE -Wall -Wextra)
target_link_libraries(${Target} PRIVATE doctest_with_main fmt::fmt baseline)
add_test(${Target} ${Target})
