#include "script_component.hpp"

// A new body has no heat acclimatisation or altitude adaptation.
["AEE_OnPlayerKilled", {
    params ["_unit", "_killer", "_instigator", "_useEffects"];
    missionNamespace setVariable [QGVAR(acclimatizationPercent), 0];
}] call CBA_fnc_addPlayerKilledHandler;

// Register the shooter-stability sway factor with ACE3 when present.
// Runs after all addons have registered their factors; ACE3's sway loop
// picks it up on its next 0.5 s tick.
[] call FUNC(integrateSwayFactor);

// ─── Diving loop (ZH-L16C, issue #118) ────────────────────────────────────
// 1 Hz integration for the local player while underwater (eyePos z < 0,
// the ADE-verified detection).  Tissues off-gas toward surface equilibrium
// when surfaced.  Gated by diveEnabled; only the local player integrates
// (the state is per-UID and follows the unit).
if (missionNamespace getVariable [QGVAR(diveEnabled), true]) then {
    [{
        params ["_unit"];
        if (_unit != call CBA_fnc_currentUnit) exitWith {};
        if (eyePos _unit select 2 < 0) then {
            [] call FUNC(updateDiveState);
        } else {
            // Surfaced: relax tissues toward surface equilibrium.  A few
            // minutes of surface air breathing clears the fast tissues.
            private _entry = [_unit] call FUNC(getDiveState);
            private _tissues = _entry select [0, 32];
            private _step = [0, 0.79, 0, _tissues, 1.0] call FUNC(zh16cStep);
            private _new = _step select 0;
            for "_i" from 0 to 31 do { _entry set [_i, _new select _i]; };
            private _state = missionNamespace getVariable [QGVAR(diveStates), createHashMap];
            private _uid = _unit getVariable [QGVAR(diveUID), ""];
            _state set [_uid, _entry];
            missionNamespace setVariable [QGVAR(diveStates), _state];
        };
    }, 1, player] call CBA_fnc_addPerFrameHandler;
};
