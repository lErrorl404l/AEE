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

// ─── CfgWorlds NVG / DOF overrides ────────────────────────────────────────
// Replaces the engine defaults with values calibrated to real NVG optics.
//
// NVG objectives are fixed-aperture (f/1.2, MIL-PRF-49427C).  The engine
// simulates variable aperture which NVGs do not have.  Locking
// nvgApertureMin = Standard = Max at 7 removes the engine's artificial
// aperture dimming.
//
// nvgLightGain = 80 (below default 100).  Real NVGs are dim devices:
// phosphor screen output is 6.9-14.4 cd/m² (Elbit MX-10160).  A lower
// engine gain lets the AEE tube model ppEffects control brightness
// without fighting the engine's built-in amplification.
//
// DOFPars: NVG objectives focus at ~10-15 m (27 mm EFL, MIL-PRF-49427C).
// Objects beyond ~15 m are progressively softer.  focusDistance = 12 m
// places the focal plane at typical NVG usage range.  farOnly = 1 blurs
// only distant objects, keeping near objects sharp.
class CfgWorlds {
    class HDRNewPars {
        nvgApertureMin = 7;
        nvgApertureStandard = 7;
        nvgApertureMax = 7;
        nvgStandardAvgLum = 3;
        nvgLightGain = 80;
        nvgTransition = 1;
        nvgTransitionCoefOn = 40.0;
        nvgTransitionCoefOff = 0.01;
    };
    class DOFPars {
        focusDistance = 12.0;
        blur = 0.6;
        farOnly = 1;
    };
};
