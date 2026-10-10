// P119 marker inheritance probe (ADR-029).
//
// Three read-only assertions on the MERGED config:
//
//  1. Every engine CfgMarkers class AEE re-declares still reports its vanilla
//     scope.  A bare reopen makes the engine log "Updating base class <p>->''"
//     and "No entry ...scope" at load; a live non-zero scope proves the parent
//     was restated.
//  2. Each re-declared engine class draws the real AEE .paa under data/markers.
//  3. The AEE friendly markers carry the Friend category (the "friendly markers
//     went under unknown" defect).
//
// Emits one [P119] line. Writes no state.

private _pass = true;
private _notes = [];

// The engine classes AEE re-declares, with the vanilla scope to preserve.
private _scopes = [
    ["b_inf", 1],
    ["b_armor", 1],
    ["b_unknown", 1],
    ["o_recon", 1],
    ["n_inf", 1],
    ["n_unknown", 1],
    ["hd_dot", 2],
    ["mil_marker", 1],
    ["waypoint", 1]
];
private _scopeBad = 0;
{
    _x params ["_cls", "_min"];
    private _entry = configFile >> "CfgMarkers" >> _cls;
    if (isNull _entry) then {
        _scopeBad = _scopeBad + 1;
    } else {
        if ((getNumber (_entry >> "scope")) < _min) then { _scopeBad = _scopeBad + 1; };
    };
} forEach _scopes;
if (_scopeBad > 0) then { _pass = false; };
_notes pushBack format ["scope checked=%1 bad=%2", count _scopes, _scopeBad];

// Each re-declared engine class must draw the real AEE texture.
private _texBad = 0;
{
    private _tex = getText (configFile >> "CfgMarkers" >> _x >> "texture");
    if ((_tex find "\z\aee\addons\symbology\data\markers\") < 0) then {
        _texBad = _texBad + 1;
    };
} forEach ["b_inf", "o_armor", "n_recon", "hd_dot", "b_unknown"];
if (_texBad > 0) then { _pass = false; };
_notes pushBack format ["texture bad=%1", _texBad];

// The AEE friendly markers carry the Friend category.
private _friendBad = 0;
if !(isClass (configFile >> "CfgMarkerClasses" >> "AEE_Friend_Land")) then {
    _friendBad = _friendBad + 1;
};
{
    private _markerClass = getText (configFile >> "CfgMarkers" >> _x >> "markerClass");
    if !(_markerClass isEqualTo "AEE_Friend_Land") then { _friendBad = _friendBad + 1; };
} forEach ["AEE_b_inf", "AEE_b_armor", "AEE_b_hq"];
if (_friendBad > 0) then { _pass = false; };
_notes pushBack format ["friend bad=%1", _friendBad];

private _msg = _notes joinString " | ";
if (_pass) then {
    diag_log text format ["[P119] [PASS] marker inheritance %1", _msg];
} else {
    diag_log text format ["[P119] [FAIL] marker inheritance %1", _msg];
};
