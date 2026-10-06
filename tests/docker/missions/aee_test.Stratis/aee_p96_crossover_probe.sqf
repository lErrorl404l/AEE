// PHASE 96: thermal crossover reads the ground node stack, headless
// (aee-thermal-realism T18).
//
// WHY THIS EXISTS.  Crossover used to read a `groundState` switch.  It now
// publishes the FIRST LAYER of the four-layer ground node stack as the
// surface temperature, so every thermal consumer exchanges with the same
// surface.  A dedicated server can call both kernels and compare the
// published value against a direct stack read.  It renders nothing.
//
// The stack is time-integrated, so the direct call advances it by the 0.1 s
// minimum step.  The comparison is therefore bounded, not exact.  The bound
// is far below the retired ground-state fallback offset (about 2 K), so a
// regression to the fallback still fails the probe.
//
// Emits: [P96] [PASS] / [P96] [FAIL] <reason>.

private _FN_X = "aee_thermal_fnc_calculateThermalCrossover";
private _FN_STACK = "aee_thermal_fnc_calculateGroundNodeStack";
private _pass = 0;
private _fail = 0;
private _notes = [];

if ((isNil _FN_X) || {isNil _FN_STACK}) then {
    _fail = _fail + 1;
    _notes pushBack "crossover or node-stack kernel is not compiled";
} else {
    // Reproduce the position the crossover resolves: the current unit's ASL
    // position, else the map origin on a headless server.
    private _unit = call CBA_fnc_currentUnit;
    private _pos = [];
    if (!isNil "_unit" && {!isNull _unit}) then { _pos = getPosASL _unit; };
    if ((count _pos) < 2) then { _pos = [0, 0, 0]; };

    [] call aee_thermal_fnc_calculateThermalCrossover;
    private _stored = missionNamespace getVariable ["aee_core_surfaceTemperature", nil];
    private _stack = [_pos] call aee_thermal_fnc_calculateGroundNodeStack;
    private _layer0 = _stack select 0;

    if (isNil "_stored") then {
        _fail = _fail + 1;
        _notes pushBack "crossover published no surface temperature";
    } else {
        // 1. The crossover published a numeric surface temperature.
        if (_stored isEqualType 0) then {
            _pass = _pass + 1;
        } else {
            _fail = _fail + 1;
            _notes pushBack format ["stored surface is %1", str _stored];
        };

        // 2. The published surface is the stack first layer.
        if ((_layer0 isEqualType 0) && {finite _layer0} && {abs (_stored - _layer0) < 0.5}) then {
            _pass = _pass + 1;
        } else {
            _fail = _fail + 1;
            _notes pushBack format ["stored %1, stack layer0 %2", _stored, _layer0];
        };
    };

    // 3. The stack carries the four-layer column, so the crossover surface is
    //    a real solved layer and not a two-value switch.
    if ((_stack isEqualType []) && {(count _stack) >= 4}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["stack shape %1", str _stack];
    };

    _notes pushBack format ["stored=%1 layer0=%2", _stored, _layer0];
};

if (_fail == 0) then {
    diag_log text format ["[P96] [PASS] crossover surface: %1 checks, %2", _pass, _notes];
} else {
    diag_log text format ["[P96] [FAIL] crossover surface: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
