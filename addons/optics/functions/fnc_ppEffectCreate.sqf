#include "..\script_component.hpp"

/*
Creates the persistent post-process effect handles used by the FX layer.

Arma 2.22 rejects the string-LHS form ("ChromAberration" ppEffectAdjust ...)
with "Type Number, expected Number" — the LHS must be the numeric handle
returned by ppEffectCreate.  This function creates five effects once
at init and stores the handles in missionNamespace:

  QGVAR(ppHandle_ChromAberration)
  QGVAR(ppHandle_DynamicBlur)
  QGVAR(ppHandle_ColorCorrections)
  QGVAR(ppHandle_FilmGrain)
  QGVAR(ppHandle_NVG_Grain)

LightShafts is NOT created here: it is an advanced post-process effect
(BIS wiki) that ppEffectCreate cannot create (returns -1); fnc_applySolarGlareFX
uses the string-LHS form for it directly.

Two FilmGrain instances exist: the night-grain handle at 2000 and the NVG
tube-grain handle at 1200.  The second stores under its own variable so it
does not overwrite the first.  Each handle gets a unique priority; the bump
loop guards against a priority collision.  Called once from XEH_preInit.

Sets: the five ppHandle_* variables.  Returns: nothing.
*/

private _effects = [
    ["ChromAberration", 3000],
    ["DynamicBlur", 4000],
    ["ColorCorrections", 5000],
    ["FilmGrain", 2000],
    ["FilmGrain", 1200]
    // LightShafts is deliberately absent: it is an ADVANCED effect (BIS
    // wiki) that cannot be created by ppEffectCreate (returns -1) and is
    // adjusted via the string-LHS form in fnc_applySolarGlareFX.
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
    // Two FilmGrain instances exist: night grain at 2000 and NVG tube grain
    // at 1200.  The second must not overwrite the first handle, so it stores
    // under its own variable.
    private _varName = format [QGVAR(ppHandle_%1), _name];
    if (_name == "FilmGrain" && missionNamespace getVariable [_varName, -1] >= 0) then {
        _varName = QGVAR(ppHandle_NVG_Grain);
    };
    missionNamespace setVariable [_varName, _handle];
    diag_log text format ["[AEE] ppEffect handle %1 = %2", _varName, _handle];
} forEach _effects;
