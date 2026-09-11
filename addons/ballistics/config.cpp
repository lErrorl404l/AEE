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
            "cba_main",
            "cba_xeh"
        };
        author = "lErrorl404l";
        authors[] = {"lErrorl404l"};
        url = "https://github.com/AEE-Dev-Team/aee";
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"
