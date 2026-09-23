#include "..\..\script_component.hpp"

/*
Frozen-lake ice load-bearing (issue #134).

Two closed-form physics: Stefan ice growth from accumulated freezing
degree-days, then Gold's load equation for the safe weight.

  Stefan:  h_ice = C · sqrt(FDD)   (C 2.7 bare / 1.7 snow-covered, cm)
  Gold:    P_safe = 3.5 · h_cm^2   (kg on clear ice)
           breakthrough = 3 × safe (flexural failure)

The mod has no frost-depth model (#11 not built), so FDD accumulates
here: a per-position (rounded 100 m grid) running sum of (0 - T_air)
whenever the air is below freezing, decayed above freezing.  Stored in
missionNamespace QGVAR(fddGrid) = createHashMap keyed by grid tag ->
[fddCDays, lastUpdateTick, iceCm].  Deterministic, cheap per tick.

Per the Minnesota DNR table (clear ice):
  <10 cm stay off; 10 person; 13-18 snowmobile/ATV; 23-25 small car;
  28-30 medium SUV; 33 medium truck; 41-43 heavy truck; 51+ heavy
  truck w/ shelter.

Input:  [_posASL] - query position
Output: [iceCm, safeKg, warnKg, loadState]
  loadState: 0 no ice, 1 walkable, 2 wheeled-lite, 3 wheeled-heavy,
             4 tracked-heavy, 5 shelter
Sets:   aee_environmental_iceThicknessCm, aee_environmental_iceSafeKg
        (read by the vehicle check)
*/

params [["_posASL", [], [[]]]];
if (_posASL isEqualTo []) exitWith { [0, 0, 0, 0] };

// ─── Accumulate FDD (Stefan) ─────────────────────────────────────────────
private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_T isEqualType 0) then { _T = 15; };
private _overcast = missionNamespace getVariable [QEGVAR(core,overcast), 0];
if !(_overcast isEqualType 0) then { _overcast = 0; };
private _snow = missionNamespace getVariable [QEGVAR(core,snowfallRate), 0];
if !(_snow isEqualType 0) then { _snow = 0; };

private _grid = missionNamespace getVariable [QGVAR(fddGrid), createHashMap];
private _key = format ["%1_%2", round ((_posASL select 0) / 100), round ((_posASL select 1) / 100)];
private _entry = _grid getOrDefault [_key, [0, -1e10, 0, 0]];
_entry params ["_fdd", "_lastTick", "_ice", "_snow24"];
private _now = diag_tickTime;
private _dtH = (_now - _lastTick) / 3600;
if (_dtH > 0.5) then { _dtH = 0.5; };   // clamp against long gaps

// The Stefan coefficient comes from the SOIL's own frozen conductivity
// and density, and from the snow that insulates it (issue #11). The mod
// once held two constants, 2.7 bare and 1.7 under snow, which is right
// for a generic soil but cannot express the real range: peat reaches
// 1.76 and dense sand 2.67 under the same weather.
//
// The surface class comes from the material classifier, not from a call
// into thermal: thermal already calls this addon, and the reverse call
// would close a dependency cycle.
private _snowDepth = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];
if !(_snowDepth isEqualType 0) then { _snowDepth = 0; };
private _surfaceClass = "ground";
if (count _posASL >= 2) then {
    _surfaceClass = (surfaceType [_posASL select 0, _posASL select 1]) call EFUNC(material,classifyBySurfaceType);
};
private _C = [_surfaceClass, _snowDepth] call EFUNC(material,calculateStefanCoefficient);

if (_T < 0) then {
    // Accumulate freezing degree-hours, convert to degree-days.
    private _fddAdd = (0 - _T) * _dtH / 24;
    _fdd = _fdd + _fddAdd;
    _ice = _C * sqrt _fdd;
} else {
    // Above freezing: slow melt (thinner ice also refreezes faster).
    private _melt = 0.05 * _dtH;   // cm per hour of above-freezing
    _ice = (_ice - _melt) max 0;
    _fdd = (_fdd - 0.02 * _dtH) max 0;
};

_grid set [_key, [_fdd, _now, _ice, _snow24]];
missionNamespace setVariable [QGVAR(fddGrid), _grid];

// ─── Gold load equation ──────────────────────────────────────────────────
private _safeKg = 3.5 * (_ice ^ 2);       // clear ice, conservative
private _warnKg = _safeKg / 3;            // flexural reserve

// ─── Load state by the DNR table ─────────────────────────────────────────
private _state = 0;
if (_ice >= 51) then { _state = 5; } else {
    if (_ice >= 41) then { _state = 4; } else {
        if (_ice >= 28) then { _state = 3; } else {
            if (_ice >= 18) then { _state = 2; } else {
                if (_ice >= 10) then { _state = 1; };
            };
        };
    };
};

missionNamespace setVariable [QGVAR(iceThicknessCm), _ice];
missionNamespace setVariable [QGVAR(iceSafeKg), _safeKg];

[_ice, _safeKg, _warnKg, _state]
