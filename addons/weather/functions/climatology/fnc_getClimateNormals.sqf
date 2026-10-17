#include "..\..\script_component.hpp"
/*
Monthly climate normals for the current map, in the shape
  [mslp hPa, -1, tMax[12], tMin[12], RH[12], precip mm[12]]

Resolution order, real data first:
  1. the world's bound reference station (fnc_getStationNormals "": Altis,
     Stratis and Malden -> Lemnos, Tanoa -> Nadi, Livonia -> Suwalki);
  2. the normals fnc_getBiome published for an unbound world (the latitude
     climatology, fnc_getLatitudeClimate);
  3. the type-locality station of the Koppen class (fnc_getStationNormals
     "<code>"), for a module-override map before getBiome has run.
Every station row is projected from data/climate/station_normals.json and
names its primary source.  An unknown class falls back to Cfb (London).

Arguments:
  0: biome (STRING, a Koppen code, default "Cfa")
*/

params [["_biome", "Cfa", [""]]];

private _world = [""] call FUNC(getStationNormals);
if (_world isNotEqualTo []) exitWith { _world };

private _latNormals = missionNamespace getVariable [QGVAR(climateNormals), []];
if (_latNormals isNotEqualTo []) exitWith { _latNormals };

private _station = [_biome] call FUNC(getStationNormals);
if (_station isEqualTo []) then { _station = ["Cfb"] call FUNC(getStationNormals); };
_station
