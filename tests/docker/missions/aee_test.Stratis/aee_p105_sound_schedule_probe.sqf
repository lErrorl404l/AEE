// PHASE 105: the sound emission schedule.
//
// fnc_getCallPattern turns the hour, the sun elevation, the month, the air
// temperature, the wind and the rain into the probability that a species
// group calls in a one-hour bin.  fnc_soundTick turns that probability and the
// guild rate into the positional one-shots to play, so birds are not constant
// and crickets follow the Dolbear duty cycle.  Both kernels are pure.
//
// This probe drives them with fixtures over a simulated day.  It plays
// nothing.
//
// Emits [P105] PASS/FAIL lines.

missionNamespace setVariable ["aee_wildlife_logDebug", false];
missionNamespace setVariable ["aee_core_logDebug", false];

private _fnPattern = missionNamespace getVariable ["aee_wildlife_fnc_getCallPattern", []];
private _fnTick = missionNamespace getVariable ["aee_wildlife_fnc_soundTick", []];
if ((_fnPattern isEqualType []) || (_fnTick isEqualType [])) exitWith {
    diag_log text "[P105] [FAIL] sound schedule kernels not compiled (pattern/tick)";
};

// A fixture asset map: two confirmed groups, so the probe drives the pure
// kernels without the client-only asset map the runtime publishes.
private _assetMap = [
    ["sound", "songbird", "CONFIRMED", ["a3\sounds_f\ambient\animals\birds1.wss"], [], ""],
    ["sound", "cricket", "CONFIRMED", ["a3\sounds_f\ambient\animals\sarance1.wss"], [], ""]
];

private _pass = 0;
private _fail = 0;
private _notes = [];

// The corpus temporal bins for the two groups the day fixture drives:
// pre_dawn, dawn, morning, midday, afternoon, dusk, night.
private _birdBins = [0.6, 1, 0.5, 0.05, 0.05, 0.4, 0];
private _cricketBins = [0.3, 0, 0, 0, 0, 0.6, 1];

// A simple diurnal sun elevation in degrees.  SQF sin takes degrees, so the
// half-day arc is 15 degrees per hour.
private _sunElev = {
    params ["_h"];
    if ((_h >= 6) && (_h < 18)) then {
        60 * sin (15 * (_h - 6))
    } else {
        -30
    };
};

// ── Dawn peak and mid-day lull ────────────────────────────────────────────

private _birdMix = [["temperate_bird_dawn", "songbird", 1.0, _birdBins]];
private _counts = [];
for "_h" from 0 to 23 do {
    private _emitted = [
        _h, [_h] call _sunElev, 6, 18, 0, 0, 1.0, _birdMix, _assetMap, [], 7
    ] call _fnTick;
    _counts pushBack (count _emitted);
};

private _peakHour = 0;
private _peakCount = -1;
for "_h" from 0 to 23 do {
    if ((_counts select _h) > _peakCount) then {
        _peakCount = _counts select _h;
        _peakHour = _h;
    };
};

// 1. The bird emission count peaks in the pre-dawn or dawn window.
if ((_peakHour >= 5) && {_peakHour <= 8} && {_peakCount > 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["bird peak hour %1 count %2", _peakHour, _peakCount];
};

// 2. The mid-day lull is near silence against the dawn peak.
private _midday = _counts select 13;
if (_midday < (_peakCount / 10)) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["midday %1 vs peak %2", _midday, _peakCount];
};

// ── Cricket Dolbear duty cycle ────────────────────────────────────────────

private _cricketMix = [["temperate_insect_cricket", "cricket", 1.0, _cricketBins]];
private _hot = [23, -30, 6, 10, 0, 0, 1.0, _cricketMix, _assetMap, [], 7] call _fnTick;
private _mild = [23, -30, 6, 6, 0, 0, 1.0, _cricketMix, _assetMap, [], 7] call _fnTick;
private _cold = [23, -30, 6, 2, 0, 0, 1.0, _cricketMix, _assetMap, [], 7] call _fnTick;

