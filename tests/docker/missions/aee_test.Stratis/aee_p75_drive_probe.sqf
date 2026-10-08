// PHASE 75: the W2 grip force decelerates a moving, crewed vehicle (#133).
//
// WHY THIS EXISTS. P74 asserts the grip force is COMPUTED correctly. That is
// not enough: addForce acts on the engine's simulation, and only a moving
// vehicle shows the force integrated into motion. This probe drives a crewed
// vehicle and asserts the wet/ice force actually removes speed.
//
// DERIVATION. fnc_applyGripLoss applies, every frame,
//     F = d_mu * m * g   opposite the velocity,
// where d_mu = dry_mu - mu_surface and g = 9.80665 m/s2 (ISO 80000-3). On a
// fully wet surface mu_surface <= wet_mu = 0.55 (hydroplaning only lowers it,
// so d_mu >= dry_mu - wet_mu = 0.25). The impulse over an interval dt is at
// least F_min * dt, so the wet vehicle must lose at least
//     dv_min = F_min * dt / m
// more speed than an otherwise identical dry run. The probe measures F_min
// (the smallest force actually applied), m and dt, and computes dv_min from
// them. The dry run is the control for engine and terrain drag: the only
// difference between the runs is the grip force.
//
// The start is found by scanning for paved cells, so the vehicle runs on the
// airfield. Emits: [P75] [PASS] / [P75] [FAIL] lines.
//
// KNOWN FLAKE (recorded 2026-10-08). The assertion below is at the theoretical
// boundary: the grip force F = d_mu * m * g is constant while wet, so the
// measured extra loss is ~equal to dv_min = F_min * dt / m, and engine
// integration jitter over the 1.5 s window can push the measured value a
// fraction below the bound. The probe then reports FAIL on one run and PASS on
// the next for an identical tree. This is a QA noise source, not a physics
// regression: P74 (the force computation) and the mobility unit suite are the
// deterministic gates. A fix needs a live Docker re-run to calibrate a timing
// tolerance on the bound.

private _seed = {
    params ["_wet"];
    missionNamespace setVariable ["aee_core_surfaceWetness", [0, 1] select _wet];
    missionNamespace setVariable ["aee_core_precipitationPhase", ["none", "rain"] select _wet];
    missionNamespace setVariable ["aee_core_avgGroundTemp", [15, 10] select _wet];
    missionNamespace setVariable ["aee_core_groundState", "Normal"];
};

// ── Find the paved runway. Scan a grid, take the farthest paved pair.
private _ils = getArray (configFile >> "CfgWorlds" >> worldName >> "ilsPosition");
private _cells = [];
for "_dx" from -1200 to 1200 step 30 do {
    for "_dy" from -1200 to 1200 step 30 do {
        private _p = [(_ils select 0) + _dx, (_ils select 1) + _dy, 0];
        private _stl = toLower (surfaceType _p);
        if (((_stl find "concrete") > -1) || {(_stl find "asphalt") > -1} || {(_stl find "runway") > -1}) then {
            _cells pushBack [(_p select 0), (_p select 1)];
        };
    };
};
private _a = [0, 0];
private _b = [0, 0];
private _best = -1;
{
    private _pa = _x;
    { if ((_pa vectorDistance _x) > _best) then { _best = _pa vectorDistance _x; _a = _pa; _b = _x; }; } forEach _cells;
} forEach _cells;

private _dirv = [(_b select 0) - (_a select 0), (_b select 1) - (_a select 1)];
private _dir2 = [sin ((_dirv select 0) atan2 (_dirv select 1)), cos ((_dirv select 0) atan2 (_dirv select 1))];
private _startPos = [(_a select 0), (_a select 1), 0];
diag_log text format ["[P75] DIAG runway paved=%1 start=%2 end=%3 len=%4", count _cells, str _a, str _b, round _best];

