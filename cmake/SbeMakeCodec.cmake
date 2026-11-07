# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

include(CMakeParseArguments)

# Internal: set up the python virtualenv used to run the generator, once per
# build tree (under ${PROJECT_BINARY_DIR}/venv of the project that calls it
# first), no matter how many times, from which subdirectory or from which
# project a SbeMakeCodec()/SbeMakeCodecBundle() runs. Creates the
# "sbe-code-gen-venv" target and stores the interpreter path in its
# SBE_CODE_GEN_PYTHON property; sets SBE_CODE_GEN_PYTHON_EXE in the caller's
# scope on return.
function(_SbeCodeGenEnsurePythonVenv CodegenRoot)
    if (NOT TARGET sbe-code-gen-venv)
        set(pythonEnvRoot ${PROJECT_BINARY_DIR}/venv)
        set(pythonEnvExe ${pythonEnvRoot}/bin/python)
        add_custom_command(
            OUTPUT ${pythonEnvExe} ${pythonEnvRoot}/pyvenv.cfg
            COMMAND ${Python3_EXECUTABLE} -m venv ${pythonEnvRoot}
            COMMAND ${pythonEnvExe} -m pip install --upgrade pip
            COMMAND ${pythonEnvExe} -m pip install -r ${CodegenRoot}/requirements.txt
            WORKING_DIRECTORY ${CodegenRoot}
            COMMENT "Creating python virtualenv at ${pythonEnvRoot}"
        )
        add_custom_target(sbe-code-gen-venv DEPENDS ${pythonEnvExe} ${pythonEnvRoot}/pyvenv.cfg)
        set_property(TARGET sbe-code-gen-venv PROPERTY SBE_CODE_GEN_PYTHON ${pythonEnvExe})
    endif()
    get_property(pythonEnvExe TARGET sbe-code-gen-venv PROPERTY SBE_CODE_GEN_PYTHON)
    set(SBE_CODE_GEN_PYTHON_EXE ${pythonEnvExe} PARENT_SCOPE)
endfunction()

# Internal: template file list of a generator, used as regeneration deps
function(_SbeCodeGenTemplateDeps CodegenRoot Generator outVar)
    file(GLOB _tplDeps CONFIGURE_DEPENDS
        "${CodegenRoot}/app/generation/${Generator}/templates/*"
        "${CodegenRoot}/app/generation/${Generator}/generator.py")
    set(${outVar} "${_tplDeps}" PARENT_SCOPE)
endfunction()

# SbeMakeCodec(<target>
#     SCHEMA <path-to-schema.xml>
#     OUTPUT <output-dir>
#     [GENERATOR <cpp-min|cpp|cpp-split>] # default: cpp-min
#     [INCLUDE_BASE <subdir>]       # generated headers go to OUTPUT/INCLUDE_BASE
#     [PACKAGE <name>]              # override schema package property
#     [SCHEMA_DEPS <files...>]      # extra regeneration inputs (e.g. xi:include'd shared types)
# )
#
# Generates an SBE message codec from an XML schema and exposes it as an
# INTERFACE library <target> with the generated schema.h precompiled.
function(SbeMakeCodec TARGET)
    set(options)
    set(oneValueArgs SCHEMA OUTPUT GENERATOR INCLUDE_BASE PACKAGE)
    set(multiValueArgs SCHEMA_DEPS)

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

    get_filename_component(cppCodegenRoot "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/.." ABSOLUTE)

    _SbeCodeGenEnsurePythonVenv(${cppCodegenRoot})
    _SbeCodeGenTemplateDeps(${cppCodegenRoot} ${PARSED_GENERATOR} templateDeps)

    add_custom_command(
        OUTPUT ${destDir}/schema.h
        DEPENDS ${PARSED_SCHEMA} ${PARSED_SCHEMA_DEPS} ${templateDeps} sbe-code-gen-venv
        COMMAND ${CMAKE_COMMAND} -E rm -rf "${PARSED_OUTPUT}"
        COMMAND ${SBE_CODE_GEN_PYTHON_EXE} -m app --schema="${PARSED_SCHEMA}" --destination="${destDir}" --generator="${PARSED_GENERATOR}" ${extraArgs}
        WORKING_DIRECTORY ${cppCodegenRoot}
        COMMENT "Generating schema (${PARSED_SCHEMA})"
    )

    add_library(${TARGET} INTERFACE EXCLUDE_FROM_ALL)
    target_compile_features(${TARGET} INTERFACE cxx_std_23)
    target_sources(${TARGET} INTERFACE ${destDir}/schema.h)
    target_include_directories(${TARGET} INTERFACE "${PARSED_OUTPUT}")
    target_precompile_headers(${TARGET} INTERFACE ${destDir}/schema.h)
endfunction()

