class CfgPatches { class demo_visuals { units[] = {}; }; };

class CfgFunctions {
    class DEMO {
        class Visual {
            file = "demo\functions";
            class lateAperture { preInit = 1; };
            class okFunc {};
        };
    };
};

class CfgPostProcessTemplates {
    class DemoGrade {};
};

class CfgWeapons {
    class Rifle_Base_F;
    class optic_demo: Rifle_Base_F {
        class ItemInfo {
            class OpticsModes {
                class Scope {
                    // weapon optics: Min > Init is out of order per the wiki (CF005, info)
                    opticsZoomMin = 0.5;
                    opticsZoomInit = 0.3;
                    opticsZoomMax = 0.1;
                    // CF006: outside 0..1
                    opticsDisablePeripherialVision = 1.5;
                    // OpticsCHAbera5 / OpticsBlur4 are vanilla-pattern names: must NOT raise CF001
                    opticsPPEffects[] = {"OpticsCHAbera5", "OpticsBlur4"};
                    visionMode[] = {"Normal"};
                };
            };
        };
    };
};

class CfgVehicles {
    class demo_static {
        class Turrets {
            class MainTurret {
                // vehicle turret: opposite Min/Max convention seen in shipped mods, must NOT raise CF005
                opticsZoomMin = 0.08;
                opticsZoomMax = 0.04;
                opticsZoomInit = 0.08;
            };
        };
    };
};

// config strings are expressions evaluated by the engine: must NOT raise a PP003 type error
class CfgOpticsEffect {
    class DemoRad {
        type = "radialblur";
        params[] = {0.005, 0.005, "0.35/(getResolution select 4)", 0.35};
        priority = 950;
    };
};
