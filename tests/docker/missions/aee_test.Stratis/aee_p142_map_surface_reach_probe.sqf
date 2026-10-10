// PHASE 142: the AEE map-surface reach, asserted on the live merged config.
//
// The AEE topographic surface is one config include, config_mapcolors.hpp,
// carried by three re-declares: the base RscMapControl, the strategic map and
// the Eden ctrlMap.  The briefing and the GPS inherit RscMapControl, so the
// same include reaches them.  The minimap and the airborne minimap keep their
// own control (CA_MiniMap) and override part of the palette; the curator map
// inherits RscMapControl with no separate re-declare.  This probe reads the
// merged config on every named surface, asserts the AEE values on the surfaces
// AEE re-declares, and reports where the reach stops.  It changes no config
// and renders nothing.
//
// Emits one [P142] PASS/FAIL line.

private _pass = 0;
private _fail = 0;
private _notes = [];

// The AEE palette and scalars, read from addons/cartography/config_mapcolors.hpp.
private _palette = [
    ["colorBackground", "array", [0.90, 0.88, 0.80, 1]],
    ["colorSea", "array", [0.55, 0.70, 0.85, 1]],
    ["colorForest", "array", [0.55, 0.74, 0.44, 1]],
    ["colorMainCountlines", "array", [0.45, 0.26, 0.12, 1]],
    ["colorCountlines", "array", [0.62, 0.42, 0.22, 1]],
    ["maxSatelliteAlpha", "number", 0.5],
    ["drawShaded", "number", 0.15],
    ["shadedSea", "number", 1],
    ["sizeExLevel", "number", 0.04]
];

private _arrEq = {
    params ["_a", "_b", "_tol"];
    if ((count _a) != (count _b)) exitWith { false };
    private _ok = true;
    {
        if (abs ((_a select _forEachIndex) - _x) > _tol) then { _ok = false; };
    } forEach _b;
    _ok
};

// ── The three surfaces AEE re-declares directly. ────────────────────────
// A target that re-declares a field wins for that display, so each of these
// carries the full AEE surface from config_mapcolors.hpp.
private _direct = [
    ["RscMapControl", configFile >> "RscMapControl"],
    ["RscDisplayStrategicMap.Map", configFile >> "RscDisplayStrategicMap" >> "controlsBackground" >> "Map"],
    ["ctrlMap (Eden)", configFile >> "ctrlMap"]
];

{
    _x params ["_label", "_cfg"];
    if (isNull _cfg) then {
        _fail = _fail + 1;
        _notes pushBack format ["%1 config path not found", _label];
    } else {
        {
            _x params ["_key", "_kind", "_want"];
            private _ok = if (_kind == "array") then {
                [getArray (_cfg >> _key), _want, 1e-6] call _arrEq
            } else {
                abs ((getNumber (_cfg >> _key)) - _want) <= 1e-6
            };
            if (_ok) then {
                _pass = _pass + 1;
            } else {
                _fail = _fail + 1;
                _notes pushBack format ["%1 %2 = %3 (AEE %4)", _label, _key, str (getArray (_cfg >> _key)), str _want];
            };
        } forEach _palette;
        // The engine grid is off on every AEE surface: alpha 0 removes the
        // engine edge numbers and in-map lines, so the AEE MGRS overlay is the
        // single complete ruler.
        {
            private _a = (getArray (_cfg >> _x)) param [3, -1];
            if (_a == 0) then {
                _pass = _pass + 1;
            } else {
                _fail = _fail + 1;
                _notes pushBack format ["%1 %2 alpha = %3 (want 0)", _label, _x, _a];
            };
        } forEach ["colorGrid", "colorGridMap"];
        if (abs ((getNumber (_cfg >> "sizeExGrid")) - 0.04) <= 1e-6) then {
            _pass = _pass + 1;
        } else {
            _fail = _fail + 1;
            _notes pushBack format ["%1 sizeExGrid = %2 (want 0.04)", _label, getNumber (_cfg >> "sizeExGrid")];
        };
    };
} forEach _direct;

