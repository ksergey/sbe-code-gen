cmake_minimum_required(VERSION 3.14)

project(sbe-code-gen)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(cppCodeGenRoot ${CMAKE_CURRENT_SOURCE_DIR})
set(pythonEnv ${CMAKE_CURRENT_BINARY_DIR}/venv)
set(pythonExe ${pythonEnv}/bin/python)

add_custom_command(
  OUTPUT ${pythonExe} ${pythonEnv}/pyvenv.cfg
  COMMAND ${Python3_EXECUTABLE} -m venv ${pythonEnv}
  COMMAND ${pythonExe} -m pip install --upgrade pip
  COMMAND ${pythonExe} -m pip install -r ${CMAKE_CURRENT_SOURCE_DIR}/requirements.txt
  COMMENT "creating python virtualenv at ${pythonEnv}"
)
add_custom_target(python_venv DEPENDS ${pythonEnv}/pyvenv.cfg)

function(sbe_make_codec TARGET)
  set(options)
  set(oneValueArgs SCHEMA OUTPUT GENERATOR INCLUDE_BASE PACKAGE)
  set(multiValueArgs)

  cmake_parse_arguments(PARSED "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  if (PARSED_INCLUDE_BASE)
    set(destDir "${PARSED_OUTPUT}/${PARSED_INCLUDE_BASE}")
  else()
    set(destDir "${PARSED_OUTPUT}")
  endif()

  set(extraArgs)
  if (PARSED_PACKAGE)
    set(extraArgs ${extraArgs} --package="${PARSED_PACKAGE}")
  endif()

  add_custom_command(
    OUTPUT ${destDir}/schema.h
    DEPENDS ${PARSED_SCHEMA} python_venv
    COMMAND ${CMAKE_COMMAND} -E rm -rf "${PARSED_OUTPUT}"
    COMMAND ${pythonExe} -m app --schema="${PARSED_SCHEMA}" --destination="${destDir}" --generator="${PARSED_GENERATOR}" ${extraArgs}
    WORKING_DIRECTORY "${cppCodeGenRoot}"
    COMMENT "generating schema (${PARSED_SCHEMA})"
  )

  add_library(${TARGET} INTERFACE EXCLUDE_FROM_ALL)
  target_compile_features(${TARGET} INTERFACE cxx_std_20)
  target_sources(${TARGET} INTERFACE ${destDir}/schema.h)
  target_include_directories(${TARGET} INTERFACE "${PARSED_OUTPUT}")
endfunction()

enable_testing()

add_subdirectory(tests EXCLUDE_FROM_ALL)
add_subdirectory(example EXCLUDE_FROM_ALL)
