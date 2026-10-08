#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_mgrsFontFamily
 *
 * Pick the map overlay font family.  Prefer the AEE family when its glyph
 * files ship, else the first usable engine family.  A missing optional font
 * must never blank the map, so the engine families are the fallback.  The AEE
 * families need the FontToTGA operator step
 * (docs/wiki/research/arma-font-surface.md).  Each candidate is tested for its
 * glyph files, because a declared CfgFontFamilies class does not prove they
 * exist.
 *
 * Arguments:
 *   0: _mono <BOOL> true selects the monospaced family (grid digits), false
 *      selects the label family
 *
 * Return: <STRING> a usable CfgFontFamilies class name
 */
params [["_mono", true, [true]]];
if !(_mono isEqualType true) then { _mono = true; };

private _aee = "AEEFont";
private _candidates = ["PuristaMedium", "RobotoCondensed", "TahomaB"];
if (_mono) then {
    _aee = "AEEFontMono";
    _candidates = ["EtelkaMonospacePro", "LucidaConsoleB", "TahomaB", "PuristaMedium"];
};

if ([_aee] call FUNC(fontFamilyUsable)) exitWith { _aee };

private _chosen = "";
{
    if (_chosen isEqualTo "") then {
        if ([_x] call FUNC(fontFamilyUsable)) then { _chosen = _x; };
    };
} forEach _candidates;

if (_chosen isEqualTo "") then { _chosen = "TahomaB"; };

_chosen
