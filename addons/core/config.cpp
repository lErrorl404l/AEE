#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {QGVAR(module)};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "aee_main",
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
};

// ─── Particle / Visual FX Cloudlets ────────────────────────────────────────
// Custom cloudlet definitions used by AEE visual FX scripts for
// sandstorm, dust devil, and snow particle emitters.
class CfgCloudlets {
    class Default {};
    class AEE_SandCloud: Default {
        interval = 0.005;
        circleRadius = 30;
        circleVelocity[] = {0,0,0};
        particleFSNtieth = 2;
        particleFSIndex = 0;
        particleFSFrameCount = 4;
        particleFSLoop = 1;
        angleVar = 360;
        animationName = "";
        particleType = "Billboard";
        timerPeriod = 0.01;
        lifeTime = 3;
        moveVelocity[] = {5,0,3};
        rotationVelocity = 0;
        weight = 1.5;
        volume = 1;
        rubbing = 0;
        size[] = {0.3,3,6};
        color[] = {{0.6,0.5,0.3,0.3},{0.6,0.5,0.3,0.1},{0.6,0.5,0.3,0}};
        animationSpeed[] = {0.5,1};
        randomDirectionPeriod = 0.5;
        randomDirectionIntensity = 0.2;
        onTimerScript = "";
        beforeDestroyScript = "";
        lifeTimeVar = 1;
        positionVar[] = {5,2,5};
        MoveVelocityVar[] = {5,0,5};
        rotationVelocityVar = 5;
        sizeVar = 0.5;
        colorVar[] = {0,0,0,0};
        randomDirectionPeriodVar = 0.1;
        randomDirectionIntensityVar = 0.1;
    };
    class AEE_SnowCloud: Default {
        interval = 0.01;
        circleRadius = 30;
        circleVelocity[] = {0,0,0};
        particleFSNtieth = 2;
        particleFSIndex = 0;
        particleFSFrameCount = 4;
        particleFSLoop = 1;
        angleVar = 360;
        animationName = "";
        particleType = "Billboard";
        timerPeriod = 0.02;
        lifeTime = 4;
        moveVelocity[] = {0,0,-1.5};
        rotationVelocity = 0;
        weight = 0.3;
        volume = 0;
        rubbing = 0;
        size[] = {0.02,0.05,0.1};
        color[] = {{1,1,1,0.4},{1,1,1,0.2},{1,1,1,0}};
        animationSpeed[] = {0.5,1};
        randomDirectionPeriod = 0.2;
        randomDirectionIntensity = 0.05;
        onTimerScript = "";
        beforeDestroyScript = "";
        lifeTimeVar = 1;
        positionVar[] = {5,2,5};
        MoveVelocityVar[] = {2,0,1};
        rotationVelocityVar = 2;
        sizeVar = 0.1;
        colorVar[] = {0,0,0,0};
        randomDirectionPeriodVar = 0.05;
        randomDirectionIntensityVar = 0.05;
    };
};
