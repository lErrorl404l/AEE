#include "script_component.hpp"
#include "\z\aee\addons\lib\script_debug.hpp"

AEE_MODULE_POST_INIT

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
                private _step = [0, 0.79, 0, _tissues, 1.0] call FUNC(zh16cStep);
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

// ─── G-LOC + altitude DCS loop (issue #135) ────────────────────────────────
// 1 Hz for the local player: measures G from velocity deltas (no engine
// G command), integrates altitude DCS via the ZH-L16C solver at barometric
// pressure, and stages the G-LOC response.  Gated by glocEnabled and
// hasInterface; the hypoxia interaction comes from the shared core hypoxia
// risk.  A dedicated server has no local player and must not register the
// loop nor write the G-LOC variables to missionNamespace.
if (hasInterface && (missionNamespace getVariable [QGVAR(glocEnabled), true])) then {
    [{
        private _perfT0 = diag_tickTime;
        params ["_unit"];
        if (_unit != call CBA_fnc_currentUnit) exitWith {};

        // ── G load from velocity deltas ──
        BEGIN_COUNTER(getGLoad);
private _g = [_unit] call FUNC(getGLoad);
END_COUNTER(getGLoad);
        private _gLevel = _g select 0;

        // AGSM (active) — a simple auto-threshold: the player holds the
        // sustained G with their own control, modelled as the AGSM boost
        // being available at will.  G-suit + seat are config-derived.
        // These are BOOLEAN toggles from the settings; the GLOC solver
        // takes numeric 0..1 factors, so coerce with parseNumber.
        private _agsm = parseNumber (missionNamespace getVariable [QGVAR(agsmAvailable), true]);
        private _gsuit = parseNumber (missionNamespace getVariable [QGVAR(gsuitEquipped), false]);
        private _reclined = parseNumber (missionNamespace getVariable [QGVAR(seatReclined), false]);
        private _hypoxRisk = missionNamespace getVariable [QEGVAR(core,currentHypoxiaRisk), 0];
        BEGIN_COUNTER(calculateGLOC);
private _glocRes = [_gLevel, 3, _agsm, _gsuit, _reclined, _hypoxRisk] call FUNC(calculateGLOC);
END_COUNTER(calculateGLOC);
        private _stage = _glocRes select 0;

        // ── Altitude DCS (above 21,000 ft the ZH-L16C R-ratio rises) ──
        private _altM = (getPosASL _unit) select 2;
        private _dcsRisk = 0;
        if (_altM > 6400) then {   // ~21,000 ft
            private _entry = [_unit] call FUNC(getDiveState);
            private _tissues = _entry select [0, 32];
            private _res = [_altM, 1, _tissues] call FUNC(calculateAltitudeDCS);
            _dcsRisk = _res select 0;
            _entry = _res select 2;
            for "_i" from 0 to 31 do { _entry set [_i, _res select 2 select _i]; };
            private _state = missionNamespace getVariable [QGVAR(diveStates), -1];
            if (_state isEqualType 0) then {
                _state = createHashMap;
                missionNamespace setVariable [QGVAR(diveStates), _state];
            };
            private _uid = _unit getVariable [QGVAR(diveUID), ""];
            _state set [_uid, _entry];
            missionNamespace setVariable [QGVAR(diveStates), _state];
        };

        // ── Publish ──
        missionNamespace setVariable [QGVAR(gLoad), _gLevel];
        missionNamespace setVariable [QGVAR(gLocStage), _stage];
        missionNamespace setVariable [QGVAR(altitudeDCSRisk), _dcsRisk];
        missionNamespace setVariable [QGVAR(gLocTolerance), _glocRes select 2];
        if (AEE_TRACE_ON) then {
            private _perfMsg = format ["gloc %1 ms", round ((diag_tickTime - _perfT0) * 1000)];
            AEE_LOG_DEBUG(_perfMsg);
        };
    }, 1, player] call CBA_fnc_addPerFrameHandler;
};

// ─── Stamina-to-animation coupling (issue #212) ────────────────────────────
// A 1 s client-local loop applies the physiology state to movement speed.
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

// Uniform per-module state dump, one line a second.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;

