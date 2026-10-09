/* SPDX-License-Identifier: GPL-2.0-or-later */
#define MAINPREFIX z
#define PREFIX aee
#define SUBPREFIX addons

#include "script_version.hpp"

#define VERSION     MAJOR.MINOR
#define VERSION_STR MAJOR.MINOR.PATCHLVL.BUILD
#define VERSION_AR  MAJOR,MINOR,PATCHLVL,BUILD

#define VERSION_CONFIG version = VERSION; versionStr = QUOTE(VERSION_STR); versionAr[] = {VERSION_AR}

#define REQUIRED_VERSION 2.02

// COMPONENT_NAME is defined per-addon in script_component.hpp, but default here for fallback
#ifdef COMPONENT_BEAUTIFIED
    #define COMPONENT_NAME QUOTE(AEE - COMPONENT_BEAUTIFIED)
#endif

// Project identity - single source for author and repository.
// config.cpp references these macros; change here, not in 18 files.
#define AUTHOR "lErrorl404l"
#define AUTHORS {AUTHOR}
#define URL "https://github.com/lErrorl404l/AEE"
