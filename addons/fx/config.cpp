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
    class AEE_SandCloud: Default {
        interval = 0.005;
        circleRadius = 30;
        circleVelocity[] = {0,0,0};
        particleFSNtieth = 2;
        particleFSIndex = 0;
        particleFSFrameCount = 4;
        particleFSLoop = 1;
        angleVar = 360;
        animationName = "";
        particleType = "Billboard";
        timerPeriod = 0.01;
        lifeTime = 3;
        moveVelocity[] = {5,0,3};
        rotationVelocity = 0;
        weight = 1.5;
        volume = 1;
        rubbing = 0;
        size[] = {0.3,3,6};
        color[] = {{0.6,0.5,0.3,0.3},{0.6,0.5,0.3,0.1},{0.6,0.5,0.3,0}};
        animationSpeed[] = {0.5,1};
        randomDirectionPeriod = 0.5;
        randomDirectionIntensity = 0.2;
        onTimerScript = "";
        beforeDestroyScript = "";
        lifeTimeVar = 1;
        positionVar[] = {5,2,5};
        MoveVelocityVar[] = {5,0,5};
        rotationVelocityVar = 5;
        sizeVar = 0.5;
        colorVar[] = {0,0,0,0};
        randomDirectionPeriodVar = 0.1;
        randomDirectionIntensityVar = 0.1;
    };
    class AEE_SnowCloud: Default {
        interval = 0.01;
        circleRadius = 30;
        circleVelocity[] = {0,0,0};
        particleFSNtieth = 2;
        particleFSIndex = 0;
        particleFSFrameCount = 4;
        particleFSLoop = 1;
        angleVar = 360;
        animationName = "";
        particleType = "Billboard";
        timerPeriod = 0.02;
        lifeTime = 4;
        moveVelocity[] = {0,0,-1.5};
        rotationVelocity = 0;
        weight = 0.3;
        volume = 0;
        rubbing = 0;
        size[] = {0.02,0.05,0.1};
        color[] = {{1,1,1,0.4},{1,1,1,0.2},{1,1,1,0}};
        animationSpeed[] = {0.5,1};
        randomDirectionPeriod = 0.2;
        randomDirectionIntensity = 0.05;
        onTimerScript = "";
        beforeDestroyScript = "";
        lifeTimeVar = 1;
        positionVar[] = {5,2,5};
        MoveVelocityVar[] = {2,0,1};
        rotationVelocityVar = 2;
        sizeVar = 0.1;
        colorVar[] = {0,0,0,0};
        randomDirectionPeriodVar = 0.05;
        randomDirectionIntensityVar = 0.05;
    };
};

#include "CfgEventHandlers.hpp"
