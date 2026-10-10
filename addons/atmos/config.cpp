/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {QGVAR(volcanicModule)};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
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

// ─── EDEN / Zeus Module ─────────────────────────────────────────────────────
// Placeable in the mission editor.  The module position is the volcano vent.
class CfgVehicles {
    class Module_F;
    class GVAR(volcanicModule): Module_F {
        scope = 2;
        displayName = CSTRING(Module_DisplayName);
        icon = "\a3\modules_f\data\portraitModule_ca.paa";
        category = "Environment";
        function = QFUNC(moduleVolcanicInit);
        functionPriority = 1;
        isGlobal = 1;
        isTriggerActivated = 0;
        isDisposable = 0;
        class Arguments {
            class vei {
                displayName = CSTRING(Arg_vei);
                description = CSTRING(Arg_vei_Desc);
                typeName = "NUMBER";
                defaultValue = 5;
            };
            class ventAltitude {
                displayName = CSTRING(Arg_ventAltitude);
                description = CSTRING(Arg_ventAltitude_Desc);
                typeName = "NUMBER";
                defaultValue = 2000;
            };
            class ashEmission {
                displayName = CSTRING(Arg_ashEmission);
                description = CSTRING(Arg_ashEmission_Desc);
                typeName = "NUMBER";
                defaultValue = 5000000;
            };
            class so2Emission {
                displayName = CSTRING(Arg_so2Emission);
                description = CSTRING(Arg_so2Emission_Desc);
                typeName = "NUMBER";
                defaultValue = 500000;
            };
            class heatFlux {
                displayName = CSTRING(Arg_heatFlux);
                description = CSTRING(Arg_heatFlux_Desc);
                typeName = "NUMBER";
                defaultValue = 100000000000;
            };
            class latitude {
                displayName = CSTRING(Arg_latitude);
                description = CSTRING(Arg_latitude_Desc);
                typeName = "NUMBER";
                defaultValue = 45;
            };
            class slope {
                displayName = CSTRING(Arg_slope);
                description = CSTRING(Arg_slope_Desc);
                typeName = "NUMBER";
                defaultValue = 15;
            };
        };
        class ModuleDescription {
            description = CSTRING(Module_Description);
            sync[] = {};
        };
    };
};
