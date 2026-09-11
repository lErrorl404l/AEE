#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "aee_main",
            "aee_core",
            "aee_actions",
            "ace_medical",
            "ace_weather",
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

class CfgVehicles {
    class Man;
    class CAManBase: Man {
        class ACE_SelfActions {
            class AEE_WeatherReport {
                displayName = "$STR_AEE_ACTIONS_WeatherReport";
                condition = "true";
                statement = "call aee_actions_fnc_openWeatherReport";
                icon = "\a3\ui_f\data\IGUI\Cfg\Actions\scan_ca.paa";
            };
            class AEE_Altimeter {
                displayName = "$STR_AEE_ACTIONS_Altimeter";
                condition = "vehicle player != player && (vehicle player) isKindOf 'Helicopter'";
                statement = "call aee_actions_fnc_openAltimeter";
                icon = "\a3\ui_f\data\IGUI\Cfg\Actions\scan_ca.paa";
            };
        };
    };
};
