// PHASE 109: the tracker error model under a degraded signal.
//
// The tracker driver FUNC(trackerUpdate) runs only on a client (it exits on
// !hasInterface), so the probe drives the REAL pure projector
// FUNC(trackerProject) with the three REAL GNSS kernels in a degraded state:
// high DOP, canopy, urban and jamming on the error ellipse; a re-acquisition
// ramp on the fix state; a far, masked, jammed datalink.  The projector must
// return a NON-ZERO total error and a displayed position that DIFFERS from the
// exact one.  A nominal case is the control: the degradation must raise the
// error above it.
//
// Emits [P109] PASS/FAIL lines.

private _fnEllipse = missionNamespace getVariable ["aee_lib_fnc_gnssErrorEllipse", nil];
private _fnFix = missionNamespace getVariable ["aee_lib_fnc_gnssFixState", nil];
private _fnLink = missionNamespace getVariable ["aee_lib_fnc_datalinkState", nil];
private _fnProject = missionNamespace getVariable ["aee_hud_fnc_trackerProject", nil];
if (isNil "_fnEllipse" || {isNil "_fnFix"} || {isNil "_fnLink"} || {isNil "_fnProject"}) exitWith {
    diag_log text "[P109] [FAIL] tracker kernels not compiled (gnssErrorEllipse/gnssFixState/datalinkState/trackerProject)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

private _exact = [1000, 2000, 10];

// Degraded: DOP 8, canopy, urban, half-power jamming, receiver 0.8; the signal
// is below the acquisition floor so the fix lags; a far, masked, jammed link.
private _ellipse = [8.0, 3.6, 0.5, 0.5, 0.5, 0.5, 0.8] call _fnEllipse;
private _fix = [1.0, 0.2, 0.0, [0, 0.5]] call _fnFix;
private _link = [6000, 1, 1, 1, 100] call _fnLink;
private _projected = [_exact, _ellipse, _fix, _link, 1] call _fnProject;
private _displayed = _projected select 0;
private _totalError = _projected select 5;

// Nominal control: DOP 1, clear sky, a good fix and a short clean link.
private _nomEllipse = [1.0, 3.6, 0, 0, 0, 0, 1] call _fnEllipse;
private _nomFix = [1.0, 1.0, 0, [0, 1]] call _fnFix;
private _nomLink = [100, 0, 0, 0, 100] call _fnLink;
private _nomProjected = [_exact, _nomEllipse, _nomFix, _nomLink, 1] call _fnProject;
private _nomError = _nomProjected select 5;

// 1. the degraded total error is non-zero
if (_totalError > 0) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "degraded total error is zero";
};

// 2. the displayed position differs from the exact one
private _displacement = _exact distance _displayed;
if (_displacement > 0) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "displayed position equals the exact position";
};

// 3. the displacement is the modelled error
if (abs (_displacement - _totalError) <= 0.01) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["displacement %1 vs total error %2", _displacement, _totalError];
};

// 4. degradation raises the error above the nominal control
if (_totalError > _nomError) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["degraded %1 not above nominal %2", _totalError, _nomError];
};

diag_log text format ["[P109] tracker error: degraded %1 m (r95 %2, lag %3, link add %4), nominal %5 m", _totalError, _ellipse select 7, _fix select 3, _link select 3, _nomError];

if (_fail == 0) then {
    diag_log text format ["[P109] [PASS] tracker error model under a degraded signal (%1 checks)", _pass];
} else {
    diag_log text format ["[P109] [FAIL] tracker error model: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
