// PHASE 87: the scene-aware shadow distance, headless (aee-workshop-copy
// item 6).
//
// The pure kernels are driven with a synthetic open sample set and a
// synthetic enclosed set.  The real driver is then called headless and the
// three published state variables are asserted present and bounded, and the
// shadow target is asserted never to exceed the object target.  No real
// player is required.
//
// The clamp is made observable by shrinking the physics target with a heavy
// fog override, so the object target sits below the shadow smoothing step.
// The fog and the shadow minimum are restored afterwards.

private _pass = 0;
private _fail = 0;
private _notes = [];
private _objTarget = 0;

private _classify = missionNamespace getVariable ["aee_vision_fnc_shadowClassifyScene", nil];
private _sampleFn = missionNamespace getVariable ["aee_vision_fnc_shadowSamplePattern", nil];
private _driver = missionNamespace getVariable ["aee_vision_fnc_calculateViewDistance", nil];

if (isNil "_classify" || {isNil "_sampleFn"} || {isNil "_driver"}) then {
    diag_log text "[P87] [FAIL] shadow kernels or driver not compiled";
} else {
    // Synthetic open set: sky samples on the sampled pattern.
    private _pattern = [13, false] call _sampleFn;
    private _openSamples = [];
    {
        _openSamples pushBack [500, _x select 2, _x select 0, _x select 1, 2];
    } forEach _pattern;
    private _open = [_openSamples, 0, [false, 0, 0, 12, 0], 500, 12, 75] call _classify;

    // Synthetic enclosed set: two near objects far apart on screen, with a
    // high interior context and no opening.
    private _enclosedSamples = [
        [30, 1.0, 0.50, 0.50, 0],
        [30, 1.0, 0.10, 0.90, 0]
    ];
    private _enclosed = [_enclosedSamples, 0, [true, 8, 8, 3, 9], 500, 12, 75] call _classify;

    if ((_open select 1) isEqualTo "OPEN") then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["open scene=%1", _open select 1];
    };
    if ((_enclosed select 1) isEqualTo "INTERIOR") then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["enclosed scene=%1", _enclosed select 1];
    };

    // Shrink the physics target with a heavy fog override so the object
    // target is small.  Save and restore both overrides.
    private _fogSaved = missionNamespace getVariable ["aee_core_currentFogDensity", nil];
    private _minSaved = missionNamespace getVariable ["aee_vision_shadowMinDistance", nil];
    missionNamespace setVariable ["aee_core_currentFogDensity", 10];

    // First driver call publishes the terrain target; derive the object
    // target from it.  Then push the shadow minimum above the object target
    // and call again: a present clamp keeps the target at or below it.
    missionNamespace setVariable ["aee_optics_shadowLastUpdate", -1e9];
    [] call _driver;
    private _vd = missionNamespace getVariable ["aee_vision_viewDistanceTarget", nil];
    if (!isNil "_vd") then {
        _objTarget = (_vd * 0.5) min 2000;
    };

    missionNamespace setVariable ["aee_vision_shadowMinDistance", _objTarget + 500];
    missionNamespace setVariable ["aee_optics_shadowLastUpdate", -1e9];
    [] call _driver;

    private _target = missionNamespace getVariable ["aee_vision_shadowTarget", nil];
    private _scene = missionNamespace getVariable ["aee_vision_shadowScene", nil];
    private _coverage = missionNamespace getVariable ["aee_vision_shadowCoverage", nil];

    if (!isNil "_target" && {!isNil "_scene"} && {!isNil "_coverage"}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack "shadow state not published";
    };

    // Bounded.
    private _max = missionNamespace getVariable ["aee_vision_shadowMaxDistance", 500];
    if (!isNil "_target" && {_target >= 0} && {_target <= (_max + 1)}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["target %1 out of [0,%2]", _target, _max];
    };

    // The shadow target never exceeds the object target.
    if (!isNil "_target" && {!isNil "_vd"}) then {
        if (_target <= (_objTarget + 0.5)) then {
            _pass = _pass + 1;
        } else {
            _fail = _fail + 1;
            _notes pushBack format ["target %1 > object %2", _target, _objTarget];
        };
    } else {
        _fail = _fail + 1;
        _notes pushBack "object target not derivable";
    };

    // Restore the overrides.
    if (isNil "_fogSaved") then {
        missionNamespace setVariable ["aee_core_currentFogDensity", nil];
    } else {
        missionNamespace setVariable ["aee_core_currentFogDensity", _fogSaved];
    };
    if (isNil "_minSaved") then {
        missionNamespace setVariable ["aee_vision_shadowMinDistance", 50];
    } else {
        missionNamespace setVariable ["aee_vision_shadowMinDistance", _minSaved];
    };
};

if ((_fail == 0) && {_pass >= 5}) then {
    diag_log text format ["[P87] [PASS] shadow distance: %1 checks (object target %2)", _pass, _objTarget];
} else {
    diag_log text format ["[P87] [FAIL] shadow distance: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
