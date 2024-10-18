cmake_minimum_required(VERSION 3.14)

project(sbe-code-gen)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(cppCodeGenRoot ${CMAKE_CURRENT_SOURCE_DIR})
set(pythonEnvPath ${CMAKE_CURRENT_BINARY_DIR}/venv)
set(pythonEnv ${pythonEnvPath}/bin/python)

add_custom_command(
  OUTPUT ${pythonEnv}
  COMMAND ${Python3_EXECUTABLE} -m venv ${pythonEnvPath}
  COMMAND ${pythonEnv} -m pip install --upgrade pip
  COMMAND ${pythonEnv} -m pip install -r ${CMAKE_CURRENT_SOURCE_DIR}/requirements.txt
  COMMENT "creating python virtualenv at ${pythonEnvPath}"
)

function(sbe_make_codec TARGET)
  set(options)
  set(oneValueArgs SCHEMA OUTPUT GENERATOR INCLUDE_BASE)
  set(multiValueArgs)

  cmake_parse_arguments(PARSED "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  if (PARSED_INCLUDE_BASE)
    set(destDir "${PARSED_OUTPUT}/${PARSED_INCLUDE_BASE}")
  else()
    set(destDir "${PARSED_OUTPUT}")
  endif()

  add_custom_command(
    OUTPUT ${destDir}/schema.h
    DEPENDS ${PARSED_SCHEMA} ${pythonEnv}
    COMMAND ${CMAKE_COMMAND} -E rm -rf "${PARSED_OUTPUT}"
    COMMAND ${pythonEnv} -m app --schema="${PARSED_SCHEMA}" --destination="${destDir}" --generator="${PARSED_GENERATOR}"
    WORKING_DIRECTORY ${cppCodeGenRoot}
    COMMENT "generating schema (${PARSED_SCHEMA})"
  )

  add_library(${TARGET} INTERFACE)
  target_compile_features(${TARGET} INTERFACE cxx_std_20)
  target_sources(${TARGET} INTERFACE ${destDir}/schema.h)
  target_include_directories(${TARGET} INTERFACE "${PARSED_OUTPUT}")
endfunction()

enable_testing()

add_subdirectory(tests EXCLUDE_FROM_ALL)
add_subdirectory(example EXCLUDE_FROM_ALL)
