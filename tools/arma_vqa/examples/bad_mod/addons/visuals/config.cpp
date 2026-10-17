class CfgPatches {
    class badmod_visuals { units[] = {}; weapons[] = {}; requiredVersion = 0.1; requiredAddons[] = {"A3_Weapons_F"}; };
};

class CfgOpticsEffect {
    class BadGrade {
        type = "ColorCorrections";
        priority = 1550;
        params[] = {1, 0.3, 0, {0,0,0,0}, {1,1,1,0.2}, {0.3,0.6,0.1,0}};
    };
    class BadBlur {
        type = "DynamicBlur";
        priority = 1550;                 // same priority as BadGrade
        params[] = {0.5, 1};             // DynamicBlur takes exactly 1 value
    };
    class BadType {
        type = "ChromaticAberration";    // real type is ChromAberration
        priority = 210;
        params[] = {0.01, 0.01, 0};
    };
    class GoodChroma {
        type = "ChromAberration";
        priority = 211;
        params[] = {0.002, 0.002, 1};
    };
};

class CfgWeapons {
    class ItemCore;
    class optic_badmod: ItemCore {
        class ItemInfo {
            class OpticsModes {
                class Scope {
                    opticsPPEffects[] = {"BadGrade", "BadBlur", "OpticsBlur2", "Missing_Effect"};
                    visionMode[] = {"Normal", "NVG", "Thermal"};   // "Thermal" is not a token; "Ti" is
                    thermalMode[] = {0, 1};
                };
                class Dot {
                    opticsPPEffects[] = {"GoodChroma"};
                    visionMode[] = {"Normal"};
                    thermalMode[] = {0};                           // no Ti in visionMode
                };
            };
        };
    };
};
