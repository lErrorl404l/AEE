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

// ─── Engine thermal model (issue #196) ─────────────────────────────────────
// The ENGINE renders TI mode from its own dynamic thermal model, whose
// parameters live in CfgVehicles (the ACE-thermals lever).  The vanilla
// values bake vehicles bright at midnight regardless of the physics; the
// material swaps (ours, MKK's) modulate the engine output but cannot
// change the model itself.  This config sets the model's inputs from AEE
// physics so the engine's dynamic component is realistic:
//
//   mFact (0..1)  metabolism influence on temperature
//   tBody (C)     the model's metabolism temperature (its resting heat)
//   htMin/htMax (s) half-cooling time range (engine state heat decay)
//   afMax (C)     max temperature from being alive/engine on
//   mfMax (C)     max temperature from moving (kinetic/friction)
//
// Humans: resting metabolism at core temperature (Gagge 36.8 C is the
// two-node solver's neutral set point).  Vehicles: NO metabolism - they
// read ambient when parked and cold-soaked, exactly the night behaviour
// real FLIR shows (Muselli 2021 radiative cooling).  Animals: warm-blooded
// like humans.
class CfgVehicles {
    class Land;
    class Man: Land {
        mFact = 1;          // full metabolism influence
        tBody = 36.8;       // resting core temp (Gagge neutral)
    };

    class All;
    class AllVehicles: All {
        htMin = 60;         // engine heat decay half-time, hot engine
        htMax = 1800;       // decay half-time, cold-soaked (30 min)
        afMax = 70;         // alive/engine-on max surface temp (C)
        mfMax = 50;         // moving max surface temp (kinetic, C)
        mFact = 0;          // no metabolism - parked = ambient
        tBody = 0;          // no resting heat
    };

    class Animal;
    class Animal_Base_F: Animal {
        mFact = 1;
        tBody = 36.8;
    };
};
