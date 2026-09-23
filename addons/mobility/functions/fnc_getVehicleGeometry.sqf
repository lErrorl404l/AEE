#include "..\script_component.hpp"

/*
Real wheel geometry for a vehicle, read from the vehicle itself (#117).

The engine does not expose tyre width, tyre diameter, wheel count, track
width or wheelbase as direct properties.  It exposes them two other ways,
and this function reads both rather than a hand-written class table:

  1. The CONFIG.  Every CarX vehicle declares its wheels under
     CfgVehicles >> Wheels >> wheel_<side>_<station>, and each declares
     `center` and `boundary` (the wheel centre and the tyre edge).  This is
     the primary source: real per-vehicle data, and it survives a model
     rename.  Source: the BI wiki Cars Config Guidelines; BI's own
     B_MRAP_01_F dump.

  2. The MODEL memory points, as the fallback.  The same wheel is named in
     the Memory LOD as wheel_<side>_<station>_axis and _bound.  These are
     engine-required on every CarX vehicle, so a mod cannot omit them.

SIDE AND STATION ORDER.  The name is wheel_<side>_<station>: 1 = left,
2 = right, station 1 = front.  This is taken from BI's own model dump
(wheel_1_1_axis and wheel_2_1_axis are the steered pair, so they differ in
the first index, and the first index is the side).  The Cars Config
Guidelines prose states the order the other way round; the model dump is
authoritative and the prose is not.

Derivation:
  track width   = distance between the left and right axes at one station
  wheelbase     = distance between the front and rear axes on one side
  tyre diameter = 2 * distance(axis, bound)   (the bound is the tyre edge)
  wheel count   = the number of distinct wheel stations found

Every value is sanity-checked against a physical band.  A value outside its
band means the points were not what the name suggests, so it is discarded
and the caller's default is used rather than a wrong number.  This is the
same guard fnc_measureBarrel uses for a weapon barrel.

Arguments:
  0: vehicle (OBJECT)

Return Value: ARRAY [trackWidth_m, wheelbase_m, tyreDiameter_m, wheelCount, source]
  source is "config", "model" or "none".
Example: [cursorObject] call aee_mobility_fnc_getVehicleGeometry
Public: No
*/

params [["_vehicle", objNull, [objNull]]];

private _track = 0;
private _base = 0;
private _tyre = 0;
private _count = 0;
private _source = "none";

if (isNull _vehicle) exitWith { [_track, _base, _tyre, _count, _source] };

private _type = typeOf _vehicle;
if (_type == "") exitWith { [_track, _base, _tyre, _count, _source] };

// The four standard stations, in the order [station, side] that the config
// and the model both use.  Only these four, so an extra wheel on a 6x6 does
// not distort the track width or the wheelbase.
private _stations = [
    ["wheel_1_1", 1, 1], ["wheel_1_2", 1, 2],
    ["wheel_2_1", 2, 1], ["wheel_2_2", 2, 2]
];

// Axis and bound positions, as [name, pos] pairs.  An array, not a hashmap:
// the repo uses no hashmap method calls, and the parser accepts this.
private _axisPos = [];
private _boundPos = [];

// ─── 1. Config route ─────────────────────────────────────────────────────
private _wheelsCfg = configFile >> "CfgVehicles" >> _type >> "Wheels";
if (isClass _wheelsCfg) then {
    {
        _x params ["_key"];
        private _wc = _wheelsCfg >> _key;
        if (isClass _wc) then {
            if (isArray (_wc >> "center")) then {
                _axisPos pushBack [_key, getArray (_wc >> "center")];
            };
            if (isArray (_wc >> "boundary")) then {
                _boundPos pushBack [_key, getArray (_wc >> "boundary")];
            };
        };
    } forEach _stations;
    if (_axisPos isNotEqualTo []) then { _source = "config"; };
};

// ─── 2. Model fallback ───────────────────────────────────────────────────
// The unary selectionNames form is the one the repo uses and the parser
    // accepts; the wheel points are then read by selectionPosition, which
    // searches the Memory LOD first.  The config route above is primary.
if (_source == "none") then {
    private _names = selectionNames _vehicle;
    if (_names isEqualType [] && {_names isNotEqualTo []}) then {
        {
            private _n = toLower _x;
            if (_n find "wheel_" == 0) then {
                private _nLen = count _n;
                private _isAxis = (_n find "_axis") == (_nLen - 5);
                private _isBound = (_n find "_bound") == (_nLen - 6);
                if (_isAxis || _isBound) then {
                    private _key = _n select [0, _nLen - ([5, 6] select _isBound)];
                    private _known = false;
                    { if ((_x select 0) == _key) then { _known = true; }; } forEach _stations;
                    if (_known) then {
                        private _pos = _vehicle selectionPosition [_x, "Memory"];
                        if (_pos isEqualType [] && {count _pos == 3}) then {
                            if (_isAxis) then { _axisPos pushBack [_key, _pos]; }
                            else { _boundPos pushBack [_key, _pos]; };
                        };
                    };
                };
            };
        } forEach _names;
        if (_axisPos isNotEqualTo []) then { _source = "model"; };
    };
};

if (_source == "none") exitWith { [_track, _base, _tyre, _count, _source] };

// ─── Helpers ─────────────────────────────────────────────────────────────
// Find a stored position by wheel name; [0,0,0] means "not declared".  A
// real point at the origin is indistinguishable, so membership was decided
// from the config or the selection list before this point.
private _posOf = {
    params ["_list", "_key"];
    private _found = [0, 0, 0];
    { if ((_x select 0) == _key) exitWith { _found = _x select 1; }; } forEach _list;
    _found
};

// ─── Derive the geometry ─────────────────────────────────────────────────
// Track width: left to right at the front station (1), else the rear (2).
private _fl = [_axisPos, "wheel_1_1"] call _posOf;
private _fr = [_axisPos, "wheel_2_1"] call _posOf;
private _rl = [_axisPos, "wheel_1_2"] call _posOf;
private _rr = [_axisPos, "wheel_2_2"] call _posOf;

if (_fl isNotEqualTo [0, 0, 0] && _fr isNotEqualTo [0, 0, 0]) then {
    _track = _fl vectorDistance _fr;
} else {
    if (_rl isNotEqualTo [0, 0, 0] && _rr isNotEqualTo [0, 0, 0]) then {
        _track = _rl vectorDistance _rr;
    };
};

// Wheelbase: front to rear on the left side (1), else the right (2).
if (_fl isNotEqualTo [0, 0, 0] && _rl isNotEqualTo [0, 0, 0]) then {
    _base = _fl vectorDistance _rl;
} else {
    if (_fr isNotEqualTo [0, 0, 0] && _rr isNotEqualTo [0, 0, 0]) then {
        _base = _fr vectorDistance _rr;
    };
};

// Tyre diameter: twice the axis-to-bound distance on any declared wheel.
{
    _x params ["_key", "_ap"];
    private _bp = [_boundPos, _key] call _posOf;
    if (_bp isNotEqualTo [0, 0, 0]) then {
        _tyre = (_ap vectorDistance _bp) * 2;
    };
} forEach _axisPos;

// Wheel count: the number of declared wheel stations.
_count = count _axisPos;

// ─── Physical bands ──────────────────────────────────────────────────────
// A value outside its band means the points were not what the name
// suggests, so it is discarded rather than used.
if !(_track > 0.8 && _track < 4.0) then { _track = 0; };
if !(_base > 1.0 && _base < 8.0) then { _base = 0; };
if !(_tyre > 0.2 && _tyre < 2.0) then { _tyre = 0; };

[_track, _base, _tyre, _count, _source]
