#include "..\script_component.hpp"

/*
Start the wildlife client tick and the gunfire report handler.

Client-only and idempotent: a second call does nothing while the PFH is live.
The manifest is loaded once.  The Fired handler reports one bounded
stimulus through the reusable substrate.

Arguments: none.

Returns:
  Nothing.
*/

if (!hasInterface) exitWith {};
if (!isNil QGVAR(ambientPFH)) exitWith {};

private _interval = missionNamespace getVariable [QGVAR(tickInterval), 1.0];
if !(_interval isEqualType 0) then { _interval = 1.0; };
if (_interval < 0.5) then { _interval = 0.5; };

private _manifest = call (compile preprocessFileLineNumbers QPATHTOF(data\sound_manifest.sqf));
missionNamespace setVariable [QGVAR(manifest), _manifest];

private _speciesTable = call (compile preprocessFileLineNumbers QPATHTOF(data\species_table.sqf));
missionNamespace setVariable [QGVAR(speciesTable), _speciesTable];

// The ecology corpus and the asset map feed the pure species matcher.  They
// are generated from data/wildlife/ by tools/validation/gen_wildlife_ecology.py.
private _ecologyCorpus = call (compile preprocessFileLineNumbers QPATHTOF(data\ecology_corpus.sqf));
missionNamespace setVariable [QGVAR(ecologyCorpus), _ecologyCorpus];

private _assetMap = call (compile preprocessFileLineNumbers QPATHTOF(data\asset_map.sqf));
missionNamespace setVariable [QGVAR(assetMap), _assetMap];

GVAR(ambientPFH) = [FUNC(wildlifeTickPFH), _interval] call CBA_fnc_addPerFrameHandler;

// The gunfire report rides the core player engine handler: a raw BIS "Fired"
// event on the local unit, re-attached across respawn.  The key is the
// caller's own name, so it cannot collide with another addon's Fired handler.
// The shot becomes a sound event with a source level, not a fixed magnitude.
// A suppressed round is quieter through the ammo's own audible-fire factor,
// and an explosive round is an explosion, not a gunshot.  The base levels and
// the audible-fire mapping are UNSOURCED.
["Fired", {
    params ["_unit", "_weapon", "_muzzle", "_mode", "_ammo"];
    if (isNull _unit) exitWith {};

    private _kind = "gunshot";
    private _audible = getNumber (configFile >> "CfgAmmo" >> _ammo >> "audibleFire");
    if (_audible <= 0) then { _audible = 1; };
    if ((getNumber (configFile >> "CfgAmmo" >> _ammo >> "explosive")) > 0) then {
        _kind = "explosion";
        _audible = 1;
    };
    private _sourceDb = ([_kind] call FUNC(acousticSourceDb)) + (20 * (log _audible));

    private _events = missionNamespace getVariable [QGVAR(soundEvents), []];
    if !(_events isEqualType []) then { _events = []; };
    _events = [
        _events, getPosASL _unit, _sourceDb, _kind, CBA_missionTime,
        WILDLIFE_ACOUSTIC_EVENT_CAP, WILDLIFE_ACOUSTIC_EVENT_HORIZON
    ] call FUNC(acousticPublish);
    missionNamespace setVariable [QGVAR(soundEvents), _events];

    // The disturbance field carries the normalised source strength, so the
    // field is a continuous level.  The old fixed magnitude of 1 is removed.
    private _strength = (
        (_sourceDb - WILDLIFE_ACOUSTIC_HEARING_FLOOR_DB)
        / (WILDLIFE_ACOUSTIC_LOUD_DB - WILDLIFE_ACOUSTIC_HEARING_FLOOR_DB)
    ) max 0 min 1;
    [getPos _unit, _strength] call EFUNC(ai,reportStimulus);
}, QGVAR(firedManEH)] call EFUNC(core,installPlayerEngineHandler);

AEE_LOG_INFO("wildlife client tick started")
