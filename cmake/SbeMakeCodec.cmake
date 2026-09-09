include(CMakeParseArguments)

# SbeMakeCodec(<target>
#     SCHEMA <path-to-schema.xml>
#     OUTPUT <output-dir>
#     [GENERATOR <cpp-min|cpp>]     # default: cpp-min
#     [INCLUDE_BASE <subdir>]       # generated headers go to OUTPUT/INCLUDE_BASE
#     [PACKAGE <name>]              # override schema package property
# )
#
# Generates an SBE message codec from an XML schema and exposes it as an
# INTERFACE library <target> with the generated schema.h precompiled.
#
# The python virtualenv used to run the generator is created once per
# top-level project (under ${PROJECT_BINARY_DIR}/venv), regardless of how
# many times or from which subdirectory SbeMakeCodec() is called.
function(SbeMakeCodec TARGET)
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

    if (NOT PARSED_GENERATOR)
        set(PARSED_GENERATOR cpp-min)
    endif()

    set(cppCodegenRoot ${CMAKE_CURRENT_FUNCTION_LIST_DIR}/..)
    set(pythonEnvRoot ${PROJECT_BINARY_DIR}/venv)
    set(pythonEnvExe ${PROJECT_BINARY_DIR}/venv/bin/python)

    # Setup venv once per top-level project, no matter how many times or from
    # which subdirectory SbeMakeCodec() is called.
    if (NOT TARGET sbe-code-gen-venv)
        add_custom_command(
            OUTPUT ${pythonEnvExe} ${pythonEnvRoot}/pyvenv.cfg
            COMMAND ${Python3_EXECUTABLE} -m venv ${pythonEnvRoot}
            COMMAND ${pythonEnvExe} -m pip install --upgrade pip
            COMMAND ${pythonEnvExe} -m pip install -r ${cppCodegenRoot}/requirements.txt
            COMMENT "Creating python virtualenv at ${pythonEnvRoot}"
        )
        add_custom_target(sbe-code-gen-venv DEPENDS ${pythonEnvExe} ${pythonEnvRoot}/pyvenv.cfg)
    endif()

    add_custom_command(
        OUTPUT ${destDir}/schema.h
        DEPENDS ${PARSED_SCHEMA} sbe-code-gen-venv
        COMMAND ${CMAKE_COMMAND} -E rm -rf "${PARSED_OUTPUT}"
        COMMAND ${pythonEnvExe} -m app --schema="${PARSED_SCHEMA}" --destination="${destDir}" --generator="${PARSED_GENERATOR}" ${extraArgs}
        WORKING_DIRECTORY ${cppCodegenRoot}
        COMMENT "Generating schema (${PARSED_SCHEMA})"
    )

    add_library(${TARGET} INTERFACE EXCLUDE_FROM_ALL)
    target_compile_features(${TARGET} INTERFACE cxx_std_23)
    target_sources(${TARGET} INTERFACE ${destDir}/schema.h)
    target_include_directories(${TARGET} INTERFACE "${PARSED_OUTPUT}")
    target_precompile_headers(${TARGET} INTERFACE ${destDir}/schema.h)
endfunction()