// ── The minimap controls AEE now re-declares. ───────────────────────────
// The engine minimap CA_MiniMap forces part of the palette (config_mapminimap.hpp
// names every unreachable field).  AEE re-declares the control for the fields
// the engine does NOT force, from config_mapminimap.hpp; this asserts that new
// reach on both the minimap and the airborne minimap.
private _reach = [
    ["colorOutside", "array", [0.90, 0.88, 0.80, 1]],
    ["colorInactive", "array", [1, 1, 1, 0.5]],
    ["colorForestTextured", "array", [0.45, 0.66, 0.34, 0.30]],
    ["colorNames", "array", [0.10, 0.10, 0.10, 0.90]],
    ["colorTrails", "array", [0.40, 0.30, 0.20, 1]],
    ["colorTrailsFill", "array", [0.90, 0.85, 0.75, 1]],
    ["fontLevel", "string", "RobotoCondensed"],
    ["sizeExLevel", "number", 0.04],
    ["ptsPerSquareSea", "number", 5],
    ["ptsPerSquareCLn", "number", 10],
    ["widthRailWay", "number", 4],
    ["shadedSea", "number", 1]
];

private _minimaps = [
    ["RscCustomInfoMiniMap.CA_MiniMap", configFile >> "RscCustomInfoMiniMap" >> "controls" >> "MiniMap" >> "Controls" >> "CA_MiniMap"],
    ["RscCustomInfoAirborneMiniMap.CA_MiniMap", configFile >> "RscCustomInfoAirborneMiniMap" >> "controls" >> "MiniMap" >> "Controls" >> "CA_MiniMap"]
];

{
    _x params ["_label", "_cfg"];
    if (isNull _cfg) then {
        _fail = _fail + 1;
        _notes pushBack format ["%1 config path not found", _label];
    } else {
        {
            _x params ["_key", "_kind", "_want"];
            private _ok = if (_kind == "array") then {
                [getArray (_cfg >> _key), _want, 1e-6] call _arrEq
            } else {
                if (_kind == "string") then {
                    (getText (_cfg >> _key)) == _want
                } else {
                    abs ((getNumber (_cfg >> _key)) - _want) <= 1e-6
                };
            };
            if (_ok) then {
                _pass = _pass + 1;
            } else {
                _fail = _fail + 1;
                _notes pushBack format ["%1 %2 (AEE reach)", _label, _key];
            };
        } forEach _reach;
        // The engine override still wins on the forced fields: record the
        // resolved values so the ceiling is visible in the log.
        diag_log text format [
            "[P142] minimap reach %1: seaA=%2 forestA=%3 clnMainA=%4 satAlpha=%5 drawShaded=%6 colorNamesA=%7 sizeExLevel=%8",
            _label,
            (getArray (_cfg >> "colorSea")) param [3, -1],
            (getArray (_cfg >> "colorForest")) param [3, -1],
            (getArray (_cfg >> "colorMainCountlines")) param [3, -1],
            getNumber (_cfg >> "maxSatelliteAlpha"),
            getNumber (_cfg >> "drawShaded"),
            (getArray (_cfg >> "colorNames")) param [3, -1],
            getNumber (_cfg >> "sizeExLevel")
        ];
    };
} forEach _minimaps;

// The curator map inherits RscMapControl, so the AEE surface reaches it with
// no separate re-declare.  Assert the control resolves.
private _curator = configFile >> "RscDisplayCurator" >> "ControlsBackground" >> "Map";
if (isNull _curator) then {
    _fail = _fail + 1;
    _notes pushBack "RscDisplayCurator.Map config path not found";
} else {
    _pass = _pass + 1;
};

// ── The AEE marker set resolves. ────────────────────────────────────────
// A representative generated class from the real Commons-derived APP-6 set.
if (isClass (configFile >> "CfgMarkers" >> "AEE_FL_Friendly_Unit_Infantry")) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "CfgMarkers >> AEE_FL_Friendly_Unit_Infantry missing";
};

// The AEE marker-apply function is compiled on every machine.  The
// disableMapIndicators call it makes is pinned at
// tools/tests/test_symbology.py:623; a script cannot read repo source, so the
// reach assertion is the compiled function's presence.
if (!isNil {missionNamespace getVariable ["aee_symbology_fnc_symbologyMarkersApply", nil]}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "aee_symbology_fnc_symbologyMarkersApply not compiled";
};

if (_fail == 0) then {
    diag_log text format ["[P142] [PASS] map surface reach on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P142] [FAIL] map surface reach: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
