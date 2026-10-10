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
            "aee_atmos",
            "aee_ballistics",
            "aee_flight",
            "aee_hydrology",
            "aee_lighting",
            "aee_mobility",
            "aee_optics",
            "aee_particles",
            "aee_vehicles",
            "cba_main",
            "cba_xeh",
            "cba_settings",
        };
        author = AUTHOR;
        authors[] = AUTHORS;
        url = URL;
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"
