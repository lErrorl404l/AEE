#include "..\script_component.hpp"

/*
Creates the persistent post-process effect handles used by the FX layer.

Arma 2.22 rejects the string-LHS form ("ChromAberration" ppEffectAdjust ...)
with "Type Number, expected Number" — the LHS must be the numeric handle
returned by ppEffectCreate.  This function creates all five effects once
at init and stores the handles in missionNamespace:

  QGVAR(ppHandle_ChromAberration)
  QGVAR(ppHandle_DynamicBlur)
  QGVAR(ppHandle_ColorCorrections)
  QGVAR(ppHandle_FilmGrain)
  QGVAR(ppHandle_LightShafts)

Each handle is created with an increasing priority so no effect is
rejected for a priority collision.  Called once from XEH_postInit.

Sets: the five ppHandle_* variables.  Returns: nothing.
*/

private _effects = [
    ["ChromAberration", 3000],
    ["DynamicBlur", 4000],
    ["ColorCorrections", 5000],
    ["FilmGrain", 2000],
    ["LightShafts", 1500]
];

{
    _x params ["_name", "_priority"];
    private _handle = ppEffectCreate [_name, _priority];
    // ppEffectCreate returns -1 when the priority is taken; bump until it succeeds
    private _guard = 0;
    while {_handle < 0 && _guard < 100} do {
        _priority = _priority + 1;
        _handle = ppEffectCreate [_name, _priority];
        _guard = _guard + 1;
    };
    missionNamespace setVariable [format [QGVAR(ppHandle_%1), _name], _handle];
    diag_log text format ["[AEE] ppEffect handle %1 = %2", _name, _handle];
} forEach _effects;
