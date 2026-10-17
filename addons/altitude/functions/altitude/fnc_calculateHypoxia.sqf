#include "..\..\script_component.hpp"

/*
Author: AEE
Description: Computes time-based hypoxia risk from equivalent oxygen altitude.
Risk is the ratio of accumulated exposure to the Time of Useful Consciousness
(TUC) for the current altitude.
Arguments: None
Return Value: NUMBER: hypoxia risk 0..1
Example: [] call aee_altitude_fnc_calculateHypoxia
Public: No
*/

private _player = call CBA_fnc_currentUnit;
private _uid = "";
private _altASL = 0;
if (!isNil "_player" && {!isNull _player}) then {
    _uid = getPlayerUID _player;
    _altASL = (getPosASL _player) select 2;
};

// ─── Ambient pressure at the BREATHING altitude ──────────────────────────
// aee_core_currentPressure is the STATION pressure at the terrain under the
// player (fnc_updatePressure), not the pressure the player breathes.  A
// pilot at 10 km over sea-level ground would read ~1013 hPa and never become
// hypoxic.  The weather pressure is carried up the standard atmosphere from
// the terrain to the player's altitude (ISA ratio, troposphere and isothermal
// stratosphere; fnc_calculateBarometricPressure), so a front still shifts it.
//
// A pressurised fixed-wing cabin holds at most 8,000 ft (2,438 m) cabin
// altitude (14 CFR 25.841(a)), and fast-jet crews breathe oxygen; a
// helicopter is unpressurised.  The equivalent altitude of a crew member in a
// Plane is therefore capped at 2,438 m.
private _breathAlt = _altASL;
if (!isNil "_player" && {!isNull _player} && {(vehicle _player) isKindOf "Plane"}) then {
    _breathAlt = _breathAlt min 2438;
};
private _terrainASL = 0;
if (!isNil "_player" && {!isNull _player}) then {
    _terrainASL = (getTerrainHeightASL (getPosASL _player)) max 0;
};
private _pressure = missionNamespace getVariable [QEGVAR(core,currentPressure), 0];
if !(_pressure isEqualType 0) then { _pressure = 0; };
private _pIsaBreath = [_breathAlt] call FUNC(calculateBarometricPressure);
private _pIsaGround = [_terrainASL min _breathAlt] call FUNC(calculateBarometricPressure);
private _pBreathHpa = if (_pressure > 0 && _pIsaGround > 0) then {
    _pressure * (_pIsaBreath / _pIsaGround)
} else {
    _pIsaBreath * 1000
};

// ─── Equivalent oxygen altitude ──────────────────────────────────────────
// The ISA altitude with the same pressure (and so the same inspired O2
// partial pressure): the inverse of the troposphere power law up to the
// tropopause (226.321 hPa at 11 km), the isothermal exponential above it.
private _eqAlt = if (_pBreathHpa >= 226.321) then {
    44330.8 * (1 - ((_pBreathHpa / ISA_SEA_LEVEL_PRESSURE_HPA) ^ 0.190263))
} else {
    11000 + (R_DRY_AIR * 216.65 / STANDARD_GRAVITY) * ln (226.321 / (_pBreathHpa max 1))
};

// ─── Time of Useful Consciousness ────────────────────────────────────────
// FAA AC 61-107B (Operations of Aircraft at Altitudes Above 25,000 Feet
// MSL), time of useful consciousness, the midpoint of each published range:
//   18,000 ft  20-30 min   22,000 ft  10 min      25,000 ft  3-5 min
//   28,000 ft  2.5-3 min   30,000 ft  1-2 min     35,000 ft  30-60 s
//   40,000 ft  15-20 s     45,000 ft  9-15 s      50,000 ft  9-12 s
// TUC falls roughly exponentially with altitude, so the table is
// interpolated in ln(TUC).  Below 18,000 ft the TUC is effectively
// unlimited and exposure does not accumulate; above 50,000 ft it holds the
// 50,000 ft value.
private _tucTable = [
    [5486, 1500],
    [6706, 600],
    [7620, 240],
    [8534, 165],
    [9144, 90],
    [10668, 45],
    [12192, 18],
    [13716, 12],
    [15240, 10.5]
];
private _onsetM = 5486;
private _tuc = 1e9;
if (_eqAlt >= _onsetM) then {
    _tuc = 10.5;
    for "_i" from 0 to ((count _tucTable) - 2) do {
        private _lo = _tucTable select _i;
        private _hi = _tucTable select (_i + 1);
        if (_eqAlt >= (_lo select 0) && _eqAlt <= (_hi select 0)) then {
            private _frac = (_eqAlt - (_lo select 0)) / ((_hi select 0) - (_lo select 0));
            _tuc = exp ((ln (_lo select 1)) + _frac * ((ln (_hi select 1)) - (ln (_lo select 1))));
        };
    };
};

private _exposureMap = missionNamespace getVariable [QGVAR(hypoxiaExposure), -1];
if (_exposureMap isEqualType 0) then {
    _exposureMap = createHashMap;
    missionNamespace setVariable [QGVAR(hypoxiaExposure), _exposureMap];
};
private _exposure = _exposureMap getOrDefault [_uid, 0];
private _tickSeconds = EGVAR(core,updateInterval);

if (_eqAlt > _onsetM) then {
    _exposure = _exposure + _tickSeconds;
} else {
    // Below 18,000 ft the body recovers slowly.  Residual exposure shortens the
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