# SbeMakeCodecBundle(<target>
#     PACKAGES <p1;p2;...>
#     SCHEMAS <path1;path2;...>     # same count as PACKAGES
#     OUTPUT <output-dir>
#     [INCLUDE_BASE <subdir>]       # schema headers go to OUTPUT/INCLUDE_BASE/<package>/schema.h
#     [GENERATOR <cpp-split>]       # only cpp-split supports bundle generation
#     [SCHEMA_DEPS <files...>]      # extra regeneration inputs (e.g. xi:include'd shared types)
# )
#
# Bundle generation: run the generator once for several schemas into a single
# destination, so types shared through xi:include become fragment headers
# emitted once and used by every schema of the bundle -- a translation unit
# that uses two schemas of the bundle sees one shared copy of those types.
#
# For every package <p> an INTERFACE library <target>-<p>-sbe is created
# (with alias <target>::<p>-sbe) exposing its schema header. Every library
# adds ${OUTPUT} and ${OUTPUT}/${INCLUDE_BASE} to its include directories:
# with INCLUDE_BASE=<base> a schema header is included as "<base>/<p>/schema.h"
# while the shared support/fragment headers (${OUTPUT}/<base>/support.h, ...)
# resolve as "support.h"/"<stem>.h" from the schema headers.
function(SbeMakeCodecBundle TARGET)
    set(options)
    set(oneValueArgs OUTPUT INCLUDE_BASE GENERATOR)
    set(multiValueArgs PACKAGES SCHEMAS SCHEMA_DEPS)

    cmake_parse_arguments(PARSED "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    find_package(Python3 COMPONENTS Interpreter REQUIRED)

    if (NOT PARSED_GENERATOR)
        set(PARSED_GENERATOR cpp-split)
    endif()

    list(LENGTH PARSED_PACKAGES packageCount)
    list(LENGTH PARSED_SCHEMAS schemaCount)
    if (NOT packageCount EQUAL schemaCount)
        message(FATAL_ERROR "SbeMakeCodecBundle(): PACKAGES and SCHEMAS must have the same length")
    endif()

    if (PARSED_INCLUDE_BASE)
        set(destDir "${PARSED_OUTPUT}/${PARSED_INCLUDE_BASE}")
    else()
        set(destDir "${PARSED_OUTPUT}")
    endif()

    get_filename_component(cppCodegenRoot "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/.." ABSOLUTE)

    _SbeCodeGenEnsurePythonVenv(${cppCodegenRoot})
    _SbeCodeGenTemplateDeps(${cppCodegenRoot} ${PARSED_GENERATOR} templateDeps)

    set(schemaHeaderOutputs)
    foreach(package ${PARSED_PACKAGES})
        list(APPEND schemaHeaderOutputs "${destDir}/${package}/schema.h")
    endforeach()

    set(schemaArgs)
    foreach(schema ${PARSED_SCHEMAS})
        list(APPEND schemaArgs --schema="${schema}")
    endforeach()

    add_custom_command(
        OUTPUT ${schemaHeaderOutputs}
        DEPENDS ${PARSED_SCHEMAS} ${PARSED_SCHEMA_DEPS} ${templateDeps} sbe-code-gen-venv
        COMMAND ${CMAKE_COMMAND} -E rm -rf "${PARSED_OUTPUT}"
        COMMAND ${SBE_CODE_GEN_PYTHON_EXE} -m app ${schemaArgs} --bundle --destination="${destDir}" --generator="${PARSED_GENERATOR}"
        WORKING_DIRECTORY ${cppCodegenRoot}
        COMMENT "Generating schema bundle (${PARSED_GENERATOR})"
    )

    math(EXPR lastPackageIndex "${packageCount} - 1")
    foreach(packageIndex RANGE ${lastPackageIndex})
        list(GET PARSED_PACKAGES ${packageIndex} package)
        list(GET schemaHeaderOutputs ${packageIndex} schemaHeader)
        set(codecTarget "${TARGET}-${package}-sbe")

        add_library(${codecTarget} INTERFACE EXCLUDE_FROM_ALL)
        target_compile_features(${codecTarget} INTERFACE cxx_std_23)
        target_sources(${codecTarget} INTERFACE ${schemaHeader})
        # ${destDir} holds the shared support/fragment headers (included as
        # "support.h"/"<stem>.h" from the schema headers); ${PARSED_OUTPUT}
        # makes "<INCLUDE_BASE>/<package>/schema.h" resolvable for consumers
        target_include_directories(${codecTarget} INTERFACE "${destDir}" "${PARSED_OUTPUT}")
        target_precompile_headers(${codecTarget} INTERFACE ${schemaHeader})
        add_library(${TARGET}::${package}-sbe ALIAS ${codecTarget})
    endforeach()
endfunction()
