# CMakeLists.txt file for sbnutil

#  This simply copies files into an install directory - there is no build

CMAKE_MINIMUM_REQUIRED (VERSION 3.11)

project(sbnutil VERSION 00.00.05)

# cetbuildtools contains our cmake modules
find_package(cetbuildtools REQUIRED)

# Add any modules from this source necessary for building
##list(APPEND CMAKE_MODULE_PATH
##  ${CMAKE_CURRENT_SOURCE_DIR}/Modules)

include(CetCMakeEnv)

# sbnutil has no architecture dependence
cet_cmake_env( noarch )

# Make sure cetbuildtools is set up (version is minimum)
find_ups_product(cetbuildtools)

# Scripts
add_subdirectory(scripts)

# ups - table and config files
# must be AFTER all other subdirectories
add_subdirectory(ups)

# packaging utility
include(UseCPack)
