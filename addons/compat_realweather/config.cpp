/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        // No host addon is required.  This module reads weather.json from the
        // mission folder, and the aee_compat_realweather_enabled CBA setting
        // gates it.  It works with or without a Real Weather host mod, so a
        // skipWhenMissingDependencies flag can never skip it.  The inert flag
        // is removed (issue #79).
        requiredAddons[] = {
            "aee_lib",
            "aee_core",
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
