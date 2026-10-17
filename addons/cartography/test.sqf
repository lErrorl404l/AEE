#include "script_component.hpp"

/*
cartography component test (aee_diagnostics_fnc_test).

Headless-safe: asserts the merged engine config and pure kernels only.  It uses
no camera, no display and no client-only gate, so a dedicated server runs it.
Emits CBA-style TEST: OK/FAIL lines and publishes the failure count to
aee_test_failures_cartography.
*/

private _failures = 0;

private _check = {
    params ["_name", "_pass", "_detail"];
    private _line = [
        format ["TEST: OK - %1", _name],
        format ["TEST: FAIL - %1: %2", _name, _detail]
    ] select !_pass;
    diag_log text _line;
    [1, 0] select _pass
};

private _arrEq = {
    params ["_a", "_b"];
    if ((count _a) != (count _b)) exitWith { false };
    private _ok = true;
    {
        if (abs ((_a select _forEachIndex) - _x) > 1e-6) then { _ok = false; };
    } forEach _b;
    _ok
};

// ── The palette AEE declares in config_mapcolors.hpp, read live from the
// merged RscMapControl surface. ───────────────────────────────────────────
private _rsc = configFile >> "RscMapControl";
private _paletteCases = [
    ["colorSea", [0.55, 0.70, 0.85, 1]],
    ["colorForest", [0.55, 0.74, 0.44, 1]],
    ["colorLevels", [0.70, 0.48, 0.32, 1]],
    ["colorMainRoads", [0.70, 0.00, 0.00, 1]],
    ["colorMainCountlines", [0.45, 0.26, 0.12, 1]],
    ["colorCountlines", [0.62, 0.42, 0.22, 1]]
];
{
    _x params ["_key", "_want"];
    private _got = getArray (_rsc >> _key);
    _failures = _failures + ([
        "palette " + _key,
        [_got, _want] call _arrEq,
        format ["got %1 want %2", _got, _want]
    ] call _check);
} forEach _paletteCases;

// ── The engine grid is off: colorGrid is the edge-number colour and
// colorGridMap the in-map line colour, both alpha 0 (ADR-030). ────────────
private _gridNumbers = getArray (_rsc >> "colorGrid");
private _gridLines = getArray (_rsc >> "colorGridMap");
_failures = _failures + ([
    "colorGrid alpha 0",
    ((count _gridNumbers) >= 4) && {(_gridNumbers select 3) == 0},
    str _gridNumbers
] call _check);
_failures = _failures + ([
    "colorGridMap alpha 0",
    ((count _gridLines) >= 4) && {(_gridLines select 3) == 0},
    str _gridLines
] call _check);

// ── The legend.  Build the palette exactly as fnc_mgrsMapDraw.sqf does: the
// six map swatches come from the live RscMapControl, the nine group swatches
// from the generated terrain registry. ────────────────────────────────────
private _palette = [
    ["relief_brown", getArray (_rsc >> "colorLevels")],
    ["water_blue", getArray (_rsc >> "colorSea")],
    ["vegetation_green", getArray (_rsc >> "colorForest")],
    ["transport_red", getArray (_rsc >> "colorMainRoads")],
    ["contour_index", getArray (_rsc >> "colorMainCountlines")],
    ["contour_intermediate", getArray (_rsc >> "colorCountlines")]
];
private _symbols = missionNamespace getVariable ["aee_cartography_terrainTables", []];
if ((count _symbols) > 0) then { _symbols = _symbols select 0; };
{
    _x params ["_groupKey", "_category"];
    private _groupColour = [];
    {
        if ((_x select 1) == _category) exitWith { _groupColour = _x select 3; };
    } forEach _symbols;
    if ((count _groupColour) == 4) then { _palette pushBack [_groupKey, _groupColour]; };
} forEach [
    ["group_relief", "relief"],
    ["group_vegetation", "vegetation"],
    ["group_hydrography", "hydrography"],
    ["group_populated", "populated"],
    ["group_works", "works"],
    ["group_transport", "transport"],
    ["group_boundary", "boundary"],
    ["group_control", "control"],
    ["group_military", "military"]
];

private _fnLegend = missionNamespace getVariable ["aee_cartography_fnc_mapLegendDraw", nil];
_failures = _failures + ([
    "mapLegendDraw compiled",
    !isNil "_fnLegend",
    "aee_cartography_fnc_mapLegendDraw not compiled"
] call _check);
if (!isNil "_fnLegend") then {
    private _rows = [_palette] call _fnLegend;
    _failures = _failures + ([
        "legend one row per group",
        (count _rows) == 15,
        format ["%1 rows, want 15", count _rows]
    ] call _check);
    // ADR-044: the legend and the map share one source, so each of the six
    // map-derived swatches equals its RscMapControl colour.
    {
        private _swatch = (_rows param [_forEachIndex, []]) param [0, []];
        _failures = _failures + ([
            "legend swatch " + _x,
            [_swatch, _palette select _forEachIndex select 1] call _arrEq,
            format ["swatch %1", _swatch]
        ] call _check);
    } forEach ["relief_brown", "water_blue", "vegetation_green", "transport_red", "contour_index", "contour_intermediate"];
};

missionNamespace setVariable ["aee_test_failures_cartography", _failures];
diag_log text "[AEE-TEST] cartography DONE";
