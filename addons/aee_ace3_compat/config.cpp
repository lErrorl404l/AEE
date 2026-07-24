class CfgPatches {
    class aee_ace3_compat {
        name = "AEE - ACE3 Compatibility";
        units[] = {};
        weapons[] = {};
        requiredVersion = 2.14;
        requiredAddons[] = {
            "aee_core",
            "ace_weather"
        };
        author = "AEE Team";
    };
};

class Extended_PreInit_EventHandlers {
    class aee_ace3_compat {
        init = "call compile preprocessFileLineNumbers 'z\aee\addons\aee_ace3_compat\XEH_preInit.sqf'";
    };
};
