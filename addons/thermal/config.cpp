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

// ─── Engine thermal model (issue #196) ─────────────────────────────────────
// The ENGINE renders TI mode from its own per-model dynamic thermal model,
// whose parameters live in CfgVehicles.  This is the single owner of those
// keys: optics/config.cpp no longer declares any of them, so load order can
// no longer change the outcome.
//
// These keys are NOT documented on the BI Community Wiki.  Their meanings
// survive only in ACE3's config comments (addons/thermals/config.cpp), which
// are themselves BIS-derived, and in a BIS forum post for the vanilla Tank.
// No published physics defines afMax, mfMax, htMin, htMax or mFact: they are
// engine tuning parameters, not measured quantities.  Only tBody has a
// physical role.
//
//   mFact (0..1)  metabolism influence on temperature (0 = none)
//   tBody (C)     the model's surface (metabolism) temperature
//   htMin/htMax (s) half-cooling time range (engine state heat decay)
//   afMax (C)     capped max temperature when alive/engine on
//   mfMax (C)     capped max temperature when moving (kinetic/friction)
//
// tBody is the surface temperature, NOT the core: the engine models one
// node per model, so there is no core to read, and a thermal imager sees the
// surface.  Human skin emissivity is 0.97-0.999, so the surface dominates
// the signal; the resting skin temperature is about 32 C, not the 36.8 C
// core set point.  Values follow ACE3's ace_thermals (same path above) so
// both mods agree: with ACE3 loaded, neither declaration silently wins.
//
// Warm-blooded: full metabolism (mFact 1) at skin temperature (tBody 32).
// Vehicles: no metabolism (mFact 0; parked reads ambient) with the ace
// half-cooling range 60..1800 s, which brackets a thin steel panel (minutes)
// and an engine block (tens of minutes), capped at 70 C alive and 50 C
// moving.  Animals are warm-blooded like humans.
//
// The caps afMax/mfMax also sit on the class All ROOT so they reach
// map-embedded buildings and statics.  Those have no selections, so
// setObjectMaterial cannot touch them and the engine would otherwise bake
// them hot.  htMin/htMax stay on vehicles only: the cooling-time keys have no
// meaning at the root.
class CfgVehicles {
    class All {
        afMax = 70;         // map-wide cap, alive/engine-on surface temp (C)
        mfMax = 50;         // map-wide cap, moving surface temp (C)
    };

    class Land;
    class Man: Land {
        mFact = 1;          // full metabolism influence
        tBody = 32;         // skin surface temp (C), not the 36.8 C core
    };

    class AllVehicles: All {
        htMin = 60;         // engine heat decay half-time, hot engine (s)
        htMax = 1800;       // decay half-time, cold-soaked (s), ace value
        afMax = 70;         // alive/engine-on max surface temp (C)
        mfMax = 50;         // moving max surface temp (kinetic, C)
        mFact = 0;          // no metabolism - parked = ambient
        tBody = 0;          // no resting heat
    };

    class Animal;
    class Animal_Base_F: Animal {
        mFact = 1;
        tBody = 32;
    };
};

// ─── Per-optic thermal keys (issue #196, aee-thermal-realism T11) ──────────
// The generated header carries the per-optic thermalMode[], thermalNoise[]
// and thermalResolution[] block, derived from the device corpus and the
// authored class bindings. It is a separate class CfgWeapons block. Regenerate
// with tools/validation/gen_thermal_optics.py.
#include "generated/ThermalOptics.hpp"
