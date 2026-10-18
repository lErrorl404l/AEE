#include "..\..\script_component.hpp"

/*
G-LOC visual consumer.

fnc_calculateGLOC stages the response and the altitude loop publishes
QGVAR(gLocStage).  This function is the consumer that turns that stage into
the narrowing view the real +Gz sequence produces, so the computed state is
visible instead of inert (issue #293).

It owns a RadialBlur post-process under its own scope and key through the
shared registry (aee_lib_fnc_createPPEffect).  RadialBlur is not one of the
effects fnc_managePostProcess and the base grade own, so this adds no second
owner of ColorCorrections, DynamicBlur, ChromAberration or FilmGrain.  That
is the advanced-effect conflict the registry exists to prevent.

The stage sequence is the one fnc_calculateGLOC cites (Whinnery & Forster
2013): greyout narrows the field first, blackout closes it further, and LOC
is the heaviest tunnel.

Reads:  QGVAR(gLocStage) 0 none / 1 greyout / 2 blackout / 3 LOC.
*/

if (!hasInterface) exitWith {};

private _stage = missionNamespace getVariable [QGVAR(gLocStage), 0];
if !(_stage isEqualType 0) then { _stage = 0; };
_stage = _stage max 0 min 3;

// Optics off, no live player, or a non-player camera: apply nothing and take
// the live effect down so a stale tunnel is never left on screen.
private _player = call CBA_fnc_currentUnit;
private _veh = vehicle _player;
private _off = (!(missionNamespace getVariable [QEGVAR(core,opticsEnabled), true]))
    || (isNil "_player") || (!alive _player)
    || (cameraOn != _player && {cameraOn != _veh});

private _handle = missionNamespace getVariable [QGVAR(gLocBlurHandle), -1];
if !(_handle isEqualType 0) then { _handle = -1; };

if (_off || _stage == 0) exitWith {
    if (_handle >= 0) then { _handle ppEffectEnable false; };
};

if (_handle < 0) then {
    // The registry keys idempotence on the scope and the key, so the handle is
    // cached here rather than beside a legacy mirror.
    _handle = ["altitude", "GLOCBlur", "RadialBlur", 1950, ""] call EFUNC(lib,createPPEffect);
    if (_handle >= 0) then {
        _handle ppEffectEnable true;
        missionNamespace setVariable [QGVAR(gLocBlurHandle), _handle];
    };
};
if (_handle < 0) exitWith {};

// RadialBlur takes [powerX, powerY, offsetX, offsetY].
private _severity = [0, 0.05, 0.15, 0.35] select _stage;
private _offset = [0, 0.02, 0.05, 0.10] select _stage;
_handle ppEffectAdjust [_severity, _severity, _offset, _offset];
_handle ppEffectCommit 0;
