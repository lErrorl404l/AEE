#include "..\..\script_component.hpp"
/*
 * aee_core_fnc_runGeoConsistency
 *
 * Throttled positional consistency monitor.  It reads the published anchor
 * and world location, computes the remaining inputs through the core geo
 * kernels and the engine map grid, calls the pure evaluator
 * FUNC(evaluateGeoConsistency) and publishes aee_core_positionDivergence.
 *
 * It reads no player, calls no other module's function and writes no other
 * module's state.  The world centre is the probe position: it is derived
 * from the anchor mapSize, not from a unit.
 *
 * The engine map grid (mapGridPosition) is world X/Y, while MGRS is UTM.
 * The grid invariant compares the engine grid string of the anchor centre
 * with the engine grid string of the world position decoded from that
 * centre's MGRS.  A match proves the two sources agree on the world frame
 * at the engine grid precision.  On a UI-less machine both strings are
 * empty and the row passes vacuously; the other three rows still run.
 *
 * Registered as a per-frame handler in XEH_postInit, at the existing
 * environment interval.  That interval is the throttle: one check per
 * environment tick, not per frame.
 *
 * Return: the divergence flag <BOOL>.
 *
 * The table is declared in data/consistency/position_invariants.json.  The
 * rows below mirror that file; the contract test asserts the ids, predicates
 * and input keys agree.  Row order is [id, name, predicate, inputs, pairs,
 * tolerance, severity, grade, note].
 */
params [["_force", false, [false]]];

private _anchor = missionNamespace getVariable ["aee_core_geoAnchor", []];
if ((count _anchor) < 9) exitWith { false };

private _worldLocation = missionNamespace getVariable ["aee_core_worldLocation", []];

private _table = [
    [
        "GRID-AGREE",
        "engine_grid_agrees_with_mgrs",
        "pairs_equal",
        ["engineGridCentre", "engineGridFromMgrs"],
        [["engineGridCentre", "engineGridFromMgrs"]],
        0,
        "warn",
        "derived",
        "Engine map grid is world X/Y; MGRS encodes UTM.  The engine grid string of the anchor centre must equal that of the MGRS-decoded centre."
    ],
    [
        "ANCHOR-CENTRE",
        "anchor_centre_maps_to_anchor",
        "agree_within",
        ["anchorLat", "anchorLon", "projectedLat", "projectedLon"],
        [["anchorLat", "projectedLat"], ["anchorLon", "projectedLon"]],
        0.0001,
        "warn",
        "derived",
        "The world centre projected through the anchor box must equal the anchor centre.  The builder computes (latSouth+latNorth)/2 and the projector computes latSouth + 0.5*(latNorth-latSouth); the two are algebraically equal but about one ULP apart on the engine's 32-bit floats (about 2e-6 deg at lat 40), so the tolerance is 1e-4 deg, the demonstrated safe margin."
    ],
    [
        "WORLDLOC-ANCHOR",
        "world_location_equals_anchor",
        "agree_within",
        ["anchorLat", "anchorLon", "worldLocationLat", "worldLocationLon"],
        [["anchorLat", "worldLocationLat"], ["anchorLon", "worldLocationLon"]],
        0.000001,
        "error",
        "derived",
        "aee_core_worldLocation derives from the anchor, so its latitude and longitude must equal the anchor centre."
    ],
    [
        "MGRS-ROUNDTRIP",
        "mgrs_round_trips",
        "agree_within",
        ["centreX", "centreY", "roundtripX", "roundtripY", "easting", "northing", "parsedEasting", "parsedNorthing"],
        [["centreX", "roundtripX"], ["centreY", "roundtripY"], ["easting", "parsedEasting"], ["northing", "parsedNorthing"]],
        1.0,
        "error",
        "derived",
        "world -> MGRS -> world and format -> parse agree; MGRS truncates to the square south-west corner, so the residual is below one metre at ten digits."
    ]
];

private _mapSize = _anchor select 3;
private _centre = [_mapSize / 2, _mapSize / 2, 0];

private _engineGridCentre = mapGridPosition _centre;

private _written = [_centre, _anchor, 10] call FUNC(worldToMgrs);
private _mgrs = _written select 0;
private _projectedLat = _written select 1;
private _projectedLon = _written select 2;
private _easting = _written select 3;
private _northing = _written select 4;

private _roundtrip = [_mgrs, _anchor] call FUNC(mgrsToWorld);
private _engineGridFromMgrs = mapGridPosition _roundtrip;

private _parsed = [_mgrs] call FUNC(parseMgrs);
// A malformed format result near a zone edge leaves fewer than four elements.
// Treat it as a reported divergence, not a raw index error each PFH tick.
private _parsedEasting = -1;
private _parsedNorthing = -1;
if ((count _parsed) >= 4) then {
    _parsedEasting = _parsed select 0;
    _parsedNorthing = _parsed select 1;
};

private _values = [
    ["engineGridCentre", _engineGridCentre],
    ["engineGridFromMgrs", _engineGridFromMgrs],
    ["anchorLat", _anchor select 0],
    ["anchorLon", _anchor select 1],
    ["projectedLat", _projectedLat],
    ["projectedLon", _projectedLon],
    ["worldLocationLat", _worldLocation select 0],
    ["worldLocationLon", _worldLocation select 2],
    ["centreX", _centre select 0],
    ["centreY", _centre select 1],
    ["roundtripX", _roundtrip select 0],
    ["roundtripY", _roundtrip select 1],
    ["easting", _easting],
    ["northing", _northing],
    ["parsedEasting", _parsedEasting],
    ["parsedNorthing", _parsedNorthing]
];

private _result = [_table, _values] call FUNC(evaluateGeoConsistency);
private _divergence = _result select 0;
private _verdicts = _result select 1;

missionNamespace setVariable ["aee_core_positionDivergence", _divergence];
missionNamespace setVariable [QGVAR(positionVerdicts), _verdicts];

if (_force && !_divergence) then {
    private _okMsg = format ["position consistency: %1 sources agree", worldName];
    AEE_LOG_INFO(_okMsg);
};

if (_divergence) then {
    for "_i" from 0 to ((count _verdicts) - 1) do {
        private _verdict = _verdicts select _i;
        if (!(_verdict select 1)) then {
            private _msg = format [
                "position consistency: %1 [%2] %3",
                _verdict select 0, _verdict select 3, _verdict select 2
            ];
            AEE_LOG_WARN(_msg);
        };
    };
};

_divergence
