sbe_make_codec(spot_2_0
  SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/../../resources/spot_2_0.xml
  OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/spot_2_0
  GENERATOR cppng
)

set(Target binance)
add_executable(${Target} main.cpp)
target_compile_features(${Target} PRIVATE cxx_std_20)
target_compile_options(${Target} PRIVATE -Wall -Wextra)
target_link_libraries(${Target} PRIVATE doctest_with_main fmt::fmt spot_2_0)
add_test(${Target} ${Target})
