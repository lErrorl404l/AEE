#include "script_component.hpp"
#include "\z\aee\addons\lib\script_debug.hpp"

AEE_MODULE_POST_INIT

// ─── Diving loop (ZH-L16C, issue #118) ────────────────────────────────────
// 1 Hz integration for the local player while underwater (eyePos z < 0,
// the ADE-verified detection).  Tissues off-gas toward surface equilibrium
// when surfaced.  Gated by diveEnabled and hasInterface; only the local
// player integrates (the state is per-UID and follows the unit).  A
// dedicated server has no local player and must not register the loop.
if (hasInterface && (missionNamespace getVariable [QGVAR(diveEnabled), true])) then {
    [{
        private _perfT0 = diag_tickTime;
        params ["_unit"];
        if (_unit != call CBA_fnc_currentUnit) exitWith {};
        if (eyePos _unit select 2 < 0) then {
            BEGIN_COUNTER(updateDiveState);
            [] call FUNC(updateDiveState);
            END_COUNTER(updateDiveState);
        } else {
            // Surfaced: relax tissues toward surface equilibrium.  A few
            // minutes of surface air breathing clears the fast tissues.
            //
            // Skipped when every compartment already sits at the fresh
            // baseline.  Relaxation from equilibrium toward equilibrium is a
            // no-op, and this loop is 1 Hz and unconditional, so a player who
            // never dived paid a 16-compartment Schreiner integration, a
            // 32-element rebuild and two hashmap writes every second for
            // nothing.  The baseline is the model's own preload,
            // 0.74047 bar, from fnc_zh16cStep.
            private _entry = [_unit] call FUNC(getDiveState);
            private _tissues = _entry select [0, 32];
            private _atBaseline = true;
            {
                // Flat layout, 16 N2 then 16 He, which is how
                // fnc_zh16cStep builds a fresh state.  He is 0 at the surface,
                // so only the N2 half can sit above the surface preload.
                if (_x > 0.74047 + 0.0001) then { _atBaseline = false; };
            } forEach (_tissues select [0, 15]);
            if (!_atBaseline) then {
                private _step = [0, 0.79, 0, _tissues, 1.0] call EFUNC(physiology,zh16cStep);
                private _new = _step select 0;
                for "_i" from 0 to 31 do { _entry set [_i, _new select _i]; };
                private _state = missionNamespace getVariable [QGVAR(diveStates), -1];
                if (_state isEqualType 0) then {
                    _state = createHashMap;
                    missionNamespace setVariable [QGVAR(diveStates), _state];
                };
                private _uid = _unit getVariable [QGVAR(diveUID), ""];
                _state set [_uid, _entry];
                missionNamespace setVariable [QGVAR(diveStates), _state];
            };
        };
        if (AEE_TRACE_ON) then {
            private _perfMsg = format ["diveState %1 ms", round ((diag_tickTime - _perfT0) * 1000)];
            AEE_LOG_DEBUG(_perfMsg);
        };
    }, 1, player] call CBA_fnc_addPerFrameHandler;
};
