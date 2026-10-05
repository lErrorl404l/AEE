// PHASE 81: the wildlife edge behaviour, probed on a headless server.
//
// WHY THIS EXISTS. The ambient bed, the species mix and the single wildlife
// tick decide what a client hears and which animals it sees. The ambient
// runtime that loads the manifest is client-local, but the kernels it calls
// carry no hasInterface gate, so a dedicated server can drive them directly.
// This probe drives the REAL SQF and does not fake a render.
//
// WHAT IS PROVEN HEADLESSLY:
//   (1) inert with no player: a live tick with an empty anchor spawns no
//       animal, starts no sound instance and raises no disturbance field.
//   (2) the water shoreline wins the context.
//   (3) the forest boundary splits a day context from its open ground.
//   (4) every AEE Koppen code maps to a legal context key.
//   (5) a large time skip, day to night ten times, keeps the state valid.
//   (6) the four force hooks are honoured and then cleared.
//   (7) the on-demand monitor returns its composed line.
//   (8) the species mix is deterministic for equal inputs.
//
// Bounded and deterministic: fixed codes, ten date steps, one monitor call and
// two species calls. Emits [P81] PASS and FAIL lines.

private _fnTick = missionNamespace getVariable ["aee_wildlife_fnc_wildlifeTick", nil];
private _fnBed = missionNamespace getVariable ["aee_wildlife_fnc_soundBedForContext", nil];
private _fnSpecies = missionNamespace getVariable ["aee_wildlife_fnc_speciesForBiome", nil];
private _fnMonitor = missionNamespace getVariable ["aee_wildlife_fnc_monitorWildlife", nil];

if (isNil "_fnTick" || {isNil "_fnBed"} || {isNil "_fnSpecies"} || {isNil "_fnMonitor"}) exitWith {
    diag_log text "[P81] [FAIL] wildlife kernel functions not compiled (tick/bed/species/monitor)";
};

private _fail = 0;
private _pass = 0;
private _notes = [];

// The legal context vocabulary of fnc_soundBedForContext.
private _legal = [
    "water", "night",
    "day_tropical", "day_arid", "day_temperate", "day_cold",
    "day_tropical_forest", "day_arid_forest", "day_temperate_forest", "day_cold_forest"
];

// The ambient runtime that loads the manifest is client-local, so a server
// starts without one. Provide the matching day_temperate rows here. A client
// run reuses its published manifest unchanged.
private _manifest = missionNamespace getVariable ["aee_wildlife_manifest", []];
if !(_manifest isEqualType []) then { _manifest = []; };
private _publishedManifest = _manifest;
if (_manifest isEqualTo []) then {
    // Mirrors the real day_temperate rows: the open bed at 0.70 gain and the
    // forest bed at 0.85, the +0.15 wooded premium of the manifest.
    _manifest = [
        ["day_temperate", "a3\sounds_f\ambient\animals\birds1.wss", 120, 0.70],
        ["day_temperate_forest", "a3\sounds_f\ambient\animals\birds2.wss", 120, 0.85]
    ];
    missionNamespace setVariable ["aee_wildlife_manifest", _manifest];
};

// -- (1) inert with no player ----------------------------------------------
// A live tick (not a dry run) with an empty anchor. With no local unit the
// tick computes the state and stops before any spawn, sound or field write.
[[], false] call _fnTick;
private _fauna = missionNamespace getVariable ["aee_wildlife_fauna", []];
if !(_fauna isEqualType []) then { _fauna = []; };
private _sounds = missionNamespace getVariable ["aee_wildlife_soundInstances", []];
if !(_sounds isEqualType []) then { _sounds = []; };
private _field = missionNamespace getVariable ["aee_ai_disturbance", []];
if !(_field isEqualType []) then { _field = []; };
if ((_fauna isEqualTo []) && (_sounds isEqualTo []) && (_field isEqualTo [])) then {
    _pass = _pass + 1;
    diag_log text format ["[P81] [PASS] (1) no player inert: fauna %1, sound %2, field %3", count _fauna, count _sounds, count _field];
} else {
    _fail = _fail + 1;
    _notes pushBack format ["(1) no player inert: fauna %1 sound %2 field %3", count _fauna, count _sounds, count _field];
    diag_log text format ["[P81] [FAIL] (1) no player inert: fauna %1 sound %2 field %3", count _fauna, count _sounds, count _field];
};

