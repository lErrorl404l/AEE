#include "..\script_component.hpp"
/*
Get the world's full geolocation from CfgWorlds: signed latitude,
latitude magnitude, longitude, and UTM map zone.  This is the single
source of truth for every location-dependent system (issue #179).

The mod once had three separate latitude reads with inconsistent
handling, and no longitude or mapZone read at all (issue #154 pattern
3).  Solar noon pinned to 12:00 game time, the compass fabricated a
longitude from map X, and MGRS could not exist.  This function is the
consolidation: one CfgWorlds read, one [lat, lon, zone] anchor, with
the BIS latitude sign quirk corrected HERE so every consumer sees the
real geographic convention.

Return:
  [latSignedTrue, magnitudeDeg, lonDeg, mapZone]
    - latSignedTrue: TRUE geographic sign - positive NORTH, negative
      south (the standard convention)
    - magnitudeDeg:  abs() of the signed value
    - lonDeg:        as published (positive east)
    - mapZone:       UTM zone number (number, 1..60), 0 if unset

CfgWorlds semantics (BIS config reference):
  - latitude:  "positive is south" - the BIS value is INVERTED from the
    standard convention (Tanoa +17.698 is southern; Stratis -35.097 is
    northern; oski_corran -56.702 is northern).  This function NEGATES
    the raw value so the caller gets positive = north.
  - longitude: "positive is east"  (Stratis: 16.482) - unchanged
  - mapZone:   UTM zone number (Stratis: 35) - unchanged

The magnitude is for consumers that want |lat| (Koppen bands, solar
max elevation); the signed value is for direction-dependent physics
(Coriolis deflection, hemisphere checks) and now carries the TRUE sign.
A missing or zero latitude falls back to 40 N (temperate default),
longitude to 0, and mapZone to 0 - the same fallback the old latitude
reader used.
*/

// The CfgWorlds read is three config lookups, and this function is called
// around thirteen times per environment tick on EVERY machine. The world
// does not change during a mission, so the result is computed once and
// cached. missionNamespace scopes the cache to the mission, so a restart
// re-reads it rather than holding a stale world.
private _cached = missionNamespace getVariable [QGVAR(worldLocation), []];
if (_cached isNotEqualTo []) exitWith { _cached };

private _signed = -getNumber (configFile >> "CfgWorlds" >> worldName >> "latitude");
if !(_signed isEqualType 0) then { _signed = 40; };
if (_signed == 0) then { _signed = 40; };

private _lon = getNumber (configFile >> "CfgWorlds" >> worldName >> "longitude");
if !(_lon isEqualType 0) then { _lon = 0; };

private _zone = getNumber (configFile >> "CfgWorlds" >> worldName >> "mapZone");
if !(_zone isEqualType 0) then { _zone = 0; };

private _result = [_signed, abs _signed, _lon, _zone];
missionNamespace setVariable [QGVAR(worldLocation), _result];

_result
