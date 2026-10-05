/* SPDX-License-Identifier: GPL-2.0-or-later */
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
        author = AUTHOR;
        authors[] = AUTHORS;
        url = URL;
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"

// ─── CfgWorlds engine pipeline overrides ──────────────────────────────────
// The HDRNewPars block is the engine HDR pipeline, read at world load.  Its
// values are re-derived from the public config of Real Lighting and Weather
// (Workshop 2809399991) and Fluffys (Workshop 3704702374, 3737586377).  No
// mod code or content is copied.  The base game config is read at run time
// and is not shipped.
//
// starEmissivity scales the engine star draw.  The engine reads it from the
// world's own Lighting class.  The base config only forward-declares
// DefaultLighting, so AEE overrides each official world's Lighting too.  40
// sits mid-band between Fluffys (30) and Real Lighting (60).
//
// The NVG keys keep their calibration.  NVG objectives are fixed-aperture
// (f/1.2, MIL-PRF-49427C); the engine simulates variable aperture, so
// locking nvgApertureMin = Standard = Max at 7 removes the artificial
// dimming.  nvgLightGain = 80 (below the default 100) keeps the phosphor dim
// (Elbit MX-10160, 6.9-14.4 cd/m²) so the AEE tube model controls brightness.
//
// DOFPars places the NVG focal plane at ~12 m (27 mm EFL, MIL-PRF-49427C).
class CfgWorlds {
    // starEmissivity scales the engine star draw.  The engine reads the value
    // from the world's own Lighting class, not from DefaultLighting.  The base
    // config forward-declares DefaultLighting and gives it no value, and every
    // official world sets its own, so AEE overrides each world's Lighting.  A
    // redefinition without a base clears the inherited base, so every block
    // below names its base.  Real Lighting and Weather (Workshop 2809399991)
    // and Fluffys (Workshop 3704702374, 3737586377) also override each world's
    // Lighting.  40 sits mid-band between Fluffys (30) and Real Lighting (60).
    // No mod content is copied.
    class DefaultLighting {
        starEmissivity = 40;
    };
    class DefaultWorld;
    class CAWorld: DefaultWorld {
        class Lighting: DefaultLighting {
            starEmissivity = 40;
        };
    };
    class Stratis: CAWorld {
        class Lighting: DefaultLighting {
            starEmissivity = 40;
        };
    };
    class Altis: CAWorld {
        class Lighting: DefaultLighting {
            starEmissivity = 40;
        };
    };
    class VR: CAWorld {
        class Lighting: DefaultLighting {
            starEmissivity = 40;
        };
    };
    class Malden: CAWorld {
        class Lighting: DefaultLighting {
            starEmissivity = 40;
        };
    };
    class Enoch: CAWorld {
        class Lighting: DefaultLighting {
            starEmissivity = 40;
        };
    };
    class Tanoa: CAWorld {
        class Lighting: DefaultLighting {
            starEmissivity = 40;
        };
    };
    class HDRNewPars {
        nvgApertureMin = 7;
        nvgApertureStandard = 7;
        nvgApertureMax = 7;
        nvgStandardAvgLum = 3;
        nvgLightGain = 80;
        nvgTransition = 1;
        nvgTransitionCoefOn = 40.0;
        nvgTransitionCoefOff = 0.01;
        minAperture = 1e-005;
        maxAperture = 256;
        apertureRatioMax = 4;
        apertureRatioMin = 10;
        bloomImageScale = 1;
        bloomScale = 0.09;
        bloomExponent = 0.75;
        bloomLuminanceOffset = 0.4;
        bloomLuminanceScale = 0.15;
        bloomLuminanceExponent = 0.25;
        tonemapMethod = 1;
        tonemapShoulderStrength = 0.22;
        tonemapLinearStrength = 0.12;
        tonemapLinearAngle = 0.1;
        tonemapToeStrength = 0.2;
        tonemapToeNumerator = 0.022;
        tonemapToeDenominator = 0.2;
        tonemapLinearWhite = 11.2;
        tonemapExposureBias = 1;
        eyeAdaptFactorLight = 3.3;
        eyeAdaptFactorDark = 0.75;
        nightShiftMinAperture = 0;
        nightShiftMaxAperture = 0.002;
        nightShiftMaxEffect = 0.6;
        nightShiftLuminanceScale = 600;
    };
    class DOFPars {
        focusDistance = 12.0;
        blur = 0.6;
        farOnly = 1;
    };
    // The night-darkness endpoints the engine interpolates between.  These
    // deepNight and fullNight arrays are re-derived from Real Lighting and
    // Weather (Workshop 2809399991) lines 589-602.  No mod content is copied.
    // Every other keyframe keeps the base game value.
    class DayLightingBrightAlmost {
        deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
        fullNight[] = {-5,{0.182,0.213,0.25},{0.05,0.111,0.221},{0.039,0.034,0.004},{0.04,0.049,0.072},{0.082,0.128,0.185},{0.283,0.35,0.431},0};
    };
    class DayLightingRainy {
        deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
        fullNight[] = {-5,{0.023,0.023,0.023},{0.02,0.02,0.02},{0.023,0.023,0.023},{0.02,0.02,0.02},{0.0098,0.0098,0.02},{0.08,0.059,0.059},0};
    };
};
