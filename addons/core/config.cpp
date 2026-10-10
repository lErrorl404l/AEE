/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {QGVAR(module), QGVAR(stormModule)};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "aee_lib",
            "A3_Data_F",
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

// ─── EDEN / Zeus Module ─────────────────────────────────────────────────────
// Placeable in the mission editor to configure AEE parameters per-mission
// without editing CBA settings or writing code.

class CfgVehicles {
    class Module_F;
    class GVAR(module): Module_F {
        scope = 2;
        displayName = CSTRING(Module_DisplayName);
        icon = "\a3\modules_f\data\portraitModule_ca.paa";
        category = "Environment";
        function = QFUNC(moduleInit);
        functionPriority = 1;
        isGlobal = 1;
        isTriggerActivated = 0;
        isDisposable = 0;
        class Arguments {
            class biomeOverride {
                displayName = CSTRING(Arg_biomeOverride);
                description = CSTRING(Arg_biomeOverride_Desc);
                typeName = "STRING";
                defaultValue = "";
            };
            class tempOffset {
                displayName = CSTRING(Arg_tempOffset);
                description = CSTRING(Arg_tempOffset_Desc);
                typeName = "NUMBER";
                defaultValue = 0;
            };
            class precipBias {
                displayName = CSTRING(Arg_precipBias);
                description = CSTRING(Arg_precipBias_Desc);
                typeName = "NUMBER";
                defaultValue = 1.0;
            };
            class windMultiplier {
                displayName = CSTRING(Arg_windMultiplier);
                description = CSTRING(Arg_windMultiplier_Desc);
                typeName = "NUMBER";
                defaultValue = 1.0;
            };
            class updateInterval {
                displayName = CSTRING(Arg_updateInterval);
                description = CSTRING(Arg_updateInterval_Desc);
                typeName = "NUMBER";
                defaultValue = 5;
            };
        };
        class ModuleDescription {
            description = CSTRING(Module_Description);
            sync[] = {};
        };
    };
    class GVAR(stormModule): Module_F {
        scope = 2;
        displayName = "AEE Storm Control";
        icon = "\a3\modules_f\data\portraitModule_ca.paa";
        category = "Environment";
        function = QFUNC(moduleStormInit);
        functionPriority = 1;
        isGlobal = 1;
        isTriggerActivated = 0;
        isDisposable = 0;
        class Arguments {
            class stormType {
                displayName = "Storm Type";
                description = "Severe weather to force: thunderstorm, sandstorm, snowstorm, or clear";
                typeName = "STRING";
                defaultValue = "thunderstorm";
            };
            class intensity {
                displayName = "Intensity";
                description = "Severity from 0 to 1 (0 = none, 1 = severe)";
                typeName = "NUMBER";
                defaultValue = 0.5;
            };
            class durationMin {
                displayName = "Duration (min)";
                description = "How long the override stays active, in minutes";
                typeName = "NUMBER";
                defaultValue = 5;
            };
        };
        class ModuleDescription {
            description = "Force a severe-weather state for a set duration. AEE publishes aee_core_stormOverrideType, aee_core_stormOverrideIntensity, and aee_core_stormOverrideUntil for the fx addon to consume.";
            sync[] = {};
        };
    };
};
