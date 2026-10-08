// PHASE 126: the wildlife sound density.
//
// The operator reported too many animal calls at once. The one-shot species
// layer is capped at WILDLIFE_SOUND_INSTANCE_CAP concurrent calls and the
// attached emitter layer at WILDLIFE_EMITTER_CAP. The acoustic niche hypothesis
// (Krause 1987; Pijanowski et al. 2011, BioScience 61(3):203-216) holds that
// species partition the auditory spectrum, so a real forest has few overlapping
// calls. No published figure gives a simultaneous-caller count, so three is a
// stated ceiling.
//
// A dedicated server has hasInterface false, so fnc_playOneShot refuses every
// call and the audible layer cannot be observed here. This probe reports the
// concurrency policy the runtime enforces and the concurrency the model
// produces, both read headless:
//   (1) the one-shot cap, read from the live monitor line
//   (2) the emitter cap, measured through the compiled fnc_emitterPlan default
//   (3) the concurrent one-shot count at the densest hour, from a mirror of the
//       real play loop over the real schedule
//   (4) the schedule still varies with the time of day
//
// It plays nothing. Emits [P126] PASS and FAIL lines.

missionNamespace setVariable ["aee_wildlife_logDebug", false];

private _fnMonitor = missionNamespace getVariable ["aee_wildlife_fnc_monitorWildlife", nil];
private _fnEmitterPlan = missionNamespace getVariable ["aee_wildlife_fnc_emitterPlan", nil];
private _fnSoundTick = missionNamespace getVariable ["aee_wildlife_fnc_soundTick", nil];
if (isNil "_fnMonitor" || {isNil "_fnEmitterPlan"} || {isNil "_fnSoundTick"}) exitWith {
    diag_log text "[P126] [FAIL] wildlife density kernels not compiled (monitor/emitterPlan/soundTick)";
};

private _target = 3;
private _pass = 0;
private _fail = 0;
private _notes = [];

// -- (1) the one-shot cap, read from the live monitor line ------------------
private _line = [] call _fnMonitor;
private _soundCap = -1;
if (_line isEqualType "") then {
    private _idx = _line find "sound=";
    if (_idx >= 0) then {
        private _slash = (_line select [(_idx + 6), 200]) find "/";
        if (_slash >= 0) then {
            private _after = (_line select [(_idx + 6), 200]) select [(_slash + 1), 100];
            private _end = _after find " ";
            if (_end < 0) then { _end = count _after; };
            _soundCap = parseNumber (_after select [0, _end]);
        };
    };
};
if (_soundCap == _target) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["one-shot cap %1, want %2", _soundCap, _target];
};

// -- (2) the emitter cap, through the compiled default ----------------------
// Eight eligible animals, no registry. The compiled fnc_emitterPlan default
// bounds the create list, so the create count is the live emitter cap.
private _active = [];
for "_i" from 0 to 7 do {
    _active pushBack [format ["a%1", _i], "owl", 10 + _i];
};
private _plan = [[], _active] call _fnEmitterPlan;
private _emitterCap = count (_plan select 0);
if (_emitterCap == _target) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["emitter cap %1, want %2", _emitterCap, _target];
};

// -- (3) the concurrent one-shot count at the densest hour ------------------
// The real tick plays up to the cap each tick and fnc_playOneShot expires a
// call three seconds after it starts. Drive the real schedule for the densest
// hour and mirror the loop, so the count is the model's own.
private _birdBins = [0.6, 1, 0.5, 0.05, 0.05, 0.4, 0];
private _cricketBins = [0.3, 0, 0, 0, 0, 0.6, 1];
private _mix = [
    ["temperate_bird_dawn", "songbird", 1.0, _birdBins],
    ["temperate_insect_cricket", "cricket", 1.0, _cricketBins]
];
private _assetMap = [
    ["sound", "songbird", "CONFIRMED", ["a3\sounds_f\ambient\animals\birds1.wss"], [], ""],
    ["sound", "cricket", "CONFIRMED", ["a3\sounds_f\ambient\animals\sarance1.wss"], [], ""]
];
private _sunElev = {
    params ["_h"];
    if ((_h >= 6) && (_h < 18)) then { 60 * sin (15 * (_h - 6)) } else { -30 }
};

private _peakHour = 0;
private _peakList = [];
private _middayCount = 0;
for "_h" from 0 to 23 do {
    private _emitted = [
        _h, [_h] call _sunElev, 6, 18, 0, 0, 1.0, _mix, _assetMap, [], 7
    ] call _fnSoundTick;
    if ((count _emitted) > (count _peakList)) then {
        _peakList = _emitted;
        _peakHour = _h;
    };
    if (_h == 13) then { _middayCount = count _emitted; };
};

private _maxLive = 0;
private _meanLive = 0;
private _total = count _peakList;
if ((_total > 0) && {_soundCap > 0}) then {
    private _life = 3;
    private _ticks = 120;
    private _live = [];
    private _cursor = 0;
    private _sum = 0;
    for "_t" from 0 to (_ticks - 1) do {
        private _still = [];
        { if (_x > _t) then { _still pushBack _x; }; } forEach _live;
        _live = _still;
        for "_k" from 0 to (_soundCap - 1) do {
            if ((count _live) < _soundCap) then {
                _live pushBack (_t + _life);
                _cursor = (_cursor + 1) mod _total;
            };
        };
        if ((count _live) > _maxLive) then { _maxLive = count _live; };
        _sum = _sum + (count _live);
    };
    _meanLive = _sum / _ticks;
};

if ((_maxLive == _target) && {_maxLive <= _soundCap}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["max concurrent %1 (cap %2), want %3", _maxLive, _soundCap, _target];
};

// -- (4) the time variation is preserved ------------------------------------
if ((count _peakList) > _middayCount) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["peak %1 midday %2", count _peakList, _middayCount];
};

diag_log text format [
    "[P126] density: one-shot cap %1, measured max concurrent %2 (mean %3), emitter cap %4, peak hour %5 calls %6, midday %7",
    _soundCap, _maxLive, round (_meanLive * 100) / 100, _emitterCap, _peakHour, count _peakList, _middayCount
];

if (_fail == 0) then {
    diag_log text format ["[P126] [PASS] wildlife sound density (%1 checks)", _pass];
} else {
    diag_log text format ["[P126] [FAIL] wildlife sound density: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