// 3. A cricket at 10 C emits, at 2 C is silent, and the Dolbear rate rises
//    with the temperature.
if (((count _hot) > 0) && {(count _cold) == 0} && {(count _hot) > (count _mild)} && {(count _mild) > 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["cricket hot %1 mild %2 cold %3", count _hot, count _mild, count _cold];
};

// 4. The Dolbear guild factor is zero below 5 C and rises inside the band.
private _p2 = ["temperate_insect_cricket", -30, 23, 6, 2, 0, 0, _cricketBins] call _fnPattern;
private _p10 = ["temperate_insect_cricket", -30, 23, 6, 10, 0, 0, _cricketBins] call _fnPattern;
private _p20 = ["temperate_insect_cricket", -30, 23, 6, 20, 0, 0, _cricketBins] call _fnPattern;
if ((_p2 == 0) && {_p10 > 0} && {_p20 > _p10}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["dolbear p2 %1 p10 %2 p20 %3", _p2, _p10, _p20];
};

// ── Rain, wind and guild gates ────────────────────────────────────────────

// 5. Rain suppresses the emissions.
private _dry = [7, 30, 6, 18, 0, 0, 1.0, _birdMix, _assetMap, [], 7] call _fnTick;
private _wet = [7, 30, 6, 18, 0, 1.0, 1.0, _birdMix, _assetMap, [], 7] call _fnTick;
if ((count _dry) > (count _wet)) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["rain dry %1 wet %2", count _dry, count _wet];
};

// 6. The amphibian chorus is rain-gated: a dry hour damps it, a wet hour
//    lifts it.
private _frogBins = [0.4, 0.1, 0, 0, 0, 0.5, 0.9];
private _frogDry = ["temperate_amphibian", -30, 23, 6, 20, 0, 0.1, _frogBins] call _fnPattern;
private _frogWet = ["temperate_amphibian", -30, 23, 6, 20, 0, 0.6, _frogBins] call _fnPattern;
if ((_frogWet > _frogDry) && {_frogDry > 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["amphibian dry %1 wet %2", _frogDry, _frogWet];
};

// 7. The cicada is diurnal: silent below the horizon, calling above it.
private _cicadaBins = [0, 0, 0.5, 1, 1, 0.5, 0];
private _cicadaNight = ["temperate_insect_cicada", -10, 23, 6, 25, 0, 0, _cicadaBins] call _fnPattern;
private _cicadaDay = ["temperate_insect_cicada", 40, 13, 6, 25, 0, 0, _cicadaBins] call _fnPattern;
if ((_cicadaNight == 0) && {_cicadaDay > 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["cicada night %1 day %2", _cicadaNight, _cicadaDay];
};

// 8. A silent listener and a group outside the mix emit nothing.
private _silent = [7, 30, 6, 18, 0, 0, 0.0, _birdMix, _assetMap, [], 7] call _fnTick;
private _zeroWeight = [7, 30, 6, 18, 0, 0, 1.0, [["temperate_bird_dawn", "songbird", 0.0, _birdBins]], _assetMap, [], 7] call _fnTick;
if ((_silent isEqualTo []) && {_zeroWeight isEqualTo []}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["silent %1 zeroWeight %2", _silent, _zeroWeight];
};

// 9. A fixed seed gives the same schedule on two runs.
private _runA = [7, 30, 6, 18, 0, 0, 1.0, _birdMix, _assetMap, [], 42] call _fnTick;
private _runB = [7, 30, 6, 18, 0, 0, 1.0, _birdMix, _assetMap, [], 42] call _fnTick;
if (_runA isEqualTo _runB) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "fixed seed was not deterministic";
};

diag_log text format ["[P105] schedule: bird peak hour %1 (%2), midday %3, cricket 10C %4 2C %5", _peakHour, _peakCount, _midday, count _hot, count _cold];

if (_fail == 0) then {
    diag_log text format ["[P105] [PASS] sound emission schedule (%1 checks)", _pass];
} else {
    diag_log text format ["[P105] [FAIL] sound emission schedule: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
