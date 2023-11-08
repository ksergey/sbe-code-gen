cmake_minimum_required(VERSION 3.14)

project(sbe-code-gen)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(cppCodeGenRoot ${CMAKE_CURRENT_SOURCE_DIR})
set(pythonEnvPath ${CMAKE_CURRENT_BINARY_DIR}/venv)
set(pythonEnv ${pythonEnvPath}/bin/python)

add_custom_command(
  OUTPUT ${pythonEnv}
  COMMAND ${Python3_EXECUTABLE} -m venv ${pythonEnvPath}
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/requirements.txt
  COMMAND ${pythonEnv} -m pip install --upgrade pip
  COMMAND ${pythonEnv} -m pip install -r ${CMAKE_CURRENT_SOURCE_DIR}/requirements.txt
)
add_custom_target(venv DEPENDS ${pythonEnv})

function(SBEMakeCodec TARGET)
  set(options)
  set(oneValueArgs SCHEMA OUTPUT GENERATOR)
  set(multiValueArgs)

  cmake_parse_arguments(PARSED "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  add_custom_command(
    OUTPUT ${PARSED_OUTPUT}/schema.h
    DEPENDS ${PARSED_SCHEMA} venv
    COMMAND ${pythonEnv} -m app --schema="${PARSED_SCHEMA}" --destination="${PARSED_OUTPUT}" --generator="${PARSED_GENERATOR}"
    WORKING_DIRECTORY ${cppCodeGenRoot}
    COMMENT "generating schema (${PARSED_SCHEMA})"
  )

  add_library(${TARGET} INTERFACE)
  target_compile_features(${TARGET} INTERFACE cxx_std_20)
  target_sources(${TARGET} INTERFACE ${PARSED_OUTPUT}/schema.h)
  target_include_directories(${TARGET} INTERFACE "${PARSED_OUTPUT}")
endfunction()

add_subdirectory(tests EXCLUDE_FROM_ALL)
add_subdirectory(example EXCLUDE_FROM_ALL)
