/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        // aee_eye itself needs 2.04 (apertureParams, fnc_eyeSampleScene); the
        // value is the mod-wide floor defined in script_mod.hpp.
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "aee_lib",
            "aee_core",
            "cba_main",
            "cba_xeh",
            "cba_settings"
        };
        author = AUTHOR;
        authors[] = AUTHORS;
        url = URL;
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"
