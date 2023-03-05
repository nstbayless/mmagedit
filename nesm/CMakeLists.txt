cmake_minimum_required(VERSION 3.13)
project(nesm)

include(CheckLibraryExists)
CHECK_LIBRARY_EXISTS(m sin "" HAVE_LIB_M)
if (HAVE_LIB_M)
    set(EXTRA_LIBS ${EXTRA_LIBS} m)
endif (HAVE_LIB_M)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/cmake/sdl2)

find_package(SDL2 REQUIRED)

set(SOURCE_FILES src/main.c src/emu/nes_system.c)
include_directories(src ${SDL2_INCLUDE_DIR})
if (WIN32)
    add_executable(nesm WIN32 ${SOURCE_FILES})
else()
    add_executable(nesm ${SOURCE_FILES})
endif (WIN32)
target_link_libraries(nesm ${SDL2_LIBRARY} ${EXTRA_LIBS})





































