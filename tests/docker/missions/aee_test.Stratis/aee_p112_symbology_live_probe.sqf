// PHASE 112: the live-marker-tracking kernels on the live world.
//
// The map and world marker layers exist only on a client, so the probe drives
// the REAL pure kernels with fixtures: the echelon ladder, the echelon-marker
// token map and the class-category to battle-dimension map. It also confirms
// the re-pointed simple classes resolve to a dimension-correct texture in the
// live config, and that the echelon overlay classes are registered.
//
// Emits one [P112] PASS/FAIL line.

private _fnEchelon = missionNamespace getVariable ["aee_optics_fnc_symbologyEchelon", nil];
private _fnEchelonMarker = missionNamespace getVariable ["aee_optics_fnc_symbologyEchelonMarker", nil];
private _fnDimension = missionNamespace getVariable ["aee_optics_fnc_symbologyDimension", nil];
if (isNil "_fnEchelon" || {isNil "_fnEchelonMarker"} || {isNil "_fnDimension"}) exitWith {
    diag_log text "[P112] [FAIL] live kernels not compiled (symbologyEchelon/symbologyEchelonMarker/symbologyDimension)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// 1. the echelon ladder: the band edges, monotone
private _echelonCases = [
    [1, "team"], [6, "squad"], [7, "section"], [13, "section"],
    [14, "platoon"], [40, "platoon"], [41, "company"], [300001, "region"]
];
{
    _x params ["_size", "_want"];
    private _got = [_size] call _fnEchelon;
    if (_got isEqualTo _want) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["echelon %1=%2 want %3", _size, _got, _want];
    };
} forEach _echelonCases;

// 2. the echelon-marker token map, including the underscore name
private _markerCases = [
    ["squad", "AEE_Ech_Squad"],
    ["army_group", "AEE_Ech_Army_Group"],
    ["region", "AEE_Ech_Region"],
    ["bogus", "AEE_Ech_Team"]
];
{
    _x params ["_token", "_want"];
    private _got = [_token] call _fnEchelonMarker;
    if (_got isEqualTo _want) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["echelonMarker %1=%2 want %3", _token, _got, _want];
    };
} forEach _markerCases;

// 3. the battle dimension per class category
private _dimensionCases = [
    ["rotary", "air"], ["fixed_wing", "air"], ["uav", "air"],
    ["sea_surface", "sea"], ["subsurface", "subsurface"],
    ["installation", "installation"], ["infantry", "land"], ["bogus", "land"]
];
{
    _x params ["_category", "_want"];
    private _got = [_category] call _fnDimension;
    if (_got isEqualTo _want) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["dimension %1=%2 want %3", _category, _got, _want];
    };
} forEach _dimensionCases;

// 4. every echelon class is a registered CfgMarkers class
{
    if (isClass (configFile >> "CfgMarkers" >> _x)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["echelon class not registered: %1", _x];
    };
} forEach ["AEE_Ech_Team", "AEE_Ech_Squad", "AEE_Ech_Army_Group", "AEE_Ech_Region"];

// 5. the re-pointed simple classes carry a dimension-correct texture
private _textureCases = [
    ["AEE_b_air", "AEE_FA_"], ["AEE_o_naval", "AEE_HS_"],
    ["AEE_n_plane", "AEE_NA_"], ["AEE_b_installation", "AEE_FI_"],
    ["AEE_n_uav", "AEE_NA_"]
];
{
    _x params ["_class", "_needle"];
    private _texture = getText (configFile >> "CfgMarkers" >> _class >> "texture");
    if ((_texture find _needle) >= 0) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["texture %1=%2 want a %3 texture", _class, _texture, _needle];
    };
} forEach _textureCases;

if (_fail == 0) then {
    diag_log text format ["[P112] [PASS] live marker kernels on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P112] [FAIL] live marker kernels: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
