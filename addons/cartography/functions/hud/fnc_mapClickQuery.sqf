#include "..\..\script_component.hpp"
/*
 * aee_cartography_fnc_mapClickQuery
 *
 * The map click-to-query tool (issue #155 layer 2).  Installs the stackable
 * "MapSingleClick" mission event handler (available since 1.58, and the
 * recommended replacement for the global onMapSingleClick command - command
 * DB), so the tool does not clobber another mod's onMapSingleClick.
 *
 * On a click it reads the AEE state at the clicked position and shows a
 * structured readout in the mod's weather-report style (FUNC(mapStateReadout),
 * the same "=== ... ===" block the actions addon uses).
 *
 * Honest scope: only the values that AEE computes PER POSITION are read at
 * the clicked point (biome, surface material, local wind, terrain height).
 * Every other value the issue names (temperature, WBGT, flood, fire, snow,
 * radio, hypoxia) is a GLOBAL scalar the mod computes at the player position,
 * so the readout labels them "current" and does not pretend they describe the
 * clicked point.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};
if (!isNil QGVAR(mapClickEH)) exitWith {};

GVAR(mapClickEH) = addMissionEventHandler ["MapSingleClick", {
    params ["_units", "_pos", "_alt", "_shift"];
    if !(missionNamespace getVariable [QGVAR(mapOverlayEnabled), false]) exitWith {};
    if !(missionNamespace getVariable [QGVAR(mapClickQuery), true]) exitWith {};

    private _px = _pos select 0;
    private _py = _pos select 1;
    private _gz = getTerrainHeightASL [_px, _py];
    private _asl = [_px, _py, _gz];

    private _rows = [];

    // ── Per-position values: computed AT the clicked point ────────────────
    private _code = [_asl] call EFUNC(weather,getBiomeAtPosition);
    private _name = [_code] call EFUNC(weather,getBiomeName);
    _rows pushBack ["Biome", _code + " (" + _name + ")"];

    private _mat = (surfaceType [_px, _py]) call EFUNC(material,classifyBySurfaceType);
    _rows pushBack ["Surface", _mat];

    _rows pushBack ["Terrain", (str (round _gz)) + " m ASL"];

    private _wind = [_asl, 2] call EFUNC(atmos,getLocalWind);
    private _wspeed = sqrt (((_wind select 0) ^ 2) + ((_wind select 1) ^ 2));
    _rows pushBack ["Local wind", (str (round (_wspeed * 10) / 10)) + " m/s"];

    // ── Current global AEE state: computed at the player position ─────────
    private _t = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
    private _wbgt = missionNamespace getVariable [QEGVAR(core,currentWBGT), 15];
    private _ground = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
    private _snow = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];
    private _flood = missionNamespace getVariable [QEGVAR(core,currentFloodRisk), "None"];
    private _fire = missionNamespace getVariable [QEGVAR(core,currentFireRisk), 0];
    private _light = missionNamespace getVariable [QEGVAR(core,currentLightningRisk), 0];
    private _radio = missionNamespace getVariable [QEGVAR(radio,radioPropagationIndex), 1.0];
    private _hypox = missionNamespace getVariable [QEGVAR(core,currentHypoxiaRisk), 0];

    _rows pushBack ["Air temp (current)", (str (round _t)) + " C"];
    _rows pushBack ["WBGT (current)", (str (round _wbgt)) + " C"];
    _rows pushBack ["Ground (current)", _ground];
    _rows pushBack ["Snow depth (current)", (str (round (_snow * 100) / 100)) + " m"];
    _rows pushBack ["Flood risk (current)", _flood];
    _rows pushBack ["Fire risk (current)", str (round (_fire * 100) / 100)];
    _rows pushBack ["Lightning risk (current)", str (round (_light * 100) / 100)];
    _rows pushBack ["Radio index (current)", str (round (_radio * 100) / 100)];
    _rows pushBack ["Hypoxia risk (current)", str (round (_hypox * 100) / 100)];

    hintSilent (["AEE Map Query", _rows] call FUNC(mapStateReadout));
}];
