#include "..\..\script_component.hpp"

/*
Rotor downwash visual from AEE's rotor physics (issue #141).

`setLocalWindParams [strength, diameter]` sets the visual rotor wash:
blown particles, the vegetation wind effect and the affected area.  It is
NOT the local wind field query (fnc_getLocalWind); it drives the renderer
only.

The strength is the momentum-theory induced velocity of the nearest
helicopter's rotor, the same model fnc_calculateDownwash uses:
  v_i = sqrt( T / (2 * rho * A) ),  T = m g,  A = pi r^2
The diameter is twice the rotor-radius estimate used there.  When no
helicopter is near, the effect is disabled with the wiki's [0.0001, 0.0001]
pair; the command ignores zero values, so 0.0001 is the disable value.

Gate: client only, and only when a helicopter is in or near the player's
view (the player's own aircraft, or one within 100 m).  The scan runs only
when the player is not already in a helicopter, and only at the tick
cadence, so it is not a per-frame cost.

Reads:  QEGVAR(core,currentAirDensity)
Sets:   engine local wind visual (setLocalWindParams)
*/
if (!hasInterface) exitWith {};

private _g = 9.80665;
private _disableParam = 0.0001;

private _player = call CBA_fnc_currentUnit;
if (isNull _player) exitWith {};

private _heli = vehicle _player;
if (isNull _heli || {!(_heli isKindOf "Helicopter")}) then {
    private _near = _player nearEntities [["Helicopter"], 100];
    _heli = if (_near isNotEqualTo []) then { _near select 0 } else { objNull };
};

if (isNull _heli) exitWith {
    if (missionNamespace getVariable [QGVAR(localWindActive), false]) then {
        setLocalWindParams [_disableParam, _disableParam];
        missionNamespace setVariable [QGVAR(localWindActive), false];
    };
};

private _mass = getMass _heli;
if (_mass <= 0) exitWith {
    setLocalWindParams [_disableParam, _disableParam];
    missionNamespace setVariable [QGVAR(localWindActive), false];
};

private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
if !(_rho isEqualType 0) then { _rho = 1.225; };
_rho = (_rho max 0.1) min 1.5;

// Rotor radius: 3 m (light) to 11 m (heavy lift), the estimate
// fnc_calculateDownwash uses for the disc area.
private _radius = 3 + ((_mass / 12000) min 1) * 8;
private _diameter = 2 * _radius;

private _thrust = _mass * _g;
private _vInduced = sqrt (_thrust / (2 * _rho * pi * _radius * _radius));

setLocalWindParams [(_vInduced max _disableParam), _diameter];
missionNamespace setVariable [QGVAR(localWindActive), true];
