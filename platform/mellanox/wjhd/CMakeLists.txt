cmake_minimum_required(VERSION 3.3)
set (CMAKE_BUILD_TYPE Debug)
enable_language (CXX)
include ("GNUInstallDirs")

project(wjhd)
set (WJHD_MAJOR_VERSION 1)
set (WJHD_MINOR_VERSION 0)
set (WJHD_API_VERSION 0)

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

add_executable(wjhd
	src/wjhchannel.cpp
	src/wjhserialize.cpp
	src/wjhagent.cpp
	src/wjhifnamecache.cpp
	src/main.cpp
)

target_include_directories(wjhd PUBLIC src/)
target_link_libraries(wjhd sxcore sxapi scew sxaclhelper sxadviser tins wjh swsscommon)
