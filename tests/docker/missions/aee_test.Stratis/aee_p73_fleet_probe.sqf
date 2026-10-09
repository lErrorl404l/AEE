// PHASE 73: the whole ground fleet, identified.
//
// WHY THIS EXISTS. The maxSpeed config override is a projection of the class
// bindings in data/vehicle/class_bindings.json, and the runtime matcher
// aee_vehicles_fnc_getVehicleMatch resolves a game class to a catalogue entry
// on its own. Neither was exercised across the fleet: the mass census spawns
// the bound classes only, so the coverage of every other ground vehicle was
// never measured.
//
// This probe enumerates every public ground vehicle class in the engine
// config, spawns one instance, reads the engine's own values and asks the
// matcher and the data lookup to resolve the class. It reports the empirical
// match, so the gap between the held bindings and the whole fleet is visible.
//
// MEASUREMENT ONLY. It applies nothing, writes no config, changes no vehicle.
// Each class is spawned once, read once and deleted before the next spawns, so
// no two bodies share a position at one time.
//
// It emits ONE line per class, in this exact form:
//   [P73] FLEET <class> type=<wheeled|tracked> match=<catalogue_id|-> conf=<n>
//         by=<layer> mass=<n> len=<n> wid=<n> turret=<0|1> data=<0|1>
// The tool tools/validation/check_fleet_coverage.py parses those lines and
// reports the matched and unmatched counts and which unmatched classes the
// override still reaches.
//
// A class with no model of its own or inherited cannot spawn, so it is
// abstract: it is skipped, not failed. The engine places a public class, which
// holds scope 2; a class with a lower scope is skipped for the same reason.

private _cfg = configFile >> "CfgVehicles";

private _classes = [];
{
    private _name = configName _x;
    if (_name == "") then { continue; };
    if (!(_name isKindOf "LandVehicle")) then { continue; };
    // A static weapon is not a vehicle. The base game declares class
    // StaticWeapon: LandVehicle, so exclude the HMG, mortar, SAM and radar
    // emplacements: this sweep is the ground vehicle fleet only.
    if (_name isKindOf "StaticWeapon") then { continue; };
    if ((getText (_cfg >> _name >> "model")) == "") then { continue; };
    if ((getNumber (_cfg >> _name >> "scope")) != 2) then { continue; };
    _classes pushBack _name;
} forEach ("true" configClasses _cfg);

_classes sort true;

private _spawned = 0;
private _matched = 0;
private _unmatched = 0;
private _skippedSpawn = 0;
private _fail = 0;
private _notes = [];

{
    private _name = _x;
    // A small grid keeps every spawn on the same clear patch. Each body is
    // deleted before the next spawns.
    private _pos = [2000 + ((_forEachIndex % 10) * 25), 2000 + ((floor (_forEachIndex / 10)) % 10) * 25, 0];
    private _veh = _name createVehicle _pos;
    if (isNull _veh) then {
        _skippedSpawn = _skippedSpawn + 1;
        _notes pushBack format ["%1 did not spawn", _name];
    } else {
        private _mass = getMass _veh;
        private _bb = boundingBoxReal _veh;
        private _len = abs (((_bb select 0) select 0) - ((_bb select 1) select 0));
        private _wid = abs (((_bb select 0) select 1) - ((_bb select 1) select 1));
        private _turret = if ((count (allTurrets _veh)) > 0) then { 1 } else { 0 };
        private _tracked = (_name isKindOf "Tank") || {_name isKindOf "Tracked_APC"};
        private _type = ["wheeled", "tracked"] select _tracked;

        // The classifier reads the live object, so it runs before the delete.
        // Its class token is the catalogue id for the corpus and band routes
        // and the engine ground token for the coarse token route.
        private _cls = "-";
        private _cby = "-";
        if (!isNil "aee_vehicles_fnc_classifyVehicle") then {
            private _classified = [_veh] call aee_vehicles_fnc_classifyVehicle;
            if ((_classified isEqualType []) && {count _classified == 9}) then {
                _cby = _classified select 8;
                if (_cby != "none") then { _cls = _classified select 0; };
            };
        };
        deleteVehicle _veh;

        private _cat = "-";
        private _conf = "-";
        private _by = "-";
        if (!isNil "aee_vehicles_fnc_getVehicleMatch") then {
            private _match = [_name] call aee_vehicles_fnc_getVehicleMatch;
            if ((_match isEqualType []) && {count _match == 7}) then {
                _cat = _match select 0;
                _conf = str (_match select 3);
                _by = _match select 4;
            };
        };
        // The value row is the matcher's second product. A resolved class
        // returns its seven-field row; an unresolved class returns nothing.
        private _dataOk = 0;
        if (!isNil "aee_vehicles_fnc_getVehicleData") then {
            private _data = [_name] call aee_vehicles_fnc_getVehicleData;
            if ((_data isEqualType []) && {count _data == 7}) then { _dataOk = 1; };
        };

        if (_cat == "-") then { _unmatched = _unmatched + 1; } else { _matched = _matched + 1; };
        _spawned = _spawned + 1;
        diag_log text format [
            "[P73] FLEET %1 type=%2 match=%3 conf=%4 by=%5 mass=%6 len=%7 wid=%8 turret=%9 data=%10 cls=%11 cby=%12",
            _name, _type, _cat, _conf, _by, _mass,
            (round (_len * 100) / 100), (round (_wid * 100) / 100), _turret, _dataOk,
            _cls, _cby
        ];
    };
} forEach _classes;

if (isNil "aee_vehicles_fnc_getVehicleMatch") then {
    _fail = _fail + 1;
    _notes pushBack "aee_vehicles_fnc_getVehicleMatch is not compiled";
};
if ((count _classes) == 0) then {
    _fail = _fail + 1;
    _notes pushBack "the engine config holds no public ground vehicle class";
};

if (_fail == 0) then {
    diag_log text format [
        "[P73] [PASS] fleet identification: %1 spawned (%2 matched, %3 unmatched), %4 public ground classes, %5 spawn-skipped",
        _spawned, _matched, _unmatched, count _classes, _skippedSpawn
    ];
} else {
    diag_log text format [
        "[P73] [FAIL] fleet identification: %1 spawned, %2 matched, %3 unmatched: %4",
        _spawned, _matched, _unmatched, str _notes
    ];
};
