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
#include "RscTitles.hpp"

// ─── Engine thermal overrides (realistic heat scales) ─────────────────────
// The vanilla engine's thermal scale is wildly optimistic: default afMax
// (alive/max temperature) is 200 C and mfMax (moving) is 100 C, so a
// running vehicle maps to ~200 C and even a parked one reads proportionally
// white-hot — a major cause of the "everything is white" thermal image.
// Real surface temperatures (ACE3's own thermals addon, and IR sensor
// references): a sun-warmed vehicle body peaks ~70 C, moving tyres ~50 C.
// Humans glow via metabolism: mFact 1 + tBody 32 C (skin surface, not the
// 37 C core).  These values match ACE3's thermals config so there is no
// conflict when both mods are loaded; they also work standalone.
//
// This is the STATIC layer.  fnc_applyEngineThermal drives the per-vehicle
// runtime heat state (setVehicleTIPars) and the display window
// (setTIParameter) on top, from AEE's own physics model.
class CfgVehicles {
    class Man;
    class CAManBase: Man {
        mFact = 1;   // metabolism has full influence
        tBody = 32;  // skin surface temperature, C
    };
    // MAP-WIDE THERMAL CAPS: applied at the ROOT so every object inherits
    // a realistic thermal ceiling, including map-embedded buildings and
    // statics that have no hiddenSelections (setObjectMaterial cannot
    // reach them).  Vanilla afMax 200 C lets the engine bake any object
    // hot at midnight; capping at the root stops that map-wide with zero
    // runtime cost (config, not per-frame).  Units (Man) and animals
    // override with metabolism (mFact/tBody) and are unaffected.
    class All {
        htMin = 60;    // exhaust/manifold hot-spots half-life
        htMax = 300;   // body panels half-life: ~5 min warm/cool, matching
                       // the physics model's engine tau.  Real sheet-metal
                       // bodies have low thermal mass and high surface area,
                       // so they warm AND cool visibly within minutes.
                       // Vanilla/ACE 1800 (30 min) is tuned for the engine
                       // block's IR DETECTABILITY — too slow for how a
                       // parked body LOOKS.
        afMax = 70;   // max alive temperature C (real sun+engine surface
                       // cap).  Vanilla 200 is unrealistic.  NOT 0: the
                       // engine reads 0 as unset/default in some paths, so
                       // 0 does not disable the alive-heat model — it falls
                       // back to vanilla 200 (the fast warm-up report).
        mfMax = 50;   // max moving temperature C (tyres/brakes)
        mFact = 0.0;
        tBody = 0;
    };
    class AllVehicles: All {
        // Vehicles inherit the root caps; this keeps the class explicit
        // for compatibility with mods that expect it here (ACE3 pattern).
    };
};
