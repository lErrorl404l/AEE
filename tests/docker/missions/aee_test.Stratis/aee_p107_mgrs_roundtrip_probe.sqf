// PHASE 107: the MGRS round trip on the live world.
//
// A world position maps through worldToMgrs to an MGRS reference and back
// through mgrsToWorld.  MGRS truncates to the square south-west corner, so the
// ten-digit residual is bounded by the square diagonal (sqrt 2 m, about
// 1.415 m); the live no-box world centre sits at 1.42 m, and a box world is
// exact. The zone must survive the round trip and equal the UTM zone of the
// anchor centre longitude, which is the projection's own rule.
//
// NOTE ON mapZone.  The CfgWorlds mapZone key is the world's declared UTM
// zone.  On a world with no mapArea (Stratis) the anchor falls back to the
// stale longitude key (16.482), whose UTM zone is 33 - NOT the declared
// mapZone 35.  The probe therefore asserts the returned zone follows the
// anchor centre, and separately proves the correspondence holds where the
// world's data is authoritative: the Altis mapArea box centre (25.246742 E)
// projects to zone 35, which IS that world's declared mapZone.
//
// Emits [P107] PASS/FAIL lines.

private _fnReader = missionNamespace getVariable ["aee_core_fnc_getGeoAnchor", nil];
private _fnW2M = missionNamespace getVariable ["aee_core_fnc_worldToMgrs", nil];
private _fnM2W = missionNamespace getVariable ["aee_core_fnc_mgrsToWorld", nil];
private _fnParse = missionNamespace getVariable ["aee_core_fnc_parseMgrs", nil];
private _fnBuild = missionNamespace getVariable ["aee_core_fnc_buildGeoAnchor", nil];
if (isNil "_fnReader" || {isNil "_fnW2M"} || {isNil "_fnM2W"} || {isNil "_fnParse"} || {isNil "_fnBuild"}) exitWith {
    diag_log text "[P107] [FAIL] MGRS kernels not compiled (getGeoAnchor/worldToMgrs/mgrsToWorld/parseMgrs/buildGeoAnchor)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

private _anchor = call _fnReader;
private _mapSize = _anchor select 3;
private _pos = [_mapSize / 2, _mapSize / 2, 0];

private _written = [_pos, _anchor, 10] call _fnW2M;
private _mgrs = _written select 0;
private _zone = _written select 5;
private _back = [_mgrs, _anchor] call _fnM2W;

// 1. the round trip stays inside the MGRS square diagonal
private _drift = _pos distance _back;
if (_drift <= 1.5) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["round trip drifted %1 m", _drift];
};

// 2. the zone is the UTM zone of the anchor centre longitude and survives
// the parse
private _centreZone = (floor (((_anchor select 1) + 180) / 6)) + 1;
private _parsed = [_mgrs] call _fnParse;
private _parsedZone = _parsed select 2;
if ((_zone == _centreZone) && {_parsedZone == _zone}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["zone %1 wanted %2 parsed %3", _zone, _centreZone, _parsedZone];
};

// 3. a box world's zone IS its declared mapZone: the projection follows the
// authoritative box, not a stale key.
private _altisCfg = configFile >> "CfgWorlds" >> "Altis";
private _box = getArray (_altisCfg >> "mapArea");
if ((count _box) != 4) then {
    _box = [25.011957, 39.718452, 25.481527, 40.094578];
};
private _boxSize = getNumber (_altisCfg >> "mapSize");
if (_boxSize <= 0) then { _boxSize = 30720; };
private _boxAnchor = [
    _boxSize,
    getNumber (_altisCfg >> "mapZone"),
    _box,
    getNumber (_altisCfg >> "latitude"),
    getNumber (_altisCfg >> "longitude")
] call _fnBuild;
private _boxWritten = [[_boxSize / 2, _boxSize / 2, 0], _boxAnchor, 10] call _fnW2M;
if ((_boxWritten select 5) == (_boxAnchor select 2)) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["box zone %1 wanted mapZone %2", _boxWritten select 5, _boxAnchor select 2];
};

diag_log text format ["[P107] live zone=%1 (mapZone key %2) mgrs=%3 drift=%4 m; box world zone=%5 mapZone=%6", _zone, _anchor select 2, _mgrs, _drift, _boxWritten select 5, _boxAnchor select 2];

if (_fail == 0) then {
    diag_log text format ["[P107] [PASS] MGRS round trip on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P107] [FAIL] MGRS round trip: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
