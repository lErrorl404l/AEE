#include "..\..\script_component.hpp"

/*
CBRN agent plume driver (issue #105).

Reads the active release (set by fnc_startCbrnRelease) and the core
weather state, resolves the Pasquill stability class and the Briggs
dispersion coefficients, computes the ground-level concentration at the
local unit with the steady Gaussian plume or the Gaussian puff, and
accumulates the inhalation dose.  It publishes the exposure state; a
medical or ACM consumer reads it.

Model sources:
  Gaussian plume / puff   Turner, Workbook of Atmospheric Dispersion
                          Estimates, EPA AP-26 (1970).
  Dispersion coefficients Briggs (1973), Diffusion Estimation for Small
                          Emissions, ATDL.
  Stability class         Pasquill, via Turner AP-26 Table 1.
  Agent parameters        FM 3-11, Chemical Operations (2003), Table 4-1.
  Rain washout            Lambda = 8.4e-5 * I^0.79 (I in mm/h).

Publishes:
  aee_core_cbrnPlumeConcentration   (mg/m3)
  aee_core_cbrnPlumeDose            (mg*min/m3)
  aee_core_cbrnPlumeLethal          (BOOL)
  aee_core_cbrnPlumeIncapacitated   (BOOL)
  aee_core_cbrnStabilityClass       (STRING)
  aee_core_cbrnPlumeActive          (BOOL)
  aee_core_cbrnDepositionFlux       (mg/m2/s)
*/

params [["_posASL", [], [[]]]];

if (!GVAR(CbrnPlumeEnabled)) exitWith {};

private _release = missionNamespace getVariable [QEGVAR(core,cbrnRelease), []];
private _active = (_release isEqualType []) && {(count _release) >= 7} && {_release select 0};

if (!_active) exitWith {
    missionNamespace setVariable [QEGVAR(core,cbrnPlumeActive), false];
};

private _srcPos   = _release select 1;
private _agent    = _release select 2;
private _strength = _release select 3;
private _altitude = _release select 4;
private _isBurst  = _release select 5;
private _startTime = _release select 6;

// ─── Observer ───────────────────────────────────────────────────────────────
private _observer = call CBA_fnc_currentUnit;
private _obsPos = _posASL;
if ((count _obsPos) < 3) then {
    if (!isNil "_observer" && {!isNull _observer}) then {
        _obsPos = getPosASL _observer;
    } else {
        _obsPos = [0, 0, 0];
    };
};

// ─── Weather state (the core environment tick owns these) ────────────────────
private _wind = missionNamespace getVariable [QEGVAR(core,currentWind), [0, 0]];
private _u = (missionNamespace getVariable [QEGVAR(core,currentWindStr), 0]) max 0.5;
private _solarFlux = missionNamespace getVariable [QEGVAR(core,currentSolarFlux), 0];
private _overcast = overcast;
private _oktas = _overcast * 8;
private _isDay = _solarFlux > 1;
private _rain = rain;

private _class = [_u, _solarFlux, _oktas, _isDay] call FUNC(getStabilityClass);

// ─── Downwind / crosswind geometry ──────────────────────────────────────────
private _wx = _wind select 0;
private _wy = _wind select 1;
private _ux = _wx / _u;
private _uy = _wy / _u;
// A dead-calm vector has no direction: default the plume downwind to +x.
if ((abs _wx) + (abs _wy) < 0.001) then { _ux = 1; _uy = 0; };

private _rx = (_obsPos select 0) - (_srcPos select 0);
private _ry = (_obsPos select 1) - (_srcPos select 1);
private _x = _rx * _ux + _ry * _uy;
private _y = -_rx * _uy + _ry * _ux;
private _z = (_obsPos select 2) - (_srcPos select 2);
if (_z < 0) then { _z = 0; };

// ─── Distance cull ──────────────────────────────────────────────────────────
// A vapour reaches further than a ground-hugging release.
private _cull = 2000;
if (_altitude <= 1) then { _cull = 500; };

private _agentRow = [_agent] call FUNC(getCbrnAgent);
private _halfLife = _agentRow select 3;

private _concentration = 0;

if ((_x > 0) && (_x <= _cull)) then {
    private _sigmas = [_x, _class, false] call FUNC(getDispersionCoefficients);
    private _sy = _sigmas select 0;
    private _sz = _sigmas select 1;

    if (_isBurst) then {
        // Puff: sigma_x = sigma_y for the instantaneous cloud.
        _concentration = [_strength, _sy, _sy, _sz, 0, _y] call FUNC(calculatePuffConcentration);
    } else {
        _concentration = [_strength, _u, _sy, _sz, _altitude, _y, _z] call FUNC(calculatePlumeConcentration);
    };

    // ─── Decay: intrinsic half-life, then rain washout ─────────────────────
    private _elapsedH = (diag_tickTime - _startTime) / 3600;
    _concentration = [_concentration, _elapsedH, _halfLife] call FUNC(calculateCbrnDecay);

    if (_rain > 0) then {
        // The engine `rain` command is a 0..1 level, not mm/h.  The 50
        // mm/h full-scale mapping is UNSOURCED (a heavy-rain proxy).
        private _rainMMh = _rain * 50;
        private _lambda = 8.4e-5 * (_rainMMh ^ 0.79);
        _concentration = _concentration * exp (-_lambda * _x / _u);
    };
};

// ─── Dose accumulation ──────────────────────────────────────────────────────
private _protection = 0;
if (!isNil "_observer" && {!isNull _observer}) then {
    _protection = [_observer] call EFUNC(persistence,getCbrnProtection);
};
private _lcT50 = _agentRow select 0;
private _dt = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
private _dose = missionNamespace getVariable [QEGVAR(core,cbrnPlumeDose), 0];

private _result = [_dose, _concentration, _dt, _lcT50, _protection] call FUNC(calculateCbrnDose);

// ─── Publish ────────────────────────────────────────────────────────────────
missionNamespace setVariable [QEGVAR(core,cbrnPlumeConcentration), _concentration];
missionNamespace setVariable [QEGVAR(core,cbrnPlumeDose), _result select 0];
missionNamespace setVariable [QEGVAR(core,cbrnPlumeLethal), _result select 1];
missionNamespace setVariable [QEGVAR(core,cbrnPlumeIncapacitated), _result select 2];
missionNamespace setVariable [QEGVAR(core,cbrnStabilityClass), _class];
missionNamespace setVariable [QEGVAR(core,cbrnPlumeActive), true];
// Dry deposition flux = vd * C, vd ~ 0.002 m/s (vapour).  The ground
// contamination model consumes this.
missionNamespace setVariable [QEGVAR(core,cbrnDepositionFlux), 0.002 * _concentration];
