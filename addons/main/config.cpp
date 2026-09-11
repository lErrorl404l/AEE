/* SPDX-License-Identifier: GPL-2.0-or-later */
#define COMPONENT main
#define COMPONENT_BEAUTIFIED Main
#include "\z\aee\addons\main\script_mod.hpp"

// #define DEBUG_MODE_FULL
// #define DISABLE_COMPILE_CACHE

#ifdef DEBUG_ENABLED_MAIN
    #define DEBUG_MODE_FULL
#endif

#include "\z\aee\addons\main\script_macros.hpp"

class CfgPatches {
    class aee_main {
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
