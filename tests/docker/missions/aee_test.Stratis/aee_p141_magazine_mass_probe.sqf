// PHASE 141: the emitted CfgMagazines mass and its thermal consumer.
//
// tools/validation/gen_engine_overrides.py emits CfgMagazines >> mass from the
// loaded-mass projection (data/ballistics/magazine_masses.json) for every bound
// magazine that resolves a held or derived loaded mass. This probe reads the
// merged config on the live server and asserts the real mass for
// 30Rnd_556x45_Stanag, then proves the thermal loadout consumer
// (fnc_calculateUnitLoadoutThermal) now sees a non-zero magazine content mass:
// a unit carrying the magazine yields a non-zero content mass from the same
// CfgMagazines >> mass key the consumer reads, and the consumer runs and
// returns its flux map.
//
// Emits one [P141] PASS/FAIL line.

private _pass = 0;
private _fail = 0;
private _notes = [];

private _mag = "30Rnd_556x45_Stanag";
private _cfg = configFile >> "CfgMagazines" >> _mag;
private _mass = getNumber (_cfg >> "mass");
private _want = 0.5107;

if (abs (_mass - _want) < 0.001) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["mass = %1 (want %2)", _mass, _want];
};

if (_mass > 0) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "mass is not positive";
};

// The consumer's content-mass read: the CfgMagazines mass of each carried
// magazine. A unit carrying the magazine must show a non-zero content mass.
private _grp = createGroup [civilian, true];
private _unit = _grp createUnit ["B_Soldier_F", [4300, 4250, 0], [], 0, "NONE"];
if (isNull _unit) then {
    _fail = _fail + 1;
    _notes pushBack "the test unit was not created";
} else {
    _unit addBackpack "B_AssaultPack_khk";
    _unit addItemToBackpack _mag;
    private _contentMass = 0;
    {
        _contentMass = _contentMass + getNumber (configFile >> "CfgMagazines" >> _x >> "mass");
    } forEach (backpackItems _unit);
    if (_contentMass > 0) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["content mass = %1", _contentMass];
    };

    private _fnConsumer = missionNamespace getVariable ["aee_thermal_fnc_calculateUnitLoadoutThermal", nil];
    if (isNil "_fnConsumer") then {
        _fail = _fail + 1;
        _notes pushBack "aee_thermal_fnc_calculateUnitLoadoutThermal not compiled";
    } else {
        private _map = [_unit] call _fnConsumer;
        if (_map isEqualType createHashMap) then {
            _pass = _pass + 1;
        } else {
            _fail = _fail + 1;
            _notes pushBack format ["consumer returned %1", _map];
        };
    };
    deleteVehicle _unit;
};
if (!isNull _grp) then { deleteGroup _grp; };

diag_log text format ["[P141] magazine mass: %1 = %2 kg (content mass seen by the consumer)",
    _mag, _mass];

if (_fail == 0) then {
    diag_log text format ["[P141] [PASS] magazine mass and thermal consumer: %1 = %2 kg, consumer sees a non-zero content mass (%3 checks)",
        _mag, _mass, _pass];
} else {
    diag_log text format ["[P141] [FAIL] magazine mass and thermal consumer: %1 passed, %2 failed: %3",
        _pass, _fail, str _notes];
};
