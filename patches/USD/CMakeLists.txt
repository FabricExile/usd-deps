project(usd)

set(CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake/defaults
                      ${CMAKE_SOURCE_DIR}/cmake/modules
                      ${CMAKE_SOURCE_DIR}/cmake/macros)

if (WIN32)
    cmake_minimum_required(VERSION 3.1.1)
else()
    cmake_minimum_required(VERSION 2.8.8)
endif()

# if(MSVC)
#     set(Boost_USE_MULTITHREADED ON)
#     set(Boost_USE_STATIC_LIBS ON)
#     set(Boost_USE_STATIC_RUNTIME ON)
# endif()

# --Python
find_package(PythonLibs 2.7 REQUIRED)

# # --Boost
# find_package(Boost
#     COMPONENTS
#         date_time
#         iostreams
#         program_options
#         python
#         regex
#         system
#     REQUIRED
# )
# add_definitions(${BOOST_DEFINITIONS})
add_definitions(-DBOOST_ALL_NO_LIB)
include_directories(${BOOST_INCLUDEDIR})


# --TBB
find_package(TBB REQUIRED)
add_definitions(${TBB_DEFINITIONS})

# --OpenEXR
find_package(OpenEXR REQUIRED)

# --pthread
find_package(Threads REQUIRED)

# additional includes
include_directories(
  ${CMAKE_BINARY_DIR}/include
  ${CMAKE_SOURCE_DIR}
  ${Boost_INCLUDE_DIRS}
  ${PYTHON_INCLUDE_DIRS}
  ${TBB_INCLUDE_DIRS}
  ${ILMBASE_INCLUDE_DIR}/Half
)

set(CMAKE_INCLUDE_CURRENT_DIR ON)
set(PXR_USE_NAMESPACES, off)

# setup config file
include(Version)
configure_file(
    ${CMAKE_SOURCE_DIR}/pxr/pxr.h.in
    ${CMAKE_BINARY_DIR}/include/pxr/pxr.h     
)

# append additional includes to pxr.h
if (WIN32)
add_definitions(-DNOMINMAX)
FILE(APPEND ${CMAKE_BINARY_DIR}/include/pxr/pxr.h "
#include <algorithm>
#include <io.h>
")
endif()

# defines
add_definitions(-DBUILD_OPTLEVEL_OPT)
add_definitions(-DBUILD_COMPONENT_SRC_PREFIX="")
if (WIN32)
    add_definitions(-DTF_NO_GNU_EXT)
    add_definitions(-DYY_NO_UNISTD_H)
endif()

# library specific
add_definitions(-DARCH_STATIC)
add_definitions(-DGF_STATIC)
add_definitions(-DJS_STATIC)
add_definitions(-DPLUG_STATIC)
add_definitions(-DTF_STATIC)
add_definitions(-DTRACELITE_STATIC)
add_definitions(-DVT_STATIC)
add_definitions(-DWORK_STATIC)
add_definitions(-DAR_STATIC)
add_definitions(-DKIND_STATIC)
add_definitions(-DPCP_STATIC)
add_definitions(-DSDF_STATIC)
add_definitions(-DUSD_STATIC)
add_definitions(-DUSDGEOM_STATIC)
add_definitions(-DUSDHYDRA_STATIC)
add_definitions(-DUSDRI_STATIC)
add_definitions(-DUSDSHADE_STATIC)
add_definitions(-DUSDUI_STATIC)
add_definitions(-DUSDUTILS_STATIC)

# find sources
FILE(GLOB SOURCES
  ${CMAKE_SOURCE_DIR}/pxr/base/lib/arch/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/base/lib/gf/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/base/lib/js/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/base/lib/plug/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/base/lib/tf/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/base/lib/tracelite/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/base/lib/vt/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/base/lib/work/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/usd/lib/ar/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/usd/lib/kind/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/usd/lib/pcp/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/usd/lib/sdf/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/usd/lib/usd/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/usd/lib/usdGeom/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/usd/lib/usdHydra/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/usd/lib/usdRi/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/usd/lib/usdShade/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/usd/lib/usdUI/*.cpp
  ${CMAKE_SOURCE_DIR}/pxr/usd/lib/usdUtils/*.cpp
)

# filter out all template files
LIST(FILTER SOURCES EXCLUDE REGEX \.template\.)
# filter out the boost::python wrap files
LIST(FILTER SOURCES EXCLUDE REGEX \/wrap)
# filter out the examples cpp files
LIST(FILTER SOURCES EXCLUDE REGEX \/examples\.cpp)
# # filter out all of the module related cpp files
# LIST(FILTER SOURCES EXCLUDE REGEX \/module\.cpp)
# LIST(FILTER SOURCES EXCLUDE REGEX \/moduleDeps\.cpp)
# LIST(FILTER SOURCES EXCLUDE REGEX \/debugCodes\.cpp)
# LIST(FILTER SOURCES EXCLUDE REGEX \/notice\.cpp)

# library
add_library(usd_static
    STATIC

    ${SOURCES}
)
