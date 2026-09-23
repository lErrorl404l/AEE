#include "..\..\script_component.hpp"

/*
Author: AEE
Description: Computes time-based hypoxia risk from equivalent oxygen altitude.
Risk is the ratio of accumulated exposure to the Time of Useful Consciousness
(TUC) for the current altitude.
Arguments: None
Return Value: NUMBER: hypoxia risk 0..1
Example: [] call aee_physiology_fnc_calculateHypoxia
Public: No
*/

private _player = call CBA_fnc_currentUnit;
private _uid = "";
private _altASL = 0;
if (!isNil "_player" && {!isNull _player}) then {
    _uid = getPlayerUID _player;
    _altASL = (getPosASL _player) select 2;
};

// ─── Equivalent oxygen altitude ──────────────────────────────────────────
// ISA hypsometric relation converts ambient pressure (hPa) to the altitude
// that has the same oxygen partial pressure.  Fall back to true ASL when no
// pressure state is present.
private _pressure = missionNamespace getVariable [QEGVAR(core,currentPressure), 0];
private _eqAlt = _altASL;
if (_pressure > 0) then {
    _eqAlt = 44330 * (1 - ((_pressure / 1013.25) ^ 0.1903));
};

// ─── Time of Useful Consciousness (FAA table) ────────────────────────────
// Linear interpolation over the standard TUC points.  Below 6000 m the TUC is
// effectively infinite (over 30 min), so the risk stays near zero.
private _tucTable = [
    [6000, 1800],
    [7000, 240],
    [8000, 120],
    [9000, 45],
    [10000, 15]
];
private _tuc = 1e9;
if (_eqAlt >= 6000) then {
    _tuc = 15;
    for "_i" from 0 to ((count _tucTable) - 2) do {
        private _lo = _tucTable select _i;
        private _hi = _tucTable select (_i + 1);
        if (_eqAlt >= (_lo select 0) && _eqAlt <= (_hi select 0)) then {
            private _frac = (_eqAlt - (_lo select 0)) / ((_hi select 0) - (_lo select 0));
            _tuc = (_lo select 1) + _frac * ((_hi select 1) - (_lo select 1));
        };
    };
    _tuc = _tuc max 15;
};

// ─── Exposure accumulation (per-player) ──────────────────────────────────
private _exposureMap = missionNamespace getVariable [QGVAR(hypoxiaExposure), createHashMap];
private _exposure = _exposureMap getOrDefault [_uid, 0];
private _tickSeconds = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];

if (_eqAlt > 6000) then {
    _exposure = _exposure + _tickSeconds;
} else {
    // Below 6000 m the body recovers slowly.  Residual exposure shortens the
    // next onset if the unit climbs again.
    _exposure = (_exposure - _tickSeconds * GVAR(HypoxiaRecovery)) max 0;
};

// ─── Risk: exposure relative to the TUC ──────────────────────────────────
private _risk = ((_exposure / _tuc) min 1) max 0;

_exposureMap set [_uid, _exposure];
missionNamespace setVariable [QGVAR(hypoxiaExposure), _exposureMap];
missionNamespace setVariable [QGVAR(hypoxiaTUC), _tuc];
missionNamespace setVariable [QEGVAR(core,currentHypoxiaRisk), _risk];

_risk
