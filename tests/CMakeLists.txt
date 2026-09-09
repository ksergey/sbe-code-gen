file(GLOB Sources "${CMAKE_CURRENT_SOURCE_DIR}/*.cpp")

SbeMakeCodec(spot_3_1
    SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/../resources/spot_3_1.xml
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/spot_3_1
    GENERATOR cpp-min
)

SbeMakeCodec(all_types
    SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/../resources/all_types_1_0.xml
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/all_types
    GENERATOR cpp-min
)

SbeMakeCodec(all_types_be
    SCHEMA ${CMAKE_CURRENT_SOURCE_DIR}/../resources/all_types_big_endian_1_0.xml
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/all_types_be
    GENERATOR cpp-min
)

# Split sources per codec: every generated schema.h lives in the same-named
# include dir, so each test target may only link the codec it actually uses.
set(SpotSources)
set(AllTypesSources)
set(AllTypesBeSources)
foreach(src IN LISTS Sources)
    if(src MATCHES "all_types_big_endian_test[.]cpp$")
        list(APPEND AllTypesBeSources ${src})
    elseif(src MATCHES "all_types_test[.]cpp$")
        list(APPEND AllTypesSources ${src})
    else()
        list(APPEND SpotSources ${src})
    endif()
endforeach()

SbeCodeGenAddTestsFromSourceList(SpotSources
    PREFIX sbe-code-gen
    COMPILE_OPTIONS -Wall -Wextra -g
    LIBS doctest::doctest_with_main spot_3_1
)

SbeCodeGenAddTestsFromSourceList(AllTypesSources
    PREFIX sbe-code-gen
    COMPILE_OPTIONS -Wall -Wextra -g
    LIBS doctest::doctest_with_main all_types
)

SbeCodeGenAddTestsFromSourceList(AllTypesBeSources
    PREFIX sbe-code-gen
    COMPILE_OPTIONS -Wall -Wextra -g
    LIBS doctest::doctest_with_main all_types_be
)

# Python codec tests (test_python_codec.py) are self-contained: at test time
# they generate their own schema.py via `python -m app`, so all they need is
# an interpreter with Jinja2 + pytest installed - the same venv SbeMakeCodec()
# already sets up above for code generation.
#
# `ctest` does not build anything on its own, so a plain
# `add_test(COMMAND ${venv}/bin/python -m pytest ...)` would fail on a clean
# build directory where the venv hasn't been created yet. Split this into two
# tests wired through a CTest fixture: the setup test builds just the
# sbe-code-gen-venv target (creating the venv on demand if needed), and the
# actual pytest run requires that fixture, so `ctest` alone - without a
# separate manual build step - is enough to run both suites.
set(pythonEnvRoot ${PROJECT_BINARY_DIR}/venv)
file(REAL_PATH "${pythonEnvRoot}" pythonEnvRoot)

add_test(
    NAME sbe-code-gen-python-venv-setup
    COMMAND ${CMAKE_COMMAND} --build ${PROJECT_BINARY_DIR} --target sbe-code-gen-venv
)
set_tests_properties(sbe-code-gen-python-venv-setup PROPERTIES
    FIXTURES_SETUP sbe_code_gen_python_venv
)

add_test(
    NAME sbe-code-gen-python-test
    COMMAND ${pythonEnvRoot}/bin/python -m pytest -q ${CMAKE_CURRENT_SOURCE_DIR}/test_python_codec.py
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
)
set_tests_properties(sbe-code-gen-python-test PROPERTIES
    FIXTURES_REQUIRED sbe_code_gen_python_venv
    ENVIRONMENT "SBE_CODE_GEN_PYTHON_CODEC_DIR=${CMAKE_CURRENT_BINARY_DIR}/python-codec-test"
)
