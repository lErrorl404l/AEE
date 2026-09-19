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

// ─── G-LOC + altitude DCS loop (issue #135) ────────────────────────────────
// 1 Hz for the local player: measures G from velocity deltas (no engine
// G command), integrates altitude DCS via the ZH-L16C solver at barometric
// pressure, and stages the G-LOC response.  Gated by glocEnabled; the
// hypoxia interaction comes from the shared core hypoxia risk.
if (missionNamespace getVariable [QGVAR(glocEnabled), true]) then {
    [{
        params ["_unit"];
        if (_unit != call CBA_fnc_currentUnit) exitWith {};

        // ── G load from velocity deltas ──
        private _g = [_unit] call FUNC(getGLoad);
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
        private _glocRes = [_gLevel, 3, _agsm, _gsuit, _reclined, _hypoxRisk] call FUNC(calculateGLOC);
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
            private _state = missionNamespace getVariable [QGVAR(diveStates), createHashMap];
            private _uid = _unit getVariable [QGVAR(diveUID), ""];
            _state set [_uid, _entry];
            missionNamespace setVariable [QGVAR(diveStates), _state];
        };

        // ── Publish ──
        missionNamespace setVariable [QGVAR(gLoad), _gLevel];
        missionNamespace setVariable [QGVAR(gLocStage), _stage];
        missionNamespace setVariable [QGVAR(altitudeDCSRisk), _dcsRisk];
        missionNamespace setVariable [QGVAR(gLocTolerance), _glocRes select 2];
    }, 1, player] call CBA_fnc_addPerFrameHandler;
};
