#include "..\script_component.hpp"

if (!isClass (configFile >> "CfgPatches" >> "kat_circulation")) exitWith {};

private _coreAETemp = (missionNamespace getVariable ["aee_core_coreAETemp", 0]);
private _coreBodyTemp = (missionNamespace getVariable ["aee_core_coreBodyTemp", 0]);
private _bodyFluid = player getVariable ["kat_circulation_bodyFluid", 60];
private _dehyd = 0;

if (_coreAETemp > 15 || _coreBodyTemp > 37.5) then {
    _dehyd = 0.05 + (_coreAETemp - 15) * 0.002 + ((_coreBodyTemp - 37.5) max 0) * 0.01;
    private _newFluid = (_bodyFluid - _dehyd) max 20;
    player setVariable ["kat_circulation_bodyFluid", _newFluid];
};

if (_dehyd < 0.1 && _bodyFluid < 55) then {
    private _newFluid = (_bodyFluid + 0.05) min 60;
    player setVariable ["kat_circulation_bodyFluid", _newFluid];
};