// ── One per-frame loop applies the grip force, as production does.
missionNamespace setVariable ["aee_p75_veh", objNull];
missionNamespace setVariable ["aee_p75_grip", false];
missionNamespace setVariable ["aee_p75_fmin", 1e9];
missionNamespace setVariable ["aee_p75_fmax", 0];
private _pfh = [{
    if (missionNamespace getVariable ["aee_p75_grip", false]) then {
        private _v = missionNamespace getVariable ["aee_p75_veh", objNull];
        if (!isNull _v && {alive _v}) then {
            if ([_v] call aee_mobility_fnc_applyGripLoss) then {
                private _f = missionNamespace getVariable ["aee_mobility_gripLossForceN", 0];
                if ((_f isEqualType 0) && {_f > 0}) then {
                    if (_f < (missionNamespace getVariable ["aee_p75_fmin", 1e9])) then {
                        missionNamespace setVariable ["aee_p75_fmin", _f];
                    };
                    if (_f > (missionNamespace getVariable ["aee_p75_fmax", 0])) then {
                        missionNamespace setVariable ["aee_p75_fmax", _f];
                    };
                };
            };
        };
    };
}] call CBA_fnc_addPerFrameHandler;

// ── One run: launch a crewed vehicle, measure the speed loss over dt.
private _measure = {
    params ["_wet", "_launch", "_dur"];
    [_wet] call _seed;
    private _v = createVehicle ["C_Hatchback_01_F", _startPos, [], 0, "NONE"];
    _v setDir ((_dir2 select 0) atan2 (_dir2 select 1));
    _v engineOn true;
    _v disableBrakes true;
    private _grp = createVehicleCrew _v;
    _v setVelocity [(_dir2 select 0) * _launch, (_dir2 select 1) * _launch, 0];
    sleep 0.3;
    private _mass = getMass _v;
    private _s0 = vectorMagnitude velocity _v;
    private _t0 = diag_tickTime;
    missionNamespace setVariable ["aee_p75_veh", _v];
    missionNamespace setVariable ["aee_p75_fmin", 1e9];
    missionNamespace setVariable ["aee_p75_fmax", 0];
    missionNamespace setVariable ["aee_p75_grip", _wet];
    sleep _dur;
    private _dt = diag_tickTime - _t0;
    private _s1 = vectorMagnitude velocity _v;
    private _z1 = (getPosATL _v) select 2;
    missionNamespace setVariable ["aee_p75_grip", false];
    private _fmin = missionNamespace getVariable ["aee_p75_fmin", 0];
    private _fmax = missionNamespace getVariable ["aee_p75_fmax", 0];
    if ((!(_fmin isEqualType 0)) || {_fmin >= 1e9}) then { _fmin = 0; };
    deleteVehicle _v;
    if (!isNull _grp) then { { deleteVehicle _x; } forEach (units _grp); deleteGroup _grp; };
    [_s0, _s1, _dt, _mass, _fmin, _fmax, _z1]
};

private _report = {
    params ["_tag", "_r"];
    _r params ["_s0", "_s1", "_dt", "_mass", "_fmin", "_fmax", "_z1"];
    diag_log text format ["[P75] DIAG %1 speed %2 -> %3 (loss %4) dt=%5 mass=%6 force=%7..%8 z=%9",
        _tag, _s0, _s1, _s0 - _s1, _dt, _mass, _fmin, _fmax, _z1];
};

private _rd = [false, 25, 1.5] call _measure;
["dry", _rd] call _report;
private _rw = [true, 25, 1.5] call _measure;
["wet", _rw] call _report;

[_pfh] call CBA_fnc_removePerFrameHandler;
[false] call _seed;

// ── Assertion. The wet run must lose at least dv_min more than the dry run.
private _dryLoss = (_rd select 0) - (_rd select 1);
private _wetLoss = (_rw select 0) - (_rw select 1);
private _extra = _wetLoss - _dryLoss;
private _mass = _rw select 3;
private _dt = _rw select 2;
private _fmin = _rw select 4;
private _expected = if (_mass > 0) then { (_fmin / _mass) * _dt } else { 0 };
diag_log text format ["[P75] DIAG dry loss=%1 wet loss=%2 extra=%3 fmin=%4 dt=%5 -> dv_min=%6",
    _dryLoss, _wetLoss, _extra, _fmin, _dt, _expected];

if ((_fmin > 0) && {_extra >= _expected}) then {
    diag_log text format ["[P75] [PASS] wet grip decelerates a driven vehicle: extra %1 m/s >= dv_min %2 m/s (F_min %3 N / %4 kg * %5 s)",
        _extra, _expected, _fmin, _mass, _dt];
} else {
    diag_log text format ["[P75] [FAIL] wet grip did not decelerate the vehicle: extra %1 m/s < dv_min %2 m/s (F_min %3 N / %4 kg * %5 s)",
        _extra, _expected, _fmin, _mass, _dt];
};