// -- (2) the water shoreline wins ------------------------------------------
private _waterBed = ["Cfb", false, 1, 0, 0, _manifest, 0, 0] call _fnBed;
if ((_waterBed select 0) == "water") then {
    _pass = _pass + 1;
    diag_log text format ["[P81] [PASS] (2) water shoreline: key %1", _waterBed select 0];
} else {
    _fail = _fail + 1;
    _notes pushBack format ["(2) water shoreline: key %1, want water", _waterBed select 0];
    diag_log text format ["[P81] [FAIL] (2) water shoreline: key %1, want water", _waterBed select 0];
};

// -- (3) the forest boundary -----------------------------------------------
// Same biome, night, water, wind and rain. Only the vegetation score moves.
private _openBed = ["Cfb", false, 0, 0, 0, _manifest, 0, 0.0] call _fnBed;
private _forestBed = ["Cfb", false, 0, 0, 0, _manifest, 0, 1.0] call _fnBed;
private _openKey = _openBed select 0;
private _forestKey = _forestBed select 0;
private _openGain = _openBed select 1;
private _forestGain = _forestBed select 1;
if ((_openKey != _forestKey) && (_forestGain > _openGain)) then {
    _pass = _pass + 1;
    diag_log text format ["[P81] [PASS] (3) forest boundary: %1 gain %2 vs %3 gain %4", _openKey, _openGain, _forestKey, _forestGain];
} else {
    _fail = _fail + 1;
    _notes pushBack format ["(3) forest boundary: %1 gain %2 vs %3 gain %4", _openKey, _openGain, _forestKey, _forestGain];
    diag_log text format ["[P81] [FAIL] (3) forest boundary: %1 gain %2 vs %3 gain %4", _openKey, _openGain, _forestKey, _forestGain];
};

// -- (4) the biome extremes ------------------------------------------------
// The 17 AEE Koppen codes. Each must select a legal context key.
private _codes = [
    "Af", "Am", "Aw", "BWh", "BWk", "BSh", "BSk", "Csa", "Csb",
    "Cfa", "Cfb", "Cwa", "Dfa", "Dfb", "Dfc", "ET", "EF"
];
private _badCode = "";
{
    private _key = ([_x, false, 0, 0, 0, _manifest, 0, 0] call _fnBed) select 0;
    if !(_key in _legal) then { _badCode = _x; };
} forEach _codes;
if ((count _codes == 17) && (_badCode == "")) then {
    _pass = _pass + 1;
    diag_log text format ["[P81] [PASS] (4) biome extremes: %1 Koppen codes, all legal", count _codes];
} else {
    _fail = _fail + 1;
    _notes pushBack format ["(4) biome extremes: %1 codes, first illegal %2", count _codes, _badCode];
    diag_log text format ["[P81] [FAIL] (4) biome extremes: %1 codes, first illegal %2", count _codes, _badCode];
};

// -- (5) the large time skip -----------------------------------------------
// Ten day and night steps. Every tick must return the five-element state with
// a legal bed key, and no step may throw.
private _savedDate = date;
private _stateOk = true;
private _badStep = -1;
for "_i" from 0 to 9 do {
    private _hour = if ((_i mod 2) == 0) then { 12 } else { 0 };
    setDate [2035, 1, 1 + _i, _hour, 0];
    private _state = [[], true] call _fnTick;
    if (_state isEqualType []) then {
        if (((count _state) != 5) || !((_state select 0) in _legal)) then {
            _stateOk = false;
            _badStep = _i;
        };
    } else {
        _stateOk = false;
        _badStep = _i;
    };
};
setDate _savedDate;
if (_stateOk) then {
    _pass = _pass + 1;
    diag_log text "[P81] [PASS] (5) large time skip: 10 day and night steps, every state valid";
} else {
    _fail = _fail + 1;
    _notes pushBack format ["(5) large time skip: invalid state at step %1", _badStep];
    diag_log text format ["[P81] [FAIL] (5) large time skip: invalid state at step %1", _badStep];
};

// -- (6) the force hooks ---------------------------------------------------
// Each hook is set, the tick is called and the hook must be honoured. Every
// hook is cleared afterwards.
missionNamespace setVariable ["aee_wildlife_forceBiome", "Aw"];
missionNamespace setVariable ["aee_wildlife_forceNight", false];
missionNamespace setVariable ["aee_wildlife_forceSilence", -1];
missionNamespace setVariable ["aee_wildlife_forceSpook", []];

