#include "..\script_component.hpp"

params [["_enabled", true, [true]]];

if (is3DEN) exitWith {};
if (!_enabled) exitWith {
    if (!isNil QGVAR(updatePFH)) then {
        [GVAR(updatePFH)] call CBA_fnc_removePerFrameHandler;
        GVAR(updatePFH) = nil;
    };
};

// Remove existing PFH first
if (!isNil QGVAR(updatePFH)) then {
    [GVAR(updatePFH)] call CBA_fnc_removePerFrameHandler;
};

// Detect base map biome once (first call caches in GVAR(biome))
[] call EFUNC(environmental,getBiome);

// ─── Geolocation sanity check (issue #179) ────────────────────────────────
// One load-time read of the world anchor.  A declared UTM zone whose
// central meridian sits away from the terrain longitude is NORMAL: a map
// is authored in a time zone, and the solar model uses the declared zone
// meridian on purpose (fnc_calculateSolarRadiation).  The condition is
// therefore reported at INFO.  Latitude is still checked against its
// physical range, because that IS a data fault.
// NOTE: BIS latitude is INVERTED (positive = south), so a sign check
// cannot use the zone number alone - only the zone<->longitude band
// cross-check is valid.  The Scottish Highlands bug (latitude = -56.702,
// issue #123) is caught by the range check below.
private _loc = [] call FUNC(getWorldLocation);
private _latSigned = _loc select 0;
private _lon = _loc select 2;
private _zone = _loc select 3;
if (_zone > 0) then {
    private _zoneMeridian = (_zone - 1) * 6 - 177;
    private _lonDiff = abs (_lon - _zoneMeridian);
    if (_lonDiff > 6) then {
        diag_log format [
            "[AEE] INFO: mapZone %1 (meridian %2) sits %3 deg from longitude %4 (CfgWorlds %5); the solar model uses the declared zone meridian",
            _zone, _zoneMeridian, _lonDiff, _lon, worldName
        ];
    };
};
if ((abs _latSigned) > 90) then {
    diag_log format [
        "[AEE] WARNING: latitude %1 out of range for %2 (CfgWorlds)",
        _latSigned, worldName
    ];
};
diag_log format [
    "[AEE] Geolocation: %1 lat=%2 lon=%3 zone=%4",
    worldName, _latSigned, _lon, _zone
];

// Register the local environment PFH.
// Runs on every machine. Core atmospheric state is deterministic (position,
// mission time, engine weather), so all machines agree without publicVariable
// broadcast. Event FX vary cosmetically per machine.
private _interval = GVAR(updateInterval);
GVAR(updatePFH) = [{
    // Resolve position once so temp, pressure, and humidity all use the
    // exact same location — deterministic, communicable between players.
    private _player = call CBA_fnc_currentUnit;
    // CBA_fnc_currentUnit always returns an object: the Zeus remote-control
    // unit, or `player`. On a dedicated server that is objNull, never nil,
    // so the test must be isNull. isNil here was a no-op and the server
    // took getPosASL objNull instead of the intended empty array.
    private _pos = if (!isNil "_player" && {!isNull _player}) then {
        getPosASL _player
    } else {
        []
    };
    [_pos] call FUNC(updateEnvironment);
}, _interval] call CBA_fnc_addPerFrameHandler;

diag_log format ["[AEE] Local environment PFH started. Base biome: %1", GVAR(biomeName)];
