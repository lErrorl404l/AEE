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
    class All;
    class AllVehicles: All {
        htMin = 60;    // exhaust/manifold hot-spots half-life
        htMax = 300;   // body panels half-life: ~5 min warm/cool, matching
                       // the physics model's engine tau.  Real sheet-metal
                       // bodies have low thermal mass and high surface area,
                       // so they warm AND cool visibly within minutes.
                       // Vanilla/ACE 1800 (30 min) is tuned for the engine
                       // block's IR DETECTABILITY — too slow for how a
                       // parked body LOOKS.  (ACE3's own comment: engine
                       // start warms the whole model at htMax rate.)
        afMax = 70;   // max alive temperature C (real sun+engine surface
                       // cap).  Vanilla 200 is unrealistic.  NOT 0: the
                       // engine reads 0 as unset/default in some paths, so
                       // 0 does not disable the alive-heat model — it falls
                       // back to vanilla 200 (the fast warm-up report).
                       // A real cap is the physical answer: the body heats
                       // toward 70 C, and our setVehicleTIPars drives the
                       // PART heat (engine/wheels/weapon) on top.
        mfMax = 50;   // max moving temperature C (tyres/brakes)
        mFact = 0.0;
        tBody = 0;
    };
};
