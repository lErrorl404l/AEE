#include "..\..\script_component.hpp"

/*
Combat-stress and morale state driver (issue #110).

Reads the engine per-unit state, calls the pure kernels in aee_strain, and
publishes the derived psychology state.  It runs where the unit is local,
because getSuppression is a local command: on a dedicated server it covers the
server-local AI, on a client the player and the player's local group.

Per unit it publishes QGVAR(psychology), a fixed 8-element array (the PSY_I_*
indices in script_component.hpp).  It never writes an engine skill: setSkill
is global and would double-count the engine's own suppression response.  The
AI behaviour layer (#81) reads the array; this addon does not consume it.

Arguments: none.  Registered as a 1 Hz per-frame handler.

Returns:
  Number - the number of units processed
*/

if (!GVAR(combatStressEnabled)) exitWith { 0 };

private _units = allUnits select {
    local _x && {alive _x} && {_x isKindOf "CAManBase"}
};

private _missionBonus = missionNamespace getVariable [QGVAR(missionMoraleBonus), 0];
if !(_missionBonus isEqualType 0) then { _missionBonus = 0; };

private _count = 0;

{
    private _unit = _x;

    // Suppression: the engine value, 0 to 1.  -1 means disabled or
    // unavailable, so it is mapped to 0 (not treated as truthy).
    private _suppression = getSuppression _unit;
    if !(_suppression isEqualType 0) then { _suppression = 0; };
    if (_suppression < 0) then { _suppression = 0; };

    // Fatigue: the engine per-unit stamina fatigue, 0 to 1.  This is a
    // per-unit quantity, so it is correct for AI.  The player-only
    // aee_physiology_fatigueFactor is NOT used here.
    private _fatigue = getFatigue _unit;
    if !(_fatigue isEqualType 0) then { _fatigue = 0; };

    // Casualty ratio: the fraction of the group lost.  The initial strength
    // is cached on the group at first sight, because the engine removes
    // corpses from the group and the ratio would otherwise reset to zero.
    private _group = group _unit;
    private _members = units _group;
    private _initial = _group getVariable [QGVAR(initialStrength), -1];
    if !(_initial isEqualType 0) then { _initial = -1; };
    if (_initial < 0) then {
        _initial = count _members;
        _group setVariable [QGVAR(initialStrength), _initial];
    };
    private _alive = { alive _x } count _members;
    private _casualtyRatio = 0;
    if (_initial > 0) then { _casualtyRatio = 1 - _alive / _initial; };
    _casualtyRatio = _casualtyRatio min 1 max 0;

    private _courage = _unit skill "courage";
    if !(_courage isEqualType 0) then { _courage = 0.5; };
    private _spotDistance = _unit skill "spotDistance";
    if !(_spotDistance isEqualType 0) then { _spotDistance = 0; };

    private _stress = [_suppression, _fatigue, _casualtyRatio] call EFUNC(strain,calculateStress);
    private _morale = [_casualtyRatio, _fatigue, _missionBonus] call EFUNC(strain,calculateMorale);
    private _multipliers = [_stress] call EFUNC(strain,getDecisionMultipliers);
    _multipliers params ["_reaction", "_accuracy", "_spotting", "_firingRate"];
    private _effectiveSpotting = [_spotDistance, _spotting] call EFUNC(strain,calculateEffectiveSpotting);
    private _action = [_morale, _courage] call EFUNC(strain,getMoraleAction);

    _unit setVariable [QGVAR(psychology), [
        _stress, _morale, _reaction, _accuracy, _spotting,
        _firingRate, _effectiveSpotting, _action
    ]];

    _count = _count + 1;
} forEach _units;

missionNamespace setVariable [QGVAR(psychologyUnits), _count];

_count
