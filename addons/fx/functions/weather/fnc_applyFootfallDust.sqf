#include "..\..\script_component.hpp"

/*
Infantry footfall kickup.

The engine throws dust for vehicles but NOT for a soldier on foot.  A
person running over dry ground lifts a visible trail of surface material;
walking lifts a little; on hardstanding or wet ground almost none.  This
adds that, from the ground the soldier is actually on.

Real behaviour this models:
  - Ground contact is periodic: each footfall strikes the ground once per
    stride.  Stride length is roughly proportional to speed, so the strike
    rate follows speed, not a fixed timer.
  - The material lifted is the SURFACE the foot lands on
    (fnc_surfaceMaterial): sand on sand, snow on snow, mud on mud.
  - The amount scales with speed (kinetic energy at impact), with the
    surface lift coefficient, and with moisture (a wet surface holds its
    particles).
  - Puff size scales with the material's lightness: a snow puff is larger
    and lasts longer than a wet clay clod.

Gate: enabled, unit on foot, moving above walking pace, on a surface that
lifts.  One source per unit, budget-checked.

Argument:
  0: unit (OBJECT, default the current unit)

Returns true when a source was started.
*/

params [["_unit", call CBA_fnc_currentUnit, [objNull]]];
if (isNull _unit || !alive _unit) exitWith { false };
if (!(EGVAR(core,enabled)) || !(GVAR(enabled))) exitWith { false };

// On foot only: a vehicle already has its own kickup.
if (!isNull objectParent _unit) exitWith { false };

private _speed = speed _unit;                 // km/h
if (_speed < 5) exitWith { false };           // below a brisk walk

// One source per unit: the guard holds a running emitter back.
private _key = format [QGVAR(footfall_%1), netId _unit];
private _existing = missionNamespace getVariable [_key, objNull];
if (!isNull _existing && alive _existing) exitWith { false };

if !([] call FUNC(checkParticleBudget)) exitWith { false };

// ─── Ground under the soldier ─────────────────────────────────────────────
private _pos = getPosASL _unit;
private _ground = [_pos] call FUNC(surfaceSample);
_ground params ["_material", "_colour", "_density"];

// Hardstanding and water do not kick up a visible plume.
if (_density < 0.15) exitWith { false };

// ─── Moisture holds the particles down ────────────────────────────────────
private _suppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 0.6];
if !(_suppression isEqualType 0) then { _suppression = 0.6; };
if (_suppression < 0.05) exitWith { false };

// ─── Speed -> impact energy -> amount lifted ──────────────────────────────
// Walk 5 km/h lifts a little; sprint 20 km/h lifts several times more.
// The kinetic term is quadratic, so the visible amount grows faster than
// the pace, which is what a real trail does.
private _speedMs = _speed / 3.6;
private _energy = _speedMs * _speedMs;
private _walkEnergy = (5 / 3.6) ^ 2;
private _amount = (_energy / _walkEnergy) * _density * _suppression;

private _params = [_material, _density, _colour, _pos] call FUNC(kickupParams);
_params params ["_weight", "_volume", "_rubbing", "_bounce", "_pcolor"];

// Alpha from the amount; the material lightness sets the puff size.
private _alpha = (0.05 + _amount * 0.06) min 0.35;
private _sizeScale = switch (_material) do {
    case "snow":   { 1.6 };
    case "dust":   { 1.2 };
    case "sand":   { 1.0 };
    case "dirt":   { 0.9 };
    case "gravel": { 0.6 };
    default        { 1.0 };
};

// ─── Source at the feet, at ground level ──────────────────────────────────
private _source = "#particlesource" createVehicleLocal _pos;
missionNamespace setVariable [_key, _source];
_source call FUNC(registerParticleSource);

_source setParticleCircle [0.25, [0, 0, 0]];
_source setParticleRandom [0.15, [0.25, 0.25, 0], [0.1, 0.1, 0.05], 0, 0.1, [0, 0, 0, 0], 0, 0];
_source setParticleParams [
    ["\A3\data_f\ParticleEffects\Universal\Universal.p3d", 16, 12, 9, 0],
    "",
    "Billboard",
    1,
    1.2 + _sizeScale * 0.4,                    // lifetime grows with size
    [0, 0, 0],
    [0, 0, 0.15],
    0,
    _weight,
    _volume,
    _rubbing,
    [0.15 * _sizeScale, 0.35 * _sizeScale],
    [[_pcolor select 0, _pcolor select 1, _pcolor select 2, _alpha],
     [_pcolor select 0, _pcolor select 1, _pcolor select 2, 0]],
    [0.5],
    1,
    0,
    "",
    "",
    _unit,
    0,
    true,
    _bounce
];

// One strike per stride: the stride shortens as the pace drops, so the
// interval follows speed rather than the frame.
private _interval = (1.6 / (_speed / 3.6)) max 0.12;
_source setDropInterval _interval;

// The source follows the soldier for one stride train, then expires.
[_source, _unit, _key] spawn {
    params ["_source", "_unit", "_key"];
    private _ttl = 0.6;
    while { _ttl > 0 && alive _source && alive _unit } do {
        _source setPosASL (getPosASL _unit);
        private _ground = [getPosASL _unit] call FUNC(surfaceSample);
        if ((_ground select 2) <= 0) exitWith {};
        sleep 0.1;
        _ttl = _ttl - 0.1;
    };
    deleteVehicle _source;
    missionNamespace setVariable [_key, nil];
};

true