private _forced = [[], true] call _fnTick;
private _forcedKey = _forced select 0;
private _biomeOk = ((_forcedKey find "day_tropical") == 0);

missionNamespace setVariable ["aee_wildlife_forceNight", true];
private _nightState = [[], true] call _fnTick;
private _nightOk = ((_nightState select 0) == "night");

// A forced silence of 1 keeps the bed and a forced silence of 0 mutes it, so
// the forced value, not the default, decides the gain.
missionNamespace setVariable ["aee_wildlife_forceBiome", "Cfb"];
missionNamespace setVariable ["aee_wildlife_forceNight", false];
missionNamespace setVariable ["aee_wildlife_forceSilence", 1];
private _loud = [[], true] call _fnTick;
missionNamespace setVariable ["aee_wildlife_forceSilence", 0];
private _quiet = [[], true] call _fnTick;
private _silenceOk = (((_loud select 1) > 0) && ((_quiet select 1) == 0));

missionNamespace setVariable ["aee_wildlife_forceSilence", -1];
missionNamespace setVariable ["aee_wildlife_forceSpook", [100, 100, 0]];
private _spooked = [[], true] call _fnTick;
private _spookOk = ((_spooked select 3) == true);

if (_biomeOk && _nightOk && _silenceOk && _spookOk) then {
    _pass = _pass + 1;
    diag_log text format ["[P81] [PASS] (6) force hooks: biome %1, night %2, silence %3, spook %4", _forcedKey, _nightState select 0, _quiet select 1, _spookOk];
} else {
    _fail = _fail + 1;
    _notes pushBack format ["(6) force hooks: biome %1 night %2 silence %3 spook %4", _forcedKey, _nightState select 0, _quiet select 1, _spookOk];
    diag_log text format ["[P81] [FAIL] (6) force hooks: biome %1 night %2 silence %3 spook %4", _forcedKey, _nightState select 0, _quiet select 1, _spookOk];
};

missionNamespace setVariable ["aee_wildlife_forceBiome", ""];
missionNamespace setVariable ["aee_wildlife_forceNight", 0];
missionNamespace setVariable ["aee_wildlife_forceSilence", -1];
missionNamespace setVariable ["aee_wildlife_forceSpook", []];

// -- (7) the monitor smoke -------------------------------------------------
private _line = [] call _fnMonitor;
if (_line isEqualType "" && {(_line find "wildlife monitor |") >= 0}) then {
    _pass = _pass + 1;
    diag_log text "[P81] [PASS] (7) monitor smoke: the composed monitor line returned";
} else {
    _fail = _fail + 1;
    _notes pushBack format ["(7) monitor smoke: line %1", _line];
    diag_log text format ["[P81] [FAIL] (7) monitor smoke: line %1", _line];
};

// -- (8) the species determinism -------------------------------------------
// Equal inputs must give the equal mix, and the mix must not be empty or the
// equality would be vacuous.
private _table = [
    ["temperate", ["Sheep_random_F", "Hen_random_F", "Rabbit_F"]]
];
private _mixA = ["Cfb", false, 0, 1.0, 42, _table] call _fnSpecies;
private _mixB = ["Cfb", false, 0, 1.0, 42, _table] call _fnSpecies;
if ((_mixA isEqualType []) && ((count _mixA) > 0) && (_mixA isEqualTo _mixB)) then {
    _pass = _pass + 1;
    diag_log text format ["[P81] [PASS] (8) determinism: %1 species rows equal across two calls", count _mixA];
} else {
    _fail = _fail + 1;
    _notes pushBack format ["(8) determinism: A %1 B %2", str _mixA, str _mixB];
    diag_log text format ["[P81] [FAIL] (8) determinism: A %1 B %2", str _mixA, str _mixB];
};

// Restore the server manifest state when this probe supplied the rows.
if (_publishedManifest isEqualTo []) then {
    missionNamespace setVariable ["aee_wildlife_manifest", []];
};

if (_fail == 0) then {
    diag_log text format ["[P81] [PASS] wildlife edge: %1 checks passed", _pass];
} else {
    diag_log text format ["[P81] [FAIL] wildlife edge: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
