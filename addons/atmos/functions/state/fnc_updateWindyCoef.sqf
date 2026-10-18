#include "..\..\script_component.hpp"

/*
Wind aloft to the engine wind-howl coefficient (issue: unused weather levers).

`enableEnvironment [ambientLife, ambientSound, windyCoef]` sets the howling
wind at heights, range 0..1, default 1 (`windyCoef` since Arma 3 2.12;
command DB `enableEnvironment`, acemod/arma3-wiki v2.22).  The engine has no
wind-aloft vector (`wind` is [x, y, 0], command DB), so this coefficient is
the only lever for how a modelled wind at height sounds.

THE WIND.  The value is the modelled wind speed at the observer's height above
ground, sampled from FUNC(getLocalWind) (the spatial wind field, which returns
the global vector above the surface layer and applies the near-surface and
terrain terms below it).  The fallback is aee_core_currentWindStr, the surface
wind magnitude the wind owner publishes.  The engine applies `windyCoef` AT
HEIGHTS, so the height dependence of the sound is the engine's and AEE
supplies the modelled strength.

THE MAPPING.  The engine states only the 0..1 range, no metre scale, so the
m/s anchor is an AEE modelling choice and is marked UNSOURCED against the
engine: 25 m/s is a storm (Beaufort 10 lower bound 24.5 m/s, the maritime
Beaufort table AEE already holds).  The coefficient saturates at storm force.

THE OTHER TWO ELEMENTS.  AEE does not own ambient life or ambient sound, so
the bridge passes the current engine state (`environmentEnabled`) for both.
Passing `true` would re-enable ambient life a mission or an operator turned
off.

Reads:  aee_core_currentWindStr, current unit position and height
Sets:   engine windyCoef (enableEnvironment [.., .., windyCoef]), client-local
Example: [] call aee_atmos_fnc_updateWindyCoef;
Public: No
*/

if (!hasInterface) exitWith {};

// ─── Modelled wind at the observer's height (m/s) ───────────────────────────
private _windMs = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];
if !(_windMs isEqualType 0) then { _windMs = 0; };

private _unit = call CBA_fnc_currentUnit;
if (!isNil "_unit" && {!isNull _unit}) then {
    private _posASL = getPosASL _unit;
    private _agl = (_posASL select 2) - (getTerrainHeightASL _posASL);
    private _local = [_posASL, _agl max 0] call FUNC(getLocalWind);
    if (_local isEqualType [] && {(count _local) >= 2}) then {
        _windMs = vectorMagnitude [_local select 0, _local select 1, 0];
    };
};

// ─── 0..1 coefficient (the engine range; the m/s anchor is UNSOURCED) ───────
private _fullMs = 25;   // storm force (Beaufort 10 lower bound 24.5 m/s)
private _coef = (_windMs / _fullMs) max 0 min 1;

// The engine keeps the coefficient until the next call, so write on a change
// of more than one step of the 0..1 range.
private _last = missionNamespace getVariable [QGVAR(windyCoefPushed), -1];
if (_last isEqualType 0 && {(abs (_coef - _last)) < 0.01}) exitWith {};
missionNamespace setVariable [QGVAR(windyCoefPushed), _coef];

enableEnvironment [environmentEnabled, environmentEnabled, _coef];
