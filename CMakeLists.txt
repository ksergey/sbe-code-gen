cmake_minimum_required(VERSION 3.19)

project(sbe-code-gen)

option(sbe_code_gen_BUILD_TESTS "Build tests (*_test.cpp files, linked against doctest)" ON)

include(cmake/Utils.cmake)
include(cmake/GetCPM.cmake)
include(cmake/SbeMakeCodec.cmake)

if (sbe_code_gen_BUILD_TESTS)
    enable_testing()
    CPMAddPackage("gh:doctest/doctest@2.5.2")
    add_subdirectory(tests)
endif()
