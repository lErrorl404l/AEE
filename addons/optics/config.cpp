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
        htMax = 300;   // body panels half-life
        // The ENGINE's own heat model is disabled for vehicles: AEE drives
        // every vehicle's heat state from its physics model via
        // setVehicleTIPars (fnc_applyEngineThermal), which computes the
        // surface temperature from solar, ambient, wind, engine and exhaust
        // heat every tick.  A non-zero afMax/mfMax would make the engine's
        // static timer model ADD a second heat curve on top of ours,
        // double-driving the image (vehicles warming too fast).  With the
        // static maxima at zero, our setVehicleTIPars values are the sole
        // heat source and the image tracks our physics exactly.
        afMax = 0;    // static alive-heat model OFF (physics drives)
        mfMax = 0;    // static moving-heat model OFF (physics drives)
        mFact = 0.0;
        tBody = 0;
    };
};
