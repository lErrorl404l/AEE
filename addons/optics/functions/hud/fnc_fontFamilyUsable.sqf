#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_fontFamilyUsable
 *
 * Test a CfgFontFamilies family for real use.  A declared class does not
 * prove the glyph files ship.  The AEE families need the FontToTGA operator
 * step, and the engine draws NO text for a family whose .fxy and .paa are
 * absent.  So every caller tests the family before it uses the name.
 *
 * Arguments:
 *   0: _family <STRING> a CfgFontFamilies class name
 *
 * Return: <BOOL> true when the family's first glyph .fxy exists
 */
params [["_family", "", [""]]];
if (_family isEqualTo "") exitWith { false };

private _fonts = getArray (configFile >> "CfgFontFamilies" >> _family >> "fonts");
private _usable = false;
if ((_fonts isEqualType []) && ((count _fonts) >= 1)) then {
    private _first = _fonts select 0;
    // An entry is a path string, or a three-element array of Latin, CJK and
    // fallback paths (docs/wiki/research/arma-font-surface.md).  Test the
    // Latin path either way.
    if ((_first isEqualType []) && {(count _first) >= 1}) then {
        _first = _first select 0;
    };
    if (_first isEqualType "") then {
        _usable = fileExists (_first + ".fxy");
    };
};

_usable
