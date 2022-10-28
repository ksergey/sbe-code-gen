include(FetchContent)

FetchContent_Declare(doctest
  URL https://github.com/onqtam/doctest/archive/refs/tags/2.4.6.tar.gz
  DOWNLOAD_EXTRACT_TIMESTAMP ON
)
FetchContent_MakeAvailable(doctest)

function(AddTest NAME)
  set(options)
  set(oneValueArgs SOURCE)
  set(multiValueArgs LIBS)

  cmake_parse_arguments(PARSED "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  add_executable(${NAME} ${PARSED_SOURCE})
  target_compile_options(${NAME} PRIVATE -Wall -Wextra)
  target_link_libraries(${NAME} PRIVATE ${PARSED_LIBS})
  add_test(${NAME} ${NAME})
endfunction()

enable_testing()

SBEMakeCodec(basic-group-schema
  SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/basic-group-schema.xml
  OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/basic-group-schema
  GENERATOR cppng
)

AddTest(basic_group_schema_test
  SOURCE basic-group-schema_test.cpp
  LIBS doctest_with_main basic-group-schema
)
