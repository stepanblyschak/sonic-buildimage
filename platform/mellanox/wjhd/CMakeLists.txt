cmake_minimum_required(VERSION 3.2)

project(wjhd)

add_compile_options(-std=c++17)
add_compile_options(-ggdb3)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")

find_library(Tins NAMES libtins.a)
find_library(Fort NAMES libfort.a)

add_executable(wjhd
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wjhdmain.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wjhdaemon.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wjhdaemon.h
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wjhchannel.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wjhchannel.h
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wjhtypes.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wjhtypes.h
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wjhcallback.h
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wjhtable.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/ifnamecache.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/ifnamecache.h
    ${CMAKE_CURRENT_SOURCE_DIR}/src/netdb.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/netdb.h
    ${CMAKE_CURRENT_SOURCE_DIR}/src/usock.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/usock.h
)

target_include_directories(wjhd PUBLIC "/usr/include/libnl3")

add_executable(wjhcli
    ${CMAKE_CURRENT_SOURCE_DIR}/src/wjhcli.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/usock.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/usock.h
)

target_link_libraries(wjhd
    wjh
    sxcore
    sxapi
    scew
    sxaclhelper
    sxadviser
    ${Tins}
    ${Fort}
    swsscommon
)

target_link_libraries(wjhcli
    swsscommon
)

install(TARGETS wjhd wjhcli DESTINATION /usr/bin/)
