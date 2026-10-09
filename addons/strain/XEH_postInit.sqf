#include "script_component.hpp"
#include "\z\aee\addons\lib\script_debug.hpp"

AEE_MODULE_POST_INIT

// Register the shooter-stability sway factor with ACE3 when present.
// Runs after all addons have registered their factors; ACE3's sway loop
// picks it up on its next 0.5 s tick.
[] call FUNC(integrateSwayFactor);

// ─── Stamina-to-animation coupling (issue #212) ────────────────────────────
// A 1 s client-local loop applies the strain state to movement speed.
// ACE3 advanced fatigue is guarded inside fnc_applyMovementSpeed.
if (hasInterface) then {
    [{
        private _perfT0 = diag_tickTime;
        BEGIN_COUNTER(applyMovementSpeed);
        [player] call FUNC(applyMovementSpeed);
        END_COUNTER(applyMovementSpeed);
        if (AEE_TRACE_ON) then {
            private _perfMsg = format ["movementSpeed %1 ms", round ((diag_tickTime - _perfT0) * 1000)];
            AEE_LOG_DEBUG(_perfMsg);
        };
    }, 1] call CBA_fnc_addPerFrameHandler;
};
