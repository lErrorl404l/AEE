// PHASE 91: the engine thermal-model surface, headless (aee-thermal-realism
// T10).
//
// The engine renders thermal imaging from a per-object temperature model.
// It exposes no `thermalProperties` field.  Its heat model is the scalar set
// (htMin/htMax/afMax/mfMax/mFact/tBody), and a material's `class StageTI`
// texture channels are heat-source coefficients into that model.  A headless
// probe cannot read pixels, so this verifies the resolved config keys and the
// TI command contract only.

private _pass = 0;
private _fail = 0;
private _notes = [];

// (1) The scalar heat keys resolve on a sample road vehicle.
private _cls = "C_Offroad_01_F";
private _cfg = configFile >> "CfgVehicles" >> _cls;
private _heatKeys = ["htMin", "htMax", "afMax", "mfMax", "mFact", "tBody"];
private _found = 0;
{
    if (isNumber (_cfg >> _x)) then { _found = _found + 1; };
} forEach _heatKeys;
if (_found >= 4) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["heat keys %1/6 on %2", _found, _cls];
};

// (2) The declared render-heat values are loaded on AllVehicles.
private _allVeh = configFile >> "CfgVehicles" >> "AllVehicles";
if ((isNumber (_allVeh >> "htMin")) && {(getNumber (_allVeh >> "htMin")) == 60}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "AllVehicles htMin is not the declared 60";
};

// (3) No `thermalProperties` entry exists on the sample class.
private _tp = _cfg >> "thermalProperties";
if (!(isNumber _tp) && {!(isArray _tp)} && {!(isClass _tp)}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "thermalProperties present";
};

// (4) The engine TI parameter read, informational (A3 2.10+).
private _ti = getTIParameters;
if (!isNil "_ti") then {
    _notes pushBack "getTIParameters present";
} else {
    _notes pushBack "getTIParameters nil";
};

if ((_fail == 0) && {_pass >= 3}) then {
    diag_log text format ["[P91] [PASS] engine thermal surface: %1 checks, %2", _pass, _notes];
} else {
    diag_log text format ["[P91] [FAIL] engine thermal surface: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
