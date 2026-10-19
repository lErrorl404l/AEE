#include "..\..\script_component.hpp"
/*
Munition runtime lookup.

Function: aee_blast_fnc_getMunitionData.

This file is GENERATED. The generator tools/validation/gen_munition_data.py
writes it from the munition catalogue under data/munition/. Do not edit it
by hand. Edit the corpus and regenerate it.

A thin consumer of aee_blast_fnc_getMunitionMatch: it returns the value row
of a unique match, or an empty array. It reads no config value and returns
no default.

The row is
[totalMassKg, warheadMassKg, chargeMassKg, calibreMm, lengthMm, filling].
A zero or an empty string means the corpus holds no published figure for
that field, which is a statement about the sources, never an estimate.

Arguments:
  0: className (STRING, a CfgAmmo, CfgMagazines or CfgWeapons classname,
     default "")
*/
params [["_className", "", [""]]];
if (_className == "") exitWith { [] };

private _match = [_className] call FUNC(getMunitionMatch);
if (_match isEqualTo []) exitWith { [] };
_match select 5
