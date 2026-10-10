#include "..\..\script_component.hpp"
/*
Unit mass: the body plus the carried load (issue #160; reused by the shot
response of issue #161).

The body mass is the 70 kg reference man of the blast model (Bowen 1968;
the same reference the injury kernel uses).  The carried load is the
equipment library's combined weight (issue #119), the same sum the
movement coupling reads.  No new mass model is added.

Input:  [_unit]
Output: mass kg
*/
params [["_unit", objNull, [objNull]]];

private _body = 70;   // kg, Bowen 1968 reference man

private _load = 0;
if (!isNull _unit) then {
    private _equip = [_unit] call FUNC(getEquipmentProperties);
    if (_equip isEqualType [] && {(count _equip) > 5}) then {
        _load = (_equip select 5) select 0;
    };
};
if !(_load isEqualType 0) then { _load = 0; };

_body + (_load max 0)
