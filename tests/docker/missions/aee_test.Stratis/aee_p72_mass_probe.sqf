// PHASE 72: the in-engine mass census, measured.
//
// WHY THIS EXISTS. getMass and the config mass on a vehicle are ENGINE
// tuning values, not real masses. data/vehicle/SCHEMA.md states that an
// engine config value is engine identity and must NEVER be a value source.
// A future CfgVehicles mass override must therefore be a CALIBRATED scale of
// a held real mass, never a copy of an engine number. This probe measures
// the engine's own mass per bound class so that calibration has a basis.
//
// This probe MEASURES ONLY. It applies nothing, it writes no config, and it
// changes no vehicle. Each class is spawned once, read once and deleted.
//
// It emits ONE line per class, in this exact form:
//   [P72] MASS <class> config=<n> live=<n>
// The tool tools/validation/build_mass_calibration.py parses those lines and
// pairs each one with the held real mass in
// data/vehicle/mass_model_calibration.json. The class list below is the 18
// classes in data/vehicle/class_bindings.json; the tool fails closed when a
// class is absent from this log.

private _CLASSES = [
    "C_Hatchback_01_F",
    "C_Hatchback_01_sport_F",
    "B_MRAP_01_F",
    "I_MRAP_03_F",
    "O_MRAP_02_F",
    "B_MBT_01_cannon_F",
    "I_MBT_03_cannon_F",
    "O_MBT_02_cannon_F",
    "B_APC_Tracked_01_rcws_F",
    "I_APC_tracked_03_cannon_F",
    "O_APC_Tracked_02_cannon_F",
    "B_Truck_01_transport_F",
    "I_Truck_02_transport_F",
    "O_Truck_02_transport_F",
    "B_AFV_Wheeled_01_cannon_F",
    "B_APC_Wheeled_01_cannon_F",
    "I_APC_Wheeled_03_cannon_F",
    "O_APC_Wheeled_02_rcws_v2_F"
];

private _ok = 0;
private _fail = 0;
private _notes = [];

{
    private _class = _x;
    private _configMass = getNumber (configFile >> "CfgVehicles" >> _class >> "mass");
    // Spawn clear of every other class. Each vehicle is deleted before the
    // next spawns, so no two bodies share the position at one time.
    private _veh = _class createVehicle [2000 + (_forEachIndex * 40), 2000, 0];
    if (isNull _veh) then {
        _fail = _fail + 1;
        _notes pushBack format ["%1 did not spawn", _class];
        diag_log text format ["[P72] MASS %1 config=%2 live=FAIL", _class, str _configMass];
    } else {
        private _live = getMass _veh;
        deleteVehicle _veh;
        _ok = _ok + 1;
        diag_log text format ["[P72] MASS %1 config=%2 live=%3", _class, str _configMass, str _live];
    };
} forEach _CLASSES;

if (_fail == 0) then {
    diag_log text format ["[P72] [PASS] engine mass census: %1 classes", _ok];
} else {
    diag_log text format ["[P72] [FAIL] engine mass census: %1 measured, %2 failed: %3", _ok, _fail, str _notes];
};
