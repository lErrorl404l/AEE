/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "aee_lib",
            "aee_core",
            "cba_main",
            "cba_xeh",
            "A3_Data_F"
        };
        author = AUTHOR;
        authors[] = AUTHORS;
        url = URL;
        VERSION_CONFIG;
    };
};

// ─── Particle / Visual FX Cloudlets ────────────────────────────────────────
// Refractive shock trace cloudlet (issue #217 follow-on).
// The engine ships the refractive-distortion billboard at
// \A3\data_f\ParticleEffects\Universal\refract, verified in the base game
// data_f package.  fnc_renderSupersonicTrace reads particleShape from this
// class, so the engine path has a single source.  The renderer sets every
// other value per tick.
class CfgCloudlets {
    // Forward declaration only (same rule as aee_core/config.cpp).  A bare
    // `class Default {};` shadows the vanilla CfgCloudlets/Default that every
    // base-game smoke cloudlet inherits.
    class Default;
    class AEE_SupersonicTrace: Default {
        particleShape = "\A3\data_f\ParticleEffects\Universal\refract";
        particleType = "Billboard";
        particleFSNtieth = 1;
        particleFSIndex = 0;
        particleFSFrameCount = 1;
        particleFSLoop = 0;
    };
};

#include "CfgEventHandlers.hpp"
