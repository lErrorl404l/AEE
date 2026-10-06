// PHASE 93: the thermal detector band resolver, headless
// (aee-thermal-realism T18).
//
// WHY THIS EXISTS.  A cooled InSb detector and the cooled MWIR MCT devices
// use the 3-5 um band; an uncooled microbolometer and the cooled LWIR MCT
// use the 8-14 um band.  The band is a per-device corpus field, so the
// resolver maps a band token to its edges and defaults to LWIR for an
// unknown token.  The kernel is pure, so a dedicated server calls it
// directly.  It renders nothing.
//
// Emits: [P93] [PASS] / [P93] [FAIL] <reason>.

private _KERNEL = "aee_thermal_fnc_resolveThermalBand";
private _pass = 0;
private _fail = 0;
private _notes = [];

if (isNil _KERNEL) then {
    _fail = _fail + 1;
    _notes pushBack "resolver kernel is not compiled";
} else {
    private _mwir = ["mwir"] call aee_thermal_fnc_resolveThermalBand;
    private _lwir = ["lwir"] call aee_thermal_fnc_resolveThermalBand;

    // 1. The MWIR pair in metres.
    if ((_mwir isEqualType []) && {(_mwir select 0) isEqualTo 3e-6} && {(_mwir select 1) isEqualTo 5e-6}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["mwir %1", str _mwir];
    };

    // 2. The LWIR pair in metres.
    if ((_lwir isEqualType []) && {(_lwir select 0) isEqualTo 8e-6} && {(_lwir select 1) isEqualTo 14e-6}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["lwir %1", str _lwir];
    };

    // 3. An unknown token resolves to the LWIR pair, the honest default.
    private _unknown = ["microwave"] call aee_thermal_fnc_resolveThermalBand;
    if (_unknown isEqualTo _lwir) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["unknown %1", str _unknown];
    };

    // 4. The empty token (the documented default) also resolves to LWIR.
    private _default = [""] call aee_thermal_fnc_resolveThermalBand;
    if (_default isEqualTo _lwir) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["default %1", str _default];
    };

    // 5. The token is case-insensitive.
    private _upper = ["MWIR"] call aee_thermal_fnc_resolveThermalBand;
    if (_upper isEqualTo _mwir) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["MWIR %1", str _upper];
    };

    _notes pushBack format ["mwir=%1 lwir=%2", str _mwir, str _lwir];
};

if (_fail == 0) then {
    diag_log text format ["[P93] [PASS] thermal band: %1 checks, %2", _pass, _notes];
} else {
    diag_log text format ["[P93] [FAIL] thermal band: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
