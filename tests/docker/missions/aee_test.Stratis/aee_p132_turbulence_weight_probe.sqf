// PHASE 132: the turbulence gust response is aerodynamic and mass-aware.
//
// WHY THIS EXISTS.  The operator reported the wind blew the light Littlebird
// around like a heavy airframe.  The old gust force was gust * rho * mass /
// 100, so the acceleration it realised was F / mass = gust * rho / 100, the
// SAME for a 782 kg AH-9 Pawnee and a 22 tonne Chinook: the model was
// mass-blind.  The simple-model path was worse, a raw velocity delta with no
// mass at all.
//
// THE MODEL.  The gust is a relative wind.  Its force is aerodynamic drag,
// the dynamic pressure times the airframe's effective drag area:
//   F = 0.5 rho v^2 (Cd S)
// rho is the local density, v the gust speed and Cd S the drag area.  The
// drag area comes from the aircraft corpus record (data/aircraft/SCHEMA.md
// section 5): drag_area_m2 for a fixed-wing (Cd S) or rotor_disc_area_m2 for
// a rotary-wing (the disc).  The force carries no mass, so the acceleration
// F / mass falls with the mass.
//
// THIS PROBE reads the operator's airframe record from the corpus, checks the
// drag area the corpus holds, and proves the force is mass-free while the
// acceleration is mass-aware against a heavy airframe.  It renders nothing.
//
// Emits: [P132] [PASS] / [P132] [FAIL] lines.

private _pass = 0;
private _fail = 0;
private _notes = [];

private _check = {
    params ["_ok", "_label"];
    if (_ok) then { _pass = _pass + 1; } else {
        _fail = _fail + 1;
        _notes pushBack _label;
    };
};

private _gust = 5.0;    // a moderate gust, m/s
private _rho = 1.225;   // ISA sea-level density, kg/m^3

// The operator's airframe from the run: B_Heli_Light_01_armed_F, the AH-9
// Pawnee (the Littlebird airframe he named).  Its corpus record is md530f.
private _lightClass = "B_Heli_Light_01_armed_F";
private _lightRow = [_lightClass] call aee_mobility_fnc_getAircraftData;
private _lightMass = if ((count _lightRow) > 0) then { _lightRow select 0 } else { 0 };
private _lightArea = [_lightRow] call aee_mobility_fnc_resolveTurbulenceArea;

// A heavy airframe for the contrast: B_Heli_Transport_01_F, the UH-80.
private _heavyClass = "B_Heli_Transport_01_F";
private _heavyRow = [_heavyClass] call aee_mobility_fnc_getAircraftData;
private _heavyMass = if ((count _heavyRow) > 0) then { _heavyRow select 0 } else { 0 };
private _heavyArea = [_heavyRow] call aee_mobility_fnc_resolveTurbulenceArea;

// 1. The corpus resolves the AH-9 Pawnee and holds its operating weight.
[_lightRow isEqualType [] && {(count _lightRow) == 4} && {abs (_lightMass - 782) < 1},
    format ["AH-9 Pawnee row %1 mass %2", _lightRow, _lightMass]] call _check;

// 2. The drag area is the rotor disc the corpus holds (55.154115 m^2), not the
//    0.7 m^2 kernel default: the record is the source, not a parallel table.
[abs (_lightArea - 55.154115) < 0.01,
    format ["AH-9 Pawnee drag area %1 (expected the rotor disc 55.154115)", _lightArea]] call _check;

// 3. The force is mass-free: same drag area, gust and density, two masses,
//    the same force.  The old model scaled the force with the mass.
private _fLight = [_gust, _rho, _lightArea, _lightMass] call aee_mobility_fnc_calculateTurbulenceForce;
private _fHeavySameArea = [_gust, _rho, _lightArea, _heavyMass] call aee_mobility_fnc_calculateTurbulenceForce;
[abs (_fLight - _fHeavySameArea) < 0.001,
    format ["force is not mass-free: light %1 heavy %2", _fLight, _fHeavySameArea]] call _check;

// 4. The acceleration is mass-aware: each airframe with its own drag area, the
//    heavy one accelerates less.
private _fHeavyOwnArea = [_gust, _rho, _heavyArea, _heavyMass] call aee_mobility_fnc_calculateTurbulenceForce;
private _aLight = _fLight / _lightMass;
private _aHeavy = _fHeavyOwnArea / _heavyMass;
[_aLight > _aHeavy,
    format ["heavy airframe is not steadier: aLight %1 aHeavy %2", _aLight, _aHeavy]] call _check;

// 5. The force is a real positive quantity for a real gust.
[_fLight > 0,
    format ["no force for a %1 m/s gust on the AH-9 Pawnee", _gust]] call _check;

diag_log text format [
    "[P132] AH-9 Pawnee %1 kg area %2 m^2 | heavy %3 kg area %4 m^2 | gust %5 m/s rho %6 | F(light) %7 N F(heavy,own area) %8 N | a(light) %9 m/s^2 a(heavy) %10 m/s^2",
    _lightMass, _lightArea, _heavyMass, _heavyArea, _gust, _rho,
    _fLight, _fHeavyOwnArea, _aLight, _aHeavy
];

if (_fail == 0) then {
    diag_log text format ["[P132] [PASS] turbulence gust is aerodynamic and mass-aware: %1 checks, light a %2 > heavy a %3 m/s^2", _pass, _aLight, _aHeavy];
} else {
    diag_log text format ["[P132] [FAIL] turbulence gust weight: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
