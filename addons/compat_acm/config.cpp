/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "aee_lib",
            "aee_core",
            "aee_persistence",
            "ACM_main",
            // fnc_integrateACM calls ACM_CBRN_fnc_* and writes ACM_CBRN_*.
            // ACM_main does not pull ACM_cbrn (ACM 1.4.8.0).
            "ACM_cbrn",
            // fnc_registerHypoxiaDutyFactor calls ace_medical_vitals.
            "ace_medical_vitals",
            "cba_main",
            "cba_xeh"
        };
        author = AUTHOR;
        authors[] = AUTHORS;
        url = URL;
        skipWhenMissingDependencies = 1;
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"
