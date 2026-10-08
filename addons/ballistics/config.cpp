/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "aee_main",
            "aee_atmos",
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

// Load-time engine overrides generated from the verified database; the
// verdict per class is in docs/wiki/research/engine-override-register.md.
#include "generated/CfgMagazines.hpp"
#include "generated/CfgAmmo.hpp"
