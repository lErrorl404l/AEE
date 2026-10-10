// PHASE 88: the weather particle alpha and the heat haze, headless
// (aee-workshop-copy item 7, part 2).
//
// The kernels are pure, so a dedicated server drives them with fixed
// overcast and humidity and asserts the wired values.  The registered
// settings and their defaults are asserted too.  It renders nothing and it
// writes no engine weather.

private _pass = 0;
private _fail = 0;
private _notes = [];

private _alphaFn = missionNamespace getVariable ["aee_particles_fnc_weatherParticleAlpha", nil];
private _hazeAlphaFn = missionNamespace getVariable ["aee_particles_fnc_heatHazeAlpha", nil];
private _hazeSizeFn = missionNamespace getVariable ["aee_particles_fnc_heatHazeSize", nil];

if (isNil "_alphaFn" || {isNil "_hazeAlphaFn"} || {isNil "_hazeSizeFn"}) then {
    diag_log text "[P88] [FAIL] weather particle kernels not compiled";
} else {
    // Fixed overcast 0.5 and humidity 50: 1 * (0.5 + 0.5) * 1 = 1.0
    private _v = [1, 0.5, 50, 1] call _alphaFn;
    if (abs (_v - 1.0) < 1e-6) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["alpha(1,0.5,50)=%1", _v]; };

    // Fixed overcast 0 and humidity 100: 1 * (0 + 1) * 1 = 1.0
    _v = [1, 0, 100, 1] call _alphaFn;
    if (abs (_v - 1.0) < 1e-6) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["alpha(1,0,100)=%1", _v]; };

    // The upper clamp holds above 2.
    _v = [1, 1, 100, 8] call _alphaFn;
    if (abs (_v - 2.0) < 1e-6) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["alpha clamp=%1", _v]; };

    // Heat haze at 20 C is 0.20, at 0 C the floor 0.15, at 100 C the cap 0.45.
    _v = [20, 0.15, 0.45] call _hazeAlphaFn;
    if (abs (_v - 0.20) < 1e-6) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["haze(20)=%1", _v]; };
    _v = [0, 0.15, 0.45] call _hazeAlphaFn;
    if (abs (_v - 0.15) < 1e-6) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["haze(0)=%1", _v]; };
    _v = [100, 0.15, 0.45] call _hazeAlphaFn;
    if (abs (_v - 0.45) < 1e-6) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["haze(100)=%1", _v]; };

    // The heat-haze size is 0.5 + draw, so a 0.5 draw yields 1.0.
    _v = [0.5] call _hazeSizeFn;
    if (abs (_v - 1.0) < 1e-6) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["hazeSize(0.5)=%1", _v]; };

    // The registered settings and their defaults.
    private _enabled = missionNamespace getVariable ["aee_particles_weatherAlphaEnabled", false];
    private _hazeEnabled = missionNamespace getVariable ["aee_weatherfx_heatHazeEnabled", false];
    private _hazeMax = missionNamespace getVariable ["aee_weatherfx_heatHazeMaxAlpha", 0];
    if (_enabled && {_hazeEnabled} && {abs (_hazeMax - 0.45) < 1e-6}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["settings enabled=%1 haze=%2 max=%3", _enabled, _hazeEnabled, _hazeMax];
    };
};

if ((_fail == 0) && {_pass >= 8}) then {
    diag_log text format ["[P88] [PASS] weather particles: %1 checks", _pass];
} else {
    diag_log text format ["[P88] [FAIL] weather particles: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
