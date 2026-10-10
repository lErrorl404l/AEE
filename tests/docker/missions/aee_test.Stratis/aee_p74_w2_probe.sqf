// PHASE 74: the W2 runtime vehicle coupling, asserted.
//
// WHY THIS EXISTS. The maxSpeed and mass overrides are static config. W2 is
// the run-time half: the engine commands setMass and addForce let the
// computed surface physics drive the engine, not only the visuals. A run
// must prove the coupling acts, so this probe applies it and reads it back.
//
// MEASUREMENT. The probe spawns one bound vehicle on the dedicated server.
// It seeds a deterministic snow depth and density, then asserts that
// applyAccretionMass changes getMass by exactly the published layer mass
// (top area * depth * density), and that the mass returns to base when the
// snow is gone. It then asserts the wet/ice grip delta in the traction path
// and that applyGripLoss publishes the sourced Coulomb force
// (d_mu * m * g) and applies nothing on dry ground.
//
// It makes no config change and weakens no existing check.
//
// Emits: [P74] [PASS] / [P74] [FAIL] lines.

private _g = 9.80665;
private _pass = 0;
private _fail = 0;

private _veh = createVehicle ["C_Hatchback_01_F", [4400, 4400, 0], [], 0, "NONE"];

if (isNull _veh) then {
    diag_log text "[P74] [FAIL] bound hatchback did not spawn";
    _fail = _fail + 1;
} else {
    // ── Accretion mass: setMass changes getMass by the layer mass ─────────
    missionNamespace setVariable ["aee_core_snowDepth_m", 0.3];
    missionNamespace setVariable ["aee_persistence_slabDensity", 300];

    private _base = getMass _veh;
    private _box = boundingBoxReal _veh;
    private _min = _box select 0;
    private _max = _box select 1;
    private _area = (abs ((_max select 0) - (_min select 0))) * (abs ((_max select 1) - (_min select 1)));
    private _expected = _area * 0.3 * 300;

    [_veh] call aee_mobility_fnc_applyAccretionMass;
    private _loaded = getMass _veh;
    private _delta = _loaded - _base;

    if ((_expected > 0) && {abs (_delta - _expected) < 0.5}) then {
        diag_log text format ["[P74] [PASS] accretion mass: base=%1 loaded=%2 delta=%3 expected=%4", _base, _loaded, _delta, _expected];
        _pass = _pass + 1;
    } else {
        diag_log text format ["[P74] [FAIL] accretion mass: base=%1 loaded=%2 delta=%3 expected=%4", _base, _loaded, _delta, _expected];
        _fail = _fail + 1;
    };

    // Off the snow the load returns to zero and the mass is restored.
    missionNamespace setVariable ["aee_core_snowDepth_m", 0];
    [_veh] call aee_mobility_fnc_applyAccretionMass;
    private _restored = getMass _veh;

    if (abs (_restored - _base) < 0.5) then {
        diag_log text format ["[P74] [PASS] accretion restore: mass=%1 base=%2", _restored, _base];
        _pass = _pass + 1;
    } else {
        diag_log text format ["[P74] [FAIL] accretion restore: mass=%1 base=%2", _restored, _base];
        _fail = _fail + 1;
    };

    // ── Wet/ice grip delta in the traction path ───────────────────────────
    missionNamespace setVariable ["aee_core_surfaceWetness", 0];
    missionNamespace setVariable ["aee_core_precipitationPhase", "none"];
    missionNamespace setVariable ["aee_core_avgGroundTemp", 15];
    private _dry = [_veh, getMass _veh, 15, false] call aee_mobility_fnc_calculateWetTraction;

    missionNamespace setVariable ["aee_core_surfaceWetness", 1];
    missionNamespace setVariable ["aee_core_precipitationPhase", "rain"];
    missionNamespace setVariable ["aee_core_avgGroundTemp", 10];
    private _wet = [_veh, getMass _veh, 15, false] call aee_mobility_fnc_calculateWetTraction;

    if (_wet < _dry) then {
        diag_log text format ["[P74] [PASS] grip delta in traction path: dry mu=%1 wet mu=%2", _dry, _wet];
        _pass = _pass + 1;
    } else {
        diag_log text format ["[P74] [FAIL] grip delta: dry mu=%1 wet mu=%2", _dry, _wet];
        _fail = _fail + 1;
    };

    // ── The grip loss drives the engine through addForce ──────────────────
    _veh setVelocity [10, 0, 0];
    private _applied = [_veh] call aee_mobility_fnc_applyGripLoss;
    private _force = missionNamespace getVariable ["aee_mobility_gripLossForceN", -1];
    private _dm = missionNamespace getVariable ["aee_mobility_gripDeltaMu", -1];
    private _expectedForce = (_dry - _wet) * (getMass _veh) * _g;

    if (_applied && {abs (_force - _expectedForce) < 1}) then {
        diag_log text format ["[P74] [PASS] grip loss force: %1 N (deltaMu=%2 expected=%3)", _force, _dm, _expectedForce];
        _pass = _pass + 1;
    } else {
        diag_log text format ["[P74] [FAIL] grip loss force: applied=%1 force=%2 deltaMu=%3 expected=%4", _applied, _force, _dm, _expectedForce];
        _fail = _fail + 1;
    };

    // ── Dry ground applies no grip loss ───────────────────────────────────
    missionNamespace setVariable ["aee_core_surfaceWetness", 0];
    missionNamespace setVariable ["aee_core_avgGroundTemp", 15];
    missionNamespace setVariable ["aee_core_groundState", "Normal"];
    private _appliedDry = [_veh] call aee_mobility_fnc_applyGripLoss;

    if (!_appliedDry) then {
        diag_log text "[P74] [PASS] dry ground: no grip-loss force";
        _pass = _pass + 1;
    } else {
        diag_log text "[P74] [FAIL] dry ground: a grip-loss force was applied";
        _fail = _fail + 1;
    };

    deleteVehicle _veh;
};

if (_fail == 0) then {
    diag_log text format ["[P74] [PASS] runtime vehicle coupling: %1 checks", _pass];
} else {
    diag_log text format ["[P74] [FAIL] runtime vehicle coupling: %1 passed, %2 failed", _pass, _fail];
};
