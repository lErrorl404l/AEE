// PHASE 111: the NATO/OPFOR symbology kernels on the live world.
//
// The map and world draw layers exist only on a client, so the probe drives
// the REAL pure kernels with fixtures: the palette (Table 1-4 and the OPFOR
// swap), the frame grammar, the inner glyphs, the resolver and the category
// table.  It renders nothing and calls no engine draw command.
//
// Emits [P111] PASS/FAIL lines.

private _fnPalette = missionNamespace getVariable ["aee_optics_fnc_symbolPalette", nil];
private _fnFrame = missionNamespace getVariable ["aee_optics_fnc_symbolFrame", nil];
private _fnIcon = missionNamespace getVariable ["aee_optics_fnc_symbolIcon", nil];
private _fnResolve = missionNamespace getVariable ["aee_optics_fnc_symbolResolve", nil];
private _fnCategory = missionNamespace getVariable ["aee_optics_fnc_symbolCategory", nil];
if (isNil "_fnPalette" || {isNil "_fnFrame"} || {isNil "_fnIcon"} || {isNil "_fnResolve"} || {isNil "_fnCategory"}) exitWith {
    diag_log text "[P111] [FAIL] symbology kernels not compiled (symbolPalette/symbolFrame/symbolIcon/symbolResolve/symbolCategory)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// 1. the hostile NATO colour is the Table 1-4 red
private _hostileNato = ["hostile", "NATO"] call _fnPalette;
if (_hostileNato isEqualTo [1, 0, 0, 1]) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["hostile NATO colour unexpected: %1", _hostileNato];
};

// 2. the OPFOR palette swaps friend to the Table 1-4 red
private _friendOpfor = ["friend", "OPFOR"] call _fnPalette;
if (_friendOpfor isEqualTo [1, 0, 0, 1]) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["friend OPFOR colour unexpected: %1", _friendOpfor];
};

// 3. the resolver returns the diamond frame and the red colour for a
//    hostile armour symbol
private _spec = ["east", "armour", "hostile", "squad", "NATO"] call _fnResolve;
private _shape = _spec select 1;
private _colour = _spec select 3;
if (_shape isEqualTo "diamond" && {_colour isEqualTo [1, 0, 0, 1]}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["hostile armour spec unexpected: shape=%1 colour=%2", _shape, _colour];
};

// 4. the friendly air frame carries a domed top edge
private _airFrame = ["friend", "air"] call _fnFrame;
private _top = _airFrame select 0;
private _domed = false;
{
    if ((_x select 1) > 0.6) then { _domed = true; };
} forEach _top;
if (_domed) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "friendly air frame has no domed top edge";
};

// 5. the infantry glyph is two crossed lines
private _infantry = ["infantry"] call _fnIcon;
private _crossed = (count _infantry) == 2;
if (_crossed) then {
    {
        if ((_x select 0) != "line") then { _crossed = false; };
    } forEach _infantry;
};
if (_crossed) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["infantry glyph unexpected: %1", _infantry];
};

// 6. the unknown glyph is empty
private _unknown = ["unknown"] call _fnIcon;
if ((count _unknown) == 0) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["unknown glyph is not empty: %1", _unknown];
};

// 7. the category table maps b_inf to infantry
private _infCategory = ["b_inf"] call _fnCategory;
if (_infCategory isEqualTo "infantry") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["b_inf category unexpected: %1", _infCategory];
};

// 8. the category table maps o_armor to armour
private _armourCategory = ["o_armor"] call _fnCategory;
if (_armourCategory isEqualTo "armour") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["o_armor category unexpected: %1", _armourCategory];
};

diag_log text format ["[P111] symbology: hostile NATO=%1 friend OPFOR=%2 spec=%3 air top points=%4 b_inf=%5 o_armor=%6", _hostileNato, _friendOpfor, _spec, count _top, _infCategory, _armourCategory];

if (_fail == 0) then {
    diag_log text format ["[P111] [PASS] symbology kernels on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P111] [FAIL] symbology kernels: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
