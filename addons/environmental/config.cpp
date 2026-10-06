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
            "cba_xeh",
            "A3_Data_F_Decade_Loadorder"
        };
        author = AUTHOR;
        authors[] = AUTHORS;
        url = URL;
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"

// ─── CfgWorlds engine pipeline overrides ──────────────────
// The engine reads HDRNewPars, DOFPars and the DayLighting keyframes
// through the WORLD CLASS CHAIN, not from a direct CfgWorlds child.  A
// direct child is an unreferenced sibling and inert.  The chain is
// CfgWorlds >> DefaultWorld >> CAWorld >> <World>:CAWorld, so AEE re-homes
// the anchor into CAWorld and into every stock world that redeclares the
// class.  Each block uses the explicit base form (`class X: X`) so the
// engine merges the values instead of replacing the class.  The same
// values appear in every block: this is the engine's structural requirement,
// not per-map tuning, so no value is keyed by a map name.
//
// The values are re-derived from the public config of Real Lighting and
// Weather (Workshop 2809399991) and Fluffys (Workshop 3704702374,
// 3737586377).  No mod code or content is copied.
//
// starEmissivity 25 is the shared default on DefaultLighting.  This is the
// vanilla world value (Altis starEmissivity = 25), restored after the review
// against Workshop 3587581054.  The engine core declares DefaultLighting with
// access 3 and starEmissivity 0.3; a re-open merges and propagates, but a world
// that sets its own starEmissivity shadows it, so CAWorld's Lighting and each
// stock world's Lighting carry the same 25.  A custom world keeps its own, and
// AEE compensates at run time through fnc_applyWorldLighting.
//
// The NVG keys keep their calibration.  NVG objectives are fixed-aperture
// (f/1.2, MIL-PRF-49427C); the engine simulates variable aperture, so
// locking nvgApertureMin = Standard = Max at 7 removes the artificial
// dimming.  nvgLightGain = 80 (below the default 100) keeps the phosphor dim
// (Elbit MX-10160, 6.9-14.4 cd/m²) so the AEE tube model controls brightness.
//
// DOFPars places the NVG focal plane at ~12 m (27 mm EFL, MIL-PRF-49427C).
//
// The base game owns these classes.  Declare each external base in an ANCESTOR
// scope of its re-open (HEMTT rejects a declaration and a re-open in the same
// scope as a duplicate).  A file-root declaration makes the engine log
// "declared, but definition was not found. Creating empty class" and re-parent
// every map onto that empty class, which empties the tone curve.
class CfgWorlds {
    // Shared default for any world that does not set its own starEmissivity.
    // Vanilla defines it in the engine core without a base, so a re-open
    // without a base merges and propagates the value.
    class DefaultLighting {
        starEmissivity = 25;
    };
    // Vanilla declares the DayLighting keyframes here, then defines them in
    // CAWorld and in each world.  DOFPars is defined here by the engine, so a
    // re-open in CAWorld inherits the water keys the engine reads.
    class DefaultWorld {
        class DayLightingBrightAlmost;
        class DayLightingRainy;
        class DOFPars;
    };
    class CAWorld: DefaultWorld {
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
        class DOFPars: DOFPars {
            focusDistance = 12.0;
            blur = 0.6;
            farOnly = 1;
        };
        class DayLightingBrightAlmost: DayLightingBrightAlmost {
            deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
            fullNight[] = {-5,{0.182,0.213,0.25},{0.05,0.111,0.221},{0.039,0.034,0.004},{0.04,0.049,0.072},{0.082,0.128,0.185},{0.283,0.35,0.431},0};
        };
        class DayLightingRainy: DayLightingRainy {
            deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
            fullNight[] = {-5,{0.023,0.023,0.023},{0.02,0.02,0.02},{0.023,0.023,0.023},{0.02,0.02,0.02},{0.0098,0.0098,0.02},{0.08,0.059,0.059},0};
        };
        class Lighting: DefaultLighting {
            starEmissivity = 25;
        };
    };
    class Stratis: CAWorld {
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
        class DayLightingBrightAlmost: DayLightingBrightAlmost {
            deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
            fullNight[] = {-5,{0.182,0.213,0.25},{0.05,0.111,0.221},{0.039,0.034,0.004},{0.04,0.049,0.072},{0.082,0.128,0.185},{0.283,0.35,0.431},0};
        };
        class DayLightingRainy: DayLightingRainy {
            deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
            fullNight[] = {-5,{0.023,0.023,0.023},{0.02,0.02,0.02},{0.023,0.023,0.023},{0.02,0.02,0.02},{0.0098,0.0098,0.02},{0.08,0.059,0.059},0};
        };
        class Lighting: DefaultLighting {
            starEmissivity = 25;
        };
    };
    class Altis: CAWorld {
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
        class DayLightingBrightAlmost: DayLightingBrightAlmost {
            deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
            fullNight[] = {-5,{0.182,0.213,0.25},{0.05,0.111,0.221},{0.039,0.034,0.004},{0.04,0.049,0.072},{0.082,0.128,0.185},{0.283,0.35,0.431},0};
        };
        class DayLightingRainy: DayLightingRainy {
            deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
            fullNight[] = {-5,{0.023,0.023,0.023},{0.02,0.02,0.02},{0.023,0.023,0.023},{0.02,0.02,0.02},{0.0098,0.0098,0.02},{0.08,0.059,0.059},0};
        };
        class Lighting: DefaultLighting {
            starEmissivity = 25;
        };
    };
    class Malden: CAWorld {
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
        class DayLightingBrightAlmost: DayLightingBrightAlmost {
            deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
            fullNight[] = {-5,{0.182,0.213,0.25},{0.05,0.111,0.221},{0.039,0.034,0.004},{0.04,0.049,0.072},{0.082,0.128,0.185},{0.283,0.35,0.431},0};
        };
        class DayLightingRainy: DayLightingRainy {
            deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
            fullNight[] = {-5,{0.023,0.023,0.023},{0.02,0.02,0.02},{0.023,0.023,0.023},{0.02,0.02,0.02},{0.0098,0.0098,0.02},{0.08,0.059,0.059},0};
        };
        class Lighting: DefaultLighting {
            starEmissivity = 25;
        };
    };
    class Tanoa: CAWorld {
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
        class DayLightingBrightAlmost: DayLightingBrightAlmost {
            deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
            fullNight[] = {-5,{0.182,0.213,0.25},{0.05,0.111,0.221},{0.039,0.034,0.004},{0.04,0.049,0.072},{0.082,0.128,0.185},{0.283,0.35,0.431},0};
        };
        class DayLightingRainy: DayLightingRainy {
            deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
            fullNight[] = {-5,{0.023,0.023,0.023},{0.02,0.02,0.02},{0.023,0.023,0.023},{0.02,0.02,0.02},{0.0098,0.0098,0.02},{0.08,0.059,0.059},0};
        };
        class Lighting: DefaultLighting {
            starEmissivity = 25;
        };
    };
    class Enoch: CAWorld {
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
        class DayLightingBrightAlmost: DayLightingBrightAlmost {
            deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
            fullNight[] = {-5,{0.182,0.213,0.25},{0.05,0.111,0.221},{0.039,0.034,0.004},{0.04,0.049,0.072},{0.082,0.128,0.185},{0.283,0.35,0.431},0};
        };
        class DayLightingRainy: DayLightingRainy {
            deepNight[] = {-15,{0.0049,0.0098,0.0098},{0,0.002,0.003},{0,0,0},{0,0,0},{0,0.002,0.003},{0,0.002,0.003},0};
            fullNight[] = {-5,{0.023,0.023,0.023},{0.02,0.02,0.02},{0.023,0.023,0.023},{0.02,0.02,0.02},{0.0098,0.0098,0.02},{0.08,0.059,0.059},0};
        };
        class Lighting: DefaultLighting {
            starEmissivity = 25;
        };
    };
};
