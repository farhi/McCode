cmake_minimum_required(VERSION 3.17)

# This will install NCrystal components
project(NCrystal_wrapper)

message(STATUS "Configure ${CMAKE_PROJECT_NAME} ${FLAVOR} ${PROJECT_NAME}")
set(NCRYSTAL_ENABLE_EXAMPLES OFF)

# To be built with/for McStas
set(BUILD_MCSTAS   "Choose the McStas flavor" on)

# Set module path
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake/Modules/")
# Set McCode values (from mkdist or defaults)
include(MCUtil)

set(FLAVOR "mcstas")

if(WINDOWS)
  setupMCCODE("${FLAVOR}")
endif()

set(CPACK_PACKAGE_NAME "${FLAVOR}-NCrystal-${MCCODE_VERSION}")
set(CPACK_PACKAGE_CONTACT       "ncrystal-developers@cern.ch")
set(CPACK_PACKAGE_VERSION       "3.4.1")
set(CPACK_PACKAGE_VERSION_MAJOR "3.4")
set(CPACK_PACKAGE_VERSION_MINOR "1")
set(CPACK_NSIS_PACKAGE_NAME "NCrystal 3.4.1")
set(CPACK_NSIS_DISPLAY_NAME "NCrystal 3.4.1")

set(CPACK_FREEBSD_PACKAGE_LICENSE "Apache-2.0")

# NSIS
set(NSIS_NAME "${CPACK_PACKAGE_NAME}")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "${NSIS_NAME}")

# Drop any mccode-deb/rpm postfixing
set(CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA "")
set(CPACK_RPM_POST_INSTALL_SCRIPT_FILE "")
set(CPACK_RPM_POST_UNINSTALL_SCRIPT_FILE "")

include(CPack)

set(WORK "${PROJECT_BINARY_DIR}/work")

if(WINDOWS)
  # batch snippets for the Python tools
  foreach (tool ncrystal-config ncrystal_endf2ncmat ncrystal_hfg2ncmat ncrystal_inspectfile ncrystal_ncmat2cpp ncrystal_ncmat2hkl ncrystal_preparemcstasdir ncrystal_vdos2ncmat ncrystal_verifyatompos)
    configure_file("${CMAKE_CURRENT_SOURCE_DIR}/batches/${tool}.bat.in" "${WORK}/${tool}.bat" @ONLY)
    install(
      PROGRAMS "${WORK}/${tool}.bat"
      DESTINATION "${bin}"
      )
  endforeach()
endif()

add_subdirectory(ncrystal)

