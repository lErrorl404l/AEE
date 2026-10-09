/* SPDX-License-Identifier: GPL-2.0-or-later */
#define COMPONENT lib
#define COMPONENT_BEAUTIFIED Lib
#include "\z\aee\addons\lib\script_mod.hpp"

// #define DEBUG_MODE_FULL
// #define DISABLE_COMPILE_CACHE

#ifdef DEBUG_ENABLED_LIB
    #define DEBUG_MODE_FULL
#endif

#include "\z\aee\addons\lib\script_macros.hpp"

class CfgPatches {
    class aee_lib {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "A3_Data_F",
            "cba_main",
            "cba_xeh"
        };
        author = AUTHOR;
        authors[] = AUTHORS;
        url = URL;
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"
