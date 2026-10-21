// Headless load gate probe.
//
// Runs on the dedicated server at mission start and prints one machine-read
// line per identity case, so tests/docker/verify_load.py can assert the rung
// that answered. It spawns nothing, applies nothing and writes no config.
//
// The verifier owns the verdict. This file only reports what the matchers
// returned, so a data change never needs an edit here.

if (!isServer) exitWith {};

diag_log text format ["[LOAD-GATE] BOOT isDedicated=%1 hasInterface=%2 version=%3",
    isDedicated, hasInterface, (productVersion select 3)];

private _missing = [];
{
    if (isNil _x) then { _missing pushBack _x; };
} forEach [
    "aee_vehicles_fnc_getVehicleMatch",
    "aee_flight_fnc_getAircraftMatch",
    "aee_blast_fnc_getMunitionMatch",
    "aee_nightvision_fnc_getDeviceMatch",
    "aee_clothing_fnc_getItemMass"
];
if ((count _missing) == 0) then {
    diag_log text "[LOAD-GATE] FUNCS present=5 missing=0";
} else {
    diag_log text format ["[LOAD-GATE] FUNCS present=%1 missing=%2", 5 - (count _missing), str _missing];
};

// ---- vehicle ladder -------------------------------------------------------
// want= names the rung the case is expected to answer at, or stronger.
// above_type asks only that the answer is stronger than the engine kind.
private _vehicle_cases = [
    ["exact_class", "I_MRAP_03_F"],
    ["alias", "B_MRAP_01_F"],
    ["keyword", "B_Truck_01_transport_F"],
    ["closest", "BTR-70"],
    ["inherited", "C_Offroad_01_F"],
    ["family", "Land Rover"],
    ["type", "Vehicle"],
    ["above_type", "Snatch"],
    ["above_type", "Jackal"]
];
{
    _x params ["_want", "_query"];
    private _r = [_query] call aee_vehicles_fnc_getVehicleMatch;
    private _by = "";
    private _id = "";
    if ((_r isEqualType []) && ((count _r) >= 5)) then {
        _by = _r select 4;
        _id = str (_r select 0);
    } else {
        _by = "none";
    };
    diag_log text format ["[LOAD-GATE] RUNG matcher=vehicle want=%1 query=%2 answered=%3 id=%4",
        _want, _query, _by, _id];
} forEach _vehicle_cases;

// ---- aircraft ladder ------------------------------------------------------
// An airframe is resolved by the flight matcher, never the vehicle matcher.
private _aircraft_cases = [
    ["exact_class", "B_Heli_Light_01_F"],
    ["alias", "Hummingbird"],
    ["above_type", "B_Heli_Attack_01_F"]
];
{
    _x params ["_want", "_query"];
    private _r = [_query] call aee_flight_fnc_getAircraftMatch;
    private _by = "";
    private _id = "";
    if ((_r isEqualType []) && ((count _r) >= 5)) then {
        _by = _r select 4;
        _id = str (_r select 0);
    } else {
        _by = "none";
    };
    diag_log text format ["[LOAD-GATE] RUNG matcher=aircraft want=%1 query=%2 answered=%3 id=%4",
        _want, _query, _by, _id];
} forEach _aircraft_cases;

// ---- munition ladder ------------------------------------------------------
private _munition_cases = [
    ["exact_class", "rksla3wpnmk82snakeye"],
    ["alias", "Bo_Mk82"],
    ["keyword", "AGM-114K"],
    ["family", "JDAM"],
    ["type", "Bomb"]
];
{
    _x params ["_want", "_query"];
    private _r = [_query] call aee_blast_fnc_getMunitionMatch;
    private _by = "";
    private _id = "";
    if ((_r isEqualType []) && ((count _r) >= 5)) then {
        _by = _r select 3;
        _id = str (_r select 0);
    } else {
        _by = "none";
    };
    diag_log text format ["[LOAD-GATE] RUNG matcher=munition want=%1 query=%2 answered=%3 id=%4",
        _want, _query, _by, _id];
} forEach _munition_cases;

// ---- device ladder --------------------------------------------------------
private _device_cases = [
    ["exact_class", "NVGoggles"],
    ["alias", "O_NVGoggles_hex_F"],
    ["type", "optic_tws"],
    ["none", "AEE_No_Such_Device_zzz"]
];
{
    _x params ["_want", "_query"];
    private _r = [_query] call aee_nightvision_fnc_getDeviceMatch;
    private _by = "";
    private _id = "";
    if ((_r isEqualType []) && ((count _r) >= 5)) then {
        _by = _r select 3;
        _id = str (_r select 0);
    } else {
        _by = "none";
    };
    diag_log text format ["[LOAD-GATE] RUNG matcher=device want=%1 query=%2 answered=%3 id=%4",
        _want, _query, _by, _id];
} forEach _device_cases;

// ---- item mass ------------------------------------------------------------
// A family item answers with a published figure. An item the research does
// not hold answers 0, never a guessed mass.
{
    diag_log text format ["[LOAD-GATE] MASS item=%1 kg=%2", _x, [_x] call aee_clothing_fnc_getItemMass];
} forEach ["FirstAidKit", "U_B_CombatUniform_mcam", "AEE_Unknown_zzz_item"];

[{diag_log text "[LOAD-GATE] DONE";}, [], 3] call CBA_fnc_waitAndExecute;
