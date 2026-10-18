#include "script_component.hpp"
#include "\z\aee\addons\lib\script_debug.hpp"

AEE_MODULE_POST_INIT

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

        // ── Real elapsed interval (issue #292) ──
        // CBA's per-frame handler passes [_args, _handle] and no delta, and a
        // hardcoded 1 s step makes physiology fall behind wall-clock on a
        // lagging client.  Measure the wall-clock gap since the last pass;
        // the floor keeps the first pass finite.
        private _now = diag_tickTime;
        private _dtSec = _now - (missionNamespace getVariable [QGVAR(lastTickTime), _now]);
        missionNamespace setVariable [QGVAR(lastTickTime), _now];
        _dtSec = _dtSec max 0.001;

        // ── G load from velocity deltas ──
        BEGIN_COUNTER(getGLoad);
        private _g = [_unit] call EFUNC(strain,getGLoad);
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
        // The exposure held above tolerance is caller state, carried across
        // passes so LOC is reached on the Whinnery-Forster time, not on the
        // first tick above tolerance (issue #290).
        private _exposurePrev = missionNamespace getVariable [QGVAR(gLocExposure_s), 0];
        if !(_exposurePrev isEqualType 0) then { _exposurePrev = 0; };
        BEGIN_COUNTER(calculateGLOC);
        private _glocRes = [_gLevel, 3, _agsm, _gsuit, _reclined, _hypoxRisk, _exposurePrev, _dtSec] call FUNC(calculateGLOC);
        END_COUNTER(calculateGLOC);
        private _stage = _glocRes select 0;
        missionNamespace setVariable [QGVAR(gLocExposure_s), _glocRes select 3];

        // ── Altitude DCS (above 21,000 ft the ZH-L16C R-ratio rises) ──
        // A pressurised fixed-wing cabin holds at most 8,000 ft cabin altitude
        // (14 CFR 25.841(a)); a helicopter is unpressurised.
        private _altM = (getPosASL _unit) select 2;
        if ((vehicle _unit) isKindOf "Plane") then { _altM = _altM min 2438; };
        private _dcsRisk = 0;
        if (_altM > 6400) then {   // ~21,000 ft
            private _entry = [_unit] call EFUNC(dive,getDiveState);
            private _tissues = _entry select [0, 32];
            private _res = [_altM, _tissues, _dtSec] call FUNC(calculateAltitudeDCS);
            // Splice the 32 tissue compartments back into the FULL dive
            // state.  _res select 2 is the 32-element tissue result and the
            // dive state is 38 elements (fnc_getDiveState), so reassigning
            // _entry to the result dropped fN2/fHe/fO2, the last depth, the
            // DCS accumulator and the ascent-violation count (issue #289).
            for "_i" from 0 to 31 do { _entry set [_i, _res select 2 select _i]; };
            private _state = missionNamespace getVariable [QEGVAR(dive,diveStates), -1];
            if (_state isEqualType 0) then {
                _state = createHashMap;
                missionNamespace setVariable [QEGVAR(dive,diveStates), _state];
            };
            private _uid = _unit getVariable [QEGVAR(dive,diveUID), ""];
            _state set [_uid, _entry];
            missionNamespace setVariable [QEGVAR(dive,diveStates), _state];
            // The kernel returns the risk the last second of exposure added.
            // The published value is the episode risk, so the one-second
            // increments compose: 2700 ticks reach the 45-minute anchor
            // (Haske & Pilmanis 2002).  Below the gate the supersaturation
            // resolves and the episode ends.
            private _episode = missionNamespace getVariable [QGVAR(altitudeDCSRisk), 0];
            _dcsRisk = 1 - ((1 - _episode) * (1 - (_res select 0)));
        };

        // ── Publish ──
        missionNamespace setVariable [QGVAR(gLoad), _gLevel];
        missionNamespace setVariable [QGVAR(gLocStage), _stage];
        missionNamespace setVariable [QGVAR(altitudeDCSRisk), _dcsRisk];
        missionNamespace setVariable [QGVAR(gLocTolerance), _glocRes select 2];
        // Apply the stage to the view.  Without a consumer the whole feature
        // is inert (issue #293).
        [] call FUNC(applyGLOCEffects);
        if (AEE_TRACE_ON) then {
            private _perfMsg = format ["gloc %1 ms", round ((diag_tickTime - _perfT0) * 1000)];
            AEE_LOG_DEBUG(_perfMsg);
        };
    }, 1, player] call CBA_fnc_addPerFrameHandler;
};
