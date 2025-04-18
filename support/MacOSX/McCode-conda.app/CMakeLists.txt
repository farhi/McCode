cmake_minimum_required(VERSION 3.17.0)

# This will install the McCode app bundle
project(mcstas-app C)

# Choose between McStas or McXtrace
option(BUILD_MCSTAS   "Choose the McStas flavor" off)
option(BUILD_MCXTRACE "Choose the McXtrace flavor (trumps BUILD_MCSTAS)" Off)

# Set module path
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake/Modules/")

# Set McCode values (from mkdist or defaults)
include(MCUtil)

if (${BUILD_MCXTRACE})
  set(FLAVOR "mcxtrace")
  set(GUIPREFIX "mx")
elseif(${BUILD_MCSTAS})
  set(FLAVOR "mcstas")
  set(GUIPREFIX "mc")
else()
  message(FATAL_ERROR "No flavor specified!\n"
    "Please use either -DBUILD_MCSTAS=1 or -DBUILD_MCXTRACE=1")
endif()

message("Enabling ${FLAVOR} flavor")

if (DEFINED ARCH_ENABLE)
  message("Enabling archictecture ${ARCH_ENABLE}")
  set(SHEBANG "/usr/bin/arch -${ARCH_ENABLE} /usr/bin/env bash")
else()
  message("Auto-detecting archictecture ...")
  if ("${CMAKE_SYSTEM_PROCESSOR}" STREQUAL "arm64" )
    message("Enabling archictecture ${CMAKE_SYSTEM_PROCESSOR}")
    set(SHEBANG "/usr/bin/arch -arm64 /usr/bin/env bash")
  else()
    set(SHEBANG "/usr/bin/env bash")
  endif()
endif()

setupMCCODE("${FLAVOR}")

# CPack configuration
set(CPACK_PACKAGE_NAME          "${FLAVOR}-app-${MCCODE_VERSION}")
set(CPACK_RESOURCE_FilE_LICENSE "${CMAKE_CURRENT_SOURCE_DIR}/../../../COPYING")
set(CPACK_PACKAGE_CONTACT       "pkwi@fysik.dtu.dk")

set(CPACK_PACKAGE_VERSION       "1.0")
set(CPACK_PACKAGE_VERSION_MAJOR "1")
set(CPACK_PACKAGE_VERSION_MINOR "0")

include(CPack)

set(WORK "${PROJECT_BINARY_DIR}/work")

# Configure the .py launcher
configure_file(Contents/MacOS/mccodegui.py.in ${WORK}/mccodegui @ONLY)
configure_file(Contents/MacOS/Miniforge-inject.command.in ${WORK}/Miniforge-inject.command @ONLY)

execute_process(COMMAND "chmod ARGS 755 work/mccodegui")

# Include the Contents subfolder...
install (
  DIRECTORY "Contents/"
  DESTINATION "Contents/"
  PATTERN "Makefile*" EXCLUDE  # skip makefiles
  PATTERN "#*"        EXCLUDE  # skip backup files
  PATTERN ".*"        EXCLUDE  # skip hidden files
  PATTERN "*.out"     EXCLUDE  # skip binary files
  )

install(
    FILES "${WORK}/mccodegui" "${WORK}/Miniforge-inject.command" 
    PERMISSIONS OWNER_EXECUTE OWNER_WRITE OWNER_READ GROUP_EXECUTE GROUP_READ WORLD_EXECUTE WORLD_READ 
    DESTINATION "Contents/MacOS/"
  )

install(
    FILES "Contents/Resources/${FLAVOR}.icns"
    DESTINATION "Contents/Resources/"
    RENAME "mccodegui.icns"
  )
