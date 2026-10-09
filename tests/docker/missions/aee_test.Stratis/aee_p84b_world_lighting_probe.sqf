// PHASE 84B: the run-time world lighting matcher.
//
// The config anchor P84 reads is load-time and world-independent.  The matcher
// derives the run-time profile from latitude, biome, terrain signals and
// engine weather and consults no map name, so it runs on EVERY world the test
// mission loads.  This probe drives the real binder and asserts the resolved
// class, the bounded profile and the published class.  It renders nothing.

private _fn = missionNamespace getVariable ["aee_environmental_fnc_applyWorldLighting", nil];
private _classFn = missionNamespace getVariable ["aee_environmental_fnc_worldLightingClass", nil];
private _pass = 0;
private _fail = 0;
private _notes = [];

private _known = [
    "POLAR", "SUBARCTIC", "MONTANE", "TEMPERATE_COOL", "TEMPERATE",
    "MEDITERRANEAN", "ARID", "TROPICAL", "TROPICAL_HUMID", "MARITIME"
];

if (isNil "_fn" || {isNil "_classFn"}) then {
    _fail = _fail + 1;
    _notes pushBack "matcher binder or class kernel not compiled";
} else {
    private _profile = [] call _fn;
    private _class = missionNamespace getVariable ["aee_environmental_worldLightingClass", ""];

    // 1. The class is one of the known set.
    if (_known find _class >= 0) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["class %1", _class];
    };

    // 2. The profile is four elements, each bounded 0..2.
    private _bounded = false;
    if ((_profile isEqualType []) && {(count _profile) == 4}) then {
        _bounded = true;
        {
            if ((_x < 0) || {_x > 2}) then { _bounded = false; };
        } forEach _profile;
    };
    if (_bounded) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["profile %1", str _profile];
    };

    // 3. The published class equals the class the binder resolved.  Recompute
    //    the class from the same facts the binder reads, through the pure
    //    class kernel, so a drift between the binder and the kernel fails.
    private _loc = [] call aee_lib_fnc_getWorldLocation;
    private _biome = missionNamespace getVariable ["aee_core_biome", "Cfb"];
    private _signals = missionNamespace getVariable ["aee_environmental_terrainSignals", []];
    private _waterFrac = 0;
    private _meanElev = 0;
    if ((_signals isEqualType []) && {(count _signals) > 4}) then {
        _waterFrac = _signals select 3;
        _meanElev = _signals select 4;
    };
    private _first = toUpper (_biome select [0, 1]);
    private _group = 5;
    if (_first == "A") then { _group = 0; };
    if (_first == "B") then { _group = 1; };
    if (_first == "C") then { _group = 2; };
    if (_first == "D") then { _group = 3; };
    if (_first == "E") then { _group = 4; };
    private _dry = 0;
    private _prefix2 = toUpper (_biome select [0, 2]);
    if ((_prefix2 == "CS") || {_prefix2 == "BW"} || {_prefix2 == "BS"}) then { _dry = 1; };
    private _expected = [(_loc select 0), _group, _waterFrac, _meanElev, _dry] call _classFn;
    if (_class == _expected) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["published %1 expected %2", _class, _expected];
    };

    if (_fail == 0) then {
        diag_log text format ["[P84B] [PASS] world lighting %1 %2", _class, str _profile];
    } else {
        diag_log text format ["[P84B] [FAIL] world lighting: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
    };
};
