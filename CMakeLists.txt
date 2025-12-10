cmake_minimum_required(VERSION 3.14)

project(sbe-code-gen)

function(sbe_make_codec TARGET)
  set(options)
  set(oneValueArgs SCHEMA OUTPUT GENERATOR INCLUDE_BASE PACKAGE)
  set(multiValueArgs)

  cmake_parse_arguments(PARSED "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

  find_package(Python3 COMPONENTS Interpreter REQUIRED)

  if (PARSED_INCLUDE_BASE)
    set(destDir "${PARSED_OUTPUT}/${PARSED_INCLUDE_BASE}")
  else()
    set(destDir "${PARSED_OUTPUT}")
  endif()

  set(extraArgs)
  if (PARSED_PACKAGE)
    set(extraArgs ${extraArgs} --package="${PARSED_PACKAGE}")
  endif()

  set(cppCodegenRoot ${CMAKE_CURRENT_FUNCTION_LIST_DIR})
  set(pythonEnvRoot ${CMAKE_CURRENT_BINARY_DIR}/venv)
  set(pythonEnvExe ${CMAKE_CURRENT_BINARY_DIR}/venv/bin/python)

  # Setup venv
  add_custom_command(
    OUTPUT ${pythonEnvExe} ${pythonEnvRoot}/pyvenv.cfg
    COMMAND ${Python3_EXECUTABLE} -m venv ${pythonEnvRoot}
    COMMAND ${pythonEnvExe} -m pip install --upgrade pip
    COMMAND ${pythonEnvExe} -m pip install -r ${cppCodegenRoot}/requirements.txt
    COMMENT "Creating python virtualenv at ${pythonEnvRoot}"
  )

  add_custom_command(
    OUTPUT ${destDir}/schema.h
    DEPENDS ${PARSED_SCHEMA} ${pythonEnvRoot}/pyvenv.cfg
    COMMAND ${CMAKE_COMMAND} -E rm -rf "${PARSED_OUTPUT}"
    COMMAND ${pythonEnvExe} -m app --schema="${PARSED_SCHEMA}" --destination="${destDir}" --generator="${PARSED_GENERATOR}" ${extraArgs}
    WORKING_DIRECTORY ${cppCodegenRoot}
    COMMENT "Generating schema (${PARSED_SCHEMA})"
  )

  add_library(${TARGET} INTERFACE EXCLUDE_FROM_ALL)
  target_compile_features(${TARGET} INTERFACE cxx_std_20)
  target_sources(${TARGET} INTERFACE ${destDir}/schema.h)
  target_include_directories(${TARGET} INTERFACE "${PARSED_OUTPUT}")
endfunction()

enable_testing()

add_subdirectory(tests EXCLUDE_FROM_ALL)
add_subdirectory(example EXCLUDE_FROM_ALL)
