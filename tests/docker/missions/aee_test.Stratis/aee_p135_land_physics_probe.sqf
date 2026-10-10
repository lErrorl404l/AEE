// PHASE 135: the land physics pipeline, asserted on the live merged config.
//
// The land section of tools/validation/gen_physics_config.py emits the
// carx/tankx/shipx surface under the same build-time gate as the aircraft
// keys: a key is emitted only when the class identity grade and the held value
// grade are both documented. PRODUCTION EMITS NO NEW LAND KEY while every land
// class binding is claimed, so this probe proves the GENERATOR PATH with a
// documented FIXTURE, NOT a shipped production key. The fixture addon
// tests/docker/probe_physics declares maxBrakeTorque for the class, generated
// from data/vehicle/fixtures/land_physics_fixture.json by
//   python3 tools/validation/gen_physics_config.py \
//     --land-fixture data/vehicle/fixtures/land_physics_fixture.json \
//     --fixture-out tests/docker/probe_physics/addons/probe_physics/generated/CfgVehicles.hpp
// and loaded after aee_mobility, so the engine merges it into the class.
//
// The probe reads the merged CfgVehicles mass and maxSpeed for
// B_MBT_01_cannon_F and asserts the corpus-derived values, then spawns, drives
// and stops the vehicle and asserts the physics does not fault. It then reads
// the merged new carx key maxBrakeTorque and asserts the documented fixture
// value. It renders nothing.
//
// Emits one [P135] PASS/FAIL line.

private _pass = 0;
private _fail = 0;
private _notes = [];

private _class = "B_MBT_01_cannon_F";
private _cfg = configFile >> "CfgVehicles" >> _class;

// The corpus-derived values. mass is the calibrated scale of the held real
// mass, maxSpeed is the held catalogue max_speed_kmh.
private _wantMass = 62273.044493;
private _wantSpeed = 72;
// The documented fixture value from data/vehicle/fixtures/land_physics_fixture.json.
private _wantBrake = 55000;

{
    _x params ["_key", "_want", "_got"];
    if (abs (_got - _want) < 0.001) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["%1 = %2 (want %3)", _key, _got, _want];
    };
} forEach [
    ["mass", _wantMass, getNumber (_cfg >> "mass")],
    ["maxSpeed", _wantSpeed, getNumber (_cfg >> "maxSpeed")],
    ["maxBrakeTorque", _wantBrake, getNumber (_cfg >> "maxBrakeTorque")]
];

// Spawn, drive and stop. The engine physics must not fault.
private _start = [4600, 4600, 0];
private _veh = createVehicle [_class, _start, [], 0, "NONE"];
_veh engineOn true;
private _grp = createVehicleCrew _veh;
_veh setVelocity [0, 12, 0];
sleep 2;
private _moved = (_start vectorDistance (getPosATL _veh)) > 2;
private _alive = alive _veh;
private _finite = (vectorMagnitude velocity _veh) isEqualType 0;
_veh setVelocity [0, 0, 0];
sleep 0.5;
_veh engineOn false;
deleteVehicle _veh;
if (!isNull _grp) then {
    { deleteVehicle _x; } forEach (units _grp);
    deleteGroup _grp;
};

if (_alive && _moved && _finite) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["drive alive=%1 moved=%2 finite=%3", _alive, _moved, _finite];
};

diag_log text format ["[P135] land physics: mass=%1 maxSpeed=%2 maxBrakeTorque=%3",
    getNumber (_cfg >> "mass"),
    getNumber (_cfg >> "maxSpeed"),
    getNumber (_cfg >> "maxBrakeTorque")
];

if (_fail == 0) then {
    diag_log text format ["[P135] [PASS] land physics pipeline: merged mass, maxSpeed and the fixture carx key match (%1 checks)", _pass];
} else {
    diag_log text format ["[P135] [FAIL] land physics pipeline: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
