cmake_minimum_required(VERSION 3.14)

project(sbe-code-gen)

find_package(PythonInterp 3.4 REQUIRED)

set(CPP_CODE_GEN_ROOT ${CMAKE_CURRENT_SOURCE_DIR})

function(SBEMakeCodec TARGET)
  set(options)
  set(oneValueArgs SCHEMA OUTPUT GENERATOR)
  set(multiValueArgs)

  cmake_parse_arguments(PARSED "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  add_custom_command(
    OUTPUT ${PARSED_OUTPUT}/schema.h
    COMMAND ${PYTHON_EXECUTABLE} -m app --schema="${PARSED_SCHEMA}" --destination="${PARSED_OUTPUT}" --generator="${PARSED_GENERATOR}"
    DEPENDS ${PARSED_SCHEMA}
    WORKING_DIRECTORY ${CPP_CODE_GEN_ROOT}
    COMMENT "generating schema (${PARSED_SCHEMA})"
  )

  add_library(${TARGET} INTERFACE)
  target_compile_features(${TARGET} INTERFACE cxx_std_20)
  target_sources(${TARGET} PUBLIC ${PARSED_OUTPUT}/schema.h)
  target_include_directories(${TARGET} INTERFACE "${PARSED_OUTPUT}")
endfunction()

add_custom_target(InstallRequirements
  COMMAND ${PYTHON_EXECUTABLE} -m pip install -r requirements.txt
  WORKING_DIRECTORY ${CPP_CODE_GEN_ROOT}
  COMMENT install requirements
)

add_subdirectory(tests EXCLUDE_FROM_ALL)
add_subdirectory(example EXCLUDE_FROM_ALL)
