// PHASE 111: the NATO/OPFOR symbology kernels on the live world.
//
// The map and world marker layers exist only on a client, so the probe drives
// the REAL pure kernels with fixtures: the palette (Table 1-4 and the OPFOR
// swap), the marker-type kernel, the marker-colour kernel and the category
// table.  It renders nothing and calls no engine draw command.
//
// Emits one [P111] PASS/FAIL line.

private _fnPalette = missionNamespace getVariable ["aee_optics_fnc_symbolPalette", nil];
private _fnType = missionNamespace getVariable ["aee_optics_fnc_symbologyMarkerType", nil];
private _fnColour = missionNamespace getVariable ["aee_optics_fnc_symbologyMarkerColor", nil];
private _fnCategory = missionNamespace getVariable ["aee_optics_fnc_symbolCategory", nil];
if (isNil "_fnPalette" || {isNil "_fnType"} || {isNil "_fnColour"} || {isNil "_fnCategory"}) exitWith {
    diag_log text "[P111] [FAIL] symbology kernels not compiled (symbolPalette/symbologyMarkerType/symbologyMarkerColor/symbolCategory)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// 1. the Table 1-4 palette: friend cyan, hostile red, neutral green, unknown yellow
private _nato = [
    ["friend", [0, 1, 1, 1]],
    ["hostile", [1, 0, 0, 1]],
    ["neutral", [0, 1, 0, 1]],
    ["unknown", [1, 1, 0, 1]]
];
{
    _x params ["_aff", "_want"];
    private _got = [_aff, "NATO"] call _fnPalette;
    if (_got isEqualTo _want) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["palette %1 NATO=%2 want %3", _aff, _got, _want];
    };
} forEach _nato;

// 2. the OPFOR palette swaps friend and hostile
private _friendOpfor = ["friend", "OPFOR"] call _fnPalette;
private _hostileOpfor = ["hostile", "OPFOR"] call _fnPalette;
if (_friendOpfor isEqualTo [1, 0, 0, 1] && {_hostileOpfor isEqualTo [0, 1, 1, 1]}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["OPFOR swap unexpected: friend=%1 hostile=%2", _friendOpfor, _hostileOpfor];
};

// 3. a hostile armour symbol is the real o_armor marker type
private _armorType = ["hostile", "armour"] call _fnType;
if (_armorType isEqualTo "AEE_o_armor") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["hostile armour marker type unexpected: %1", _armorType];
};

// 4. the marker colour class: hostile red, friend blue under NATO, swapped under OPFOR
private _natoHostile = ["hostile", "NATO"] call _fnColour;
private _natoFriend = ["friend", "NATO"] call _fnColour;
private _opforFriend = ["friend", "OPFOR"] call _fnColour;
private _opforHostile = ["hostile", "OPFOR"] call _fnColour;
if (_natoHostile isEqualTo "ColorEAST" && {_natoFriend isEqualTo "ColorWEST"}
    && {_opforFriend isEqualTo "ColorEAST"} && {_opforHostile isEqualTo "ColorWEST"}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["marker colour unexpected: natoH=%1 natoF=%2 opforF=%3 opforH=%4", _natoHostile, _natoFriend, _opforFriend, _opforHostile];
};

// 5. the category table maps the engine marker types to the class categories
private _infCategory = ["b_inf"] call _fnCategory;
private _armourCategory = ["o_armor"] call _fnCategory;
if (_infCategory isEqualTo "infantry" && {_armourCategory isEqualTo "armour"}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["category table unexpected: b_inf=%1 o_armor=%2", _infCategory, _armourCategory];
};

if (_fail == 0) then {
    diag_log text format ["[P111] [PASS] symbology kernels on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P111] [FAIL] symbology kernels: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
