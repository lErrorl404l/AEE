// PHASE 106: the geo anchor and the mapArea versus latitude/longitude divergence.
//
// Two checks, both against the REAL kernels:
//  (a) the live world anchor.  FUNC(getGeoAnchor) must report the sourceToken
//      the current world's CfgWorlds deserves.  The probe recomputes the
//      expected token from the SAME raw config the reader uses, so the
//      assertion follows the world's data, not a hard-coded name.  Stratis
//      ships no mapArea, so the anchor falls back to the CfgWorlds keys and
//      must report "cfgworlds".
//  (b) the divergence MECHANISM, world-independent.  The shipped Altis mapArea
//      box plus the stale Altis latitude/longitude keys are passed through the
//      REAL pure builder.  A usable box wins, so the token is "mapArea" and
//      the centre is the box centre (39.906515 N, 25.246742 E): the stale keys
//      are NOT used.  That divergence is exactly what the anchor exists to
//      resolve.
//
// The Altis CfgWorlds class is in the base game, so check (b) reads the same
// raw values on any world.  If the class were absent the shipped literals are
// the fixture and the assertion still runs through the real builder.
//
// Emits [P106] PASS/FAIL lines.

private _fnReader = missionNamespace getVariable ["aee_core_fnc_getGeoAnchor", nil];
private _fnBuild = missionNamespace getVariable ["aee_core_fnc_buildGeoAnchor", nil];
if (isNil "_fnReader" || {isNil "_fnBuild"}) exitWith {
    diag_log text "[P106] [FAIL] geo anchor kernels not compiled (getGeoAnchor/buildGeoAnchor)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// ── (a) the live world anchor ---------------------------------------------
private _anchor = call _fnReader;
private _cfg = configFile >> "CfgWorlds" >> worldName;
private _rawBox = getArray (_cfg >> "mapArea");
private _expectedToken = "cfgworlds";
if ((_rawBox isEqualType []) && {(count _rawBox) == 4}) then {
    private _lonW = _rawBox select 0;
    private _latS = _rawBox select 1;
    private _lonE = _rawBox select 2;
    private _latN = _rawBox select 3;
    if (
        (_lonW isEqualType 0) && (_latS isEqualType 0)
        && (_lonE isEqualType 0) && (_latN isEqualType 0)
        && (_lonW < _lonE) && (_latS < _latN)
        && (_lonW >= -180) && (_lonE <= 180)
        && (_latS >= -90) && (_latN <= 90)
    ) then {
        _expectedToken = "mapArea";
    };
};

if ((count _anchor) == 9
    && {(_anchor select 8) == _expectedToken}
    && {(_anchor select 2) == getNumber (_cfg >> "mapZone")}
    && {(_anchor select 3) == getNumber (_cfg >> "mapSize")}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["live anchor %1 wanted token=%2 got=%3", worldName, _expectedToken, str _anchor];
};

// ── (b) the divergence mechanism, world-independent -----------------------
private _altisCfg = configFile >> "CfgWorlds" >> "Altis";
private _box = getArray (_altisCfg >> "mapArea");
if ((count _box) != 4) then {
    _box = [25.011957, 39.718452, 25.481527, 40.094578];
};
private _staleLat = getNumber (_altisCfg >> "latitude");
private _staleLon = getNumber (_altisCfg >> "longitude");
if (_staleLat == 0) then { _staleLat = -35.152; };
if (_staleLon == 0) then { _staleLon = 16.661; };

private _built = [
    getNumber (_altisCfg >> "mapSize"),
    getNumber (_altisCfg >> "mapZone"),
    _box,
    _staleLat,
    _staleLon
] call _fnBuild;

private _builtLat = _built select 0;
private _builtLon = _built select 1;
private _staleCentreLat = -_staleLat;   // the BIS latitude key is inverted

// SQF numbers are 32-bit, so a computed centre and the eight-digit shipped
// literal differ at about 1e-6 degrees.  Compare against the box centre
// computed the same way (exact in float), and against the shipped literal at a
// realistic tolerance; both are far from the stale-key centre (35.152 N).
private _expLat = ((_box select 1) + (_box select 3)) / 2;
private _expLon = ((_box select 0) + (_box select 2)) / 2;
private _boxToken = (_built select 8) == "mapArea";
private _boxCentre = ((abs (_builtLat - _expLat)) <= 0.000001)
    && ((abs (_builtLon - _expLon)) <= 0.000001);
private _boxShipped = ((abs (_builtLat - 39.906515)) <= 0.0001)
    && ((abs (_builtLon - 25.246742)) <= 0.0001);
private _boxStale = (abs (_builtLat - _staleCentreLat)) > 1;

diag_log text format ["[P106] box: centre=%1,%2 exp=%3,%4 shipped=%5 stale=%6 token=%7", str _builtLat, str _builtLon, _expLat, _expLon, _boxShipped, _boxStale, _built select 8];

if (_boxToken && _boxCentre && _boxShipped && _boxStale) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["mapArea box ignored: centre %1,%2 token %3", _builtLat, _builtLon, _built select 8];
};

diag_log text format ["[P106] anchor: world=%1 token=%2 zone=%3; box centre %4,%5 (stale keys %6,%7)", worldName, _anchor select 8, _anchor select 2, _builtLat, _builtLon, _staleCentreLat, _staleLon];

if (_fail == 0) then {
    diag_log text format ["[P106] [PASS] geo anchor source and mapArea divergence (%1 checks)", _pass];
} else {
    diag_log text format ["[P106] [FAIL] geo anchor: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
