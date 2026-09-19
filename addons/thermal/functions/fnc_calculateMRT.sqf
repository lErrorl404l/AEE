#include "..\script_component.hpp"
/*
Mean Radiant Temperature (ISO 7726) - the radiation-exchange driver.

MRT is the uniform temperature of an imaginary enclosure in which the
radiant heat transfer from a body equals the radiant heat transfer in
the actual non-uniform environment (ISO 7726; Wikipedia "Mean radiant
temperature").  It is the area-weighted mean temperature of the
surrounding surfaces, and it - NOT the air temperature - drives the
net radiant exchange:

  q_rad = eps * sigma * (Ts^4 - MRT^4)

The old per-object and per-selection solvers exchanged radiation
against Tair.  That is physically wrong: on a sunny day the surrounding
surfaces (ground, other vehicles, buildings) sit far above air
temperature, so a body in sun keeps gaining radiant energy until its
surface approaches MRT, not Tair.  The black-globe thermometer exists
precisely because of this: it balances absorbed radiation against
convection, so its reading sits between Tair and MRT (the faster the
air moves, the closer to Tair).

For the AEE model the enclosure surfaces are:
  - ground (PER-POSITION, material-classified - asphalt absorbs far
    more than soil; fnc_calculateGroundTemperature)
  - sky (longwave sky temperature, a function of overcast)
  - nearby objects (objectTemperatures, already solved)

MRT is the area-weighted mean of these, weighted by view factor.  For
a body standing in the open with a half-space of ground and half-space
of sky (view factors 0.5 / 0.5 - ISO 7726 spherical/standing-person
approximation), plus a contribution from nearby warm objects whose
view factor falls with distance.

  MRT = F_ground * T_ground + F_sky * T_sky + sum(F_obj_i * T_obj_i)
  F_ground + F_sky + sum(F_obj) = 1

Per-selection view factors: a tyre/undercarriage selection sits ON the
ground (F_ground ~0.7, sky ~0.1); a roof selection sees the sky
(F_sky ~0.7, ground ~0.3); a weapon held by a soldier sees the body,
ground and sky.  The caller passes the ground view factor (0..1) and
the function splits the remainder between sky and objects.

Sky longwave temperature (Swinbank 1963, validated - a clear night sky
radiates at 0.0552 * Ta^1.5 K, far below air temperature; overcast sky
approaches air temperature because cloud bases are warm emitters):

  T_sky = 0.0552 * Ta_K^1.5 - 273.15     (clear sky, Swinbank 1963)
  blended toward Ta as overcast -> 1

Inputs come from the AEE environment state, so no new sensors are
invented: every value is already simulated (issue #124).

Input:
  0: position (ARRAY) - the ground point for the enclosure [optional,
     defaults to the current unit]
  1: ground view factor (NUMBER 0..1) - share of the enclosure taken
     by the ground; default 0.5 (standing person)
Output: MRT in degrees C (number)
*/

params [["_pos", [], [[]]], ["_fGround", 0.5, [0]]];
_fGround = _fGround max 0.05 min 0.9;

if !(missionNamespace getVariable [QEGVAR(core,enabled), true]) exitWith { missionNamespace getVariable [QEGVAR(core,currentTemperature), 15] };

private _tAir = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_tAir isEqualType 0) then { _tAir = 15; };

private _tGround = [_pos] call FUNC(calculateGroundTemperature);

// ─── Sky longwave temperature (Swinbank 1963) ─────────────────────────────
// T_sky = 0.0552 * Ta^1.5 (Kelvin) for a clear sky.  Overcast raises the
// effective sky emitter to near air temperature (cloud base is a warm
// blackbody), so blend by overcast 0..1.
private _tAirK = _tAir + 273.15;
private _tSkyClear = (0.0552 * (_tAirK ^ 1.5)) - 273.15;
private _tSky = _tAir + (_tSkyClear - _tAir) * (1 - overcast);
if (_tSky > _tAir) then { _tSky = _tAir; };  // sky can never be a warmer emitter than air

// ─── Nearby objects (radiant coupling, view-factor weighted) ──────────────
// The existing object-temperature solver already publishes per-object
// surface temperatures in EGVAR(core,objectTemperatures) as [obj, temp]
// pairs.  Only a small warm-bias contribution is taken here: a standing
// person or vehicle sees ~a half-space of sky+ground, and nearby large
// objects add their temperature weighted by a distance falloff.
private _objContrib = 0;
private _objFactor = 0;
private _unit = call CBA_fnc_currentUnit;
private _objs = missionNamespace getVariable [QEGVAR(core,objectTemperatures), []];
if (isNil "_objs") then { _objs = []; };
if (!isNil "_unit" && {count _objs > 0}) then {
    private _objPos = if (count _pos >= 3) then { _pos } else { getPosASL _unit };
    private _count = 0;
    {
        _x params ["_obj", "_temp"];
        if (isNil "_temp") then { continue; };
        if !(_temp isEqualType 0) then { continue; };
        if (_temp < -50 || _temp > 1000) then { continue; };
        private _d = _objPos distanceSqr getPosASL _obj;
        // View factor ~ solid angle: falls off as 1/d^2, capped.
        private _f = 1 / (1 + (_d / 40000));  // 200 m reference distance
        _objContrib = _objContrib + (_temp * _f);
        _objFactor = _objFactor + _f;
        _count = _count + 1;
        if (_count >= 8) exitWith {};
    } forEach _objs;
};

// ─── Area-weighted MRT (view factors sum to 1) ────────────────────────────
// The caller's ground view factor drives the split: a tyre selection
// sees mostly ground, a roof mostly sky.  Warm objects displace the
// sky share.
private _fObj = _objFactor min (1 - _fGround);
private _fSky = 1 - _fGround - _fObj;
if (_fSky < 0) then { _fSky = 0; };
if (_fObj > 0) then {
    private _meanObj = _objContrib / _objFactor;
    private _mrt = (_fGround * _tGround) + (_fSky * _tSky) + (_fObj * _meanObj);
    _mrt
} else {
    (_fGround * _tGround) + (_fSky * _tSky)
}
