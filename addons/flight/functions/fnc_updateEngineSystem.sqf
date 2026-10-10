#include "..\script_component.hpp"

/*
Manage one local aircraft engine for one interval and publish a scripted
turbine-temperature and oil-pressure readout.

WHY THIS FUNCTION EXISTS.  The engine exposes no turbine temperature, no
exhaust gas temperature, no inter-turbine temperature, no oil pressure, no
start state and no wear in any model.  This kernel commands the spool with
setWantedRPMRTD when the advanced flight model is on, reads the live engine
speed with enginesRpmRTD, and it computes the turbine temperature and the oil
pressure as a SCRIPTED readout from the sourced limits in the generated
systems row.

THE CEILING.  Turbine temperature, exhaust gas temperature, inter-turbine
temperature, oil, start and wear are NOT exposed by the engine.  They are
SCRIPTED from the sourced limits.  THE SCRIPTED TURBINE TEMPERATURE IS
NOT A MEASUREMENT.  It is a declared readout between the sourced limits.

setWantedRPMRTD IS RTD-ONLY.  In the simple flight model
difficultyEnabledRTD is false, the command is a no-op, and the scripted
turbine temperature and oil still run from the sourced limits.  The kernel
guards the whole RTD path, the getter and the command, on
difficultyEnabledRTD.  The getter and the command are compiled from a string,
because the RTD command set differs between the game client and the
dedicated-server binary, exactly as fnc_applyExhaustShimmer does.  The simple
model publishes no spool reader, so the kernel carries the spool state itself
in a per-vehicle variable and drives it with the pure helper
fnc_calculateEngineNg.

THE RPM BASE.  The commanded value is an engine RPM, not a ratio.  The base
is the published engine_design_rpm from the systems row.  When the corpus
holds no design speed, the base falls back to getEngineTargetRPMRTD (engine
0), gated on difficultyEnabledRTD.  With no base the kernel issues no
command.

THE TARGET.  The commanded fraction in 0..1 selects the sourced idle speed
at zero and the sourced maximum speed at one, interpolated between.  The
command is setWantedRPMRTD [_baseRpm * _newNg, tau, -1], the engine RPM for
every engine.

THE SCRIPTED READOUT.  fnc_calculateScriptedTgtOil maps the new speed onto
the sourced turbine-temperature band and the sourced oil band.  The kernel
publishes the three values as per-vehicle variables for a status consumer.

DETERMINISM AND LOCALITY.  The kernel runs on the machine that owns the
airframe, INCLUDING the server, so a server-owned AI airframe still gets the
scripted readout.  The local test is the gate.

Guards, each explicit:
  - A null or dead vehicle is refused.
  - A non-Air vehicle is refused.  A parachute is an Air object with no
    engine, so it is refused.
  - A non-local vehicle is refused, so only the owning machine writes.
  - An unknown class has no systems row, so it is refused.
  - A non-positive idle speed or a maximum speed not above the idle speed is
    refused, because the spool span would be unusable.

Arguments:
  0:  _veh        (OBJECT) the aircraft to manage
  1:  _wanted     (NUMBER) commanded spool fraction, 0 idle to 1 maximum
  2:  _deltaTimeS (NUMBER) elapsed interval, s, default diag_deltaTime

Return Value: BOOL - true when the engine state was written
Example: [cursorObject, 1, 1] call aee_flight_fnc_updateEngineSystem
Public: No
*/

params [
    ["_veh", objNull, [objNull]],
    ["_wanted", 0, [0]],
    ["_deltaTimeS", diag_deltaTime, [0]]
];

if (isNull _veh || {!alive _veh}) exitWith { false };
if !(_veh isKindOf "Air") exitWith { false };
if (_veh isKindOf "ParachuteBase") exitWith { false };

// Deterministic and local, INCLUDING the server. The owning machine is the
// only writer.
if (!local _veh) exitWith { false };

if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { false };

private _systems = [typeOf _veh] call FUNC(getAircraftSystems);
if (_systems isEqualTo []) exitWith { false };

// The systems row holds the numeric fields first, in the generated order:
// 0 fuel_capacity, 1 fuel_consumption_rate, 2 fuel_density_kg_l,
// 3 sfc_kg_kwh, 4 fuel_cg_arm_m, 5 engine_design_rpm, 6 engine_idle_ng,
// 7 engine_max_ng, 8 engine_max_np, 9 engine_max_torque_nm, 10 engine_max_tgt_c,
// 11 engine_oil_pressure_min_kpa, 12 engine_oil_pressure_max_kpa.
private _designRpm = _systems select 5;
private _idleNg = _systems select 6;
private _maxNg = _systems select 7;
private _maxTgtC = _systems select 10;
private _oilMinKpa = _systems select 11;
private _oilMaxKpa = _systems select 12;

if (_idleNg <= 0 || _maxNg <= _idleNg) exitWith { false };

// The commanded speed is the sourced idle at zero and the sourced maximum
// at one, interpolated between.
private _wantedNg = _idleNg + ((_maxNg - _idleNg) * (_wanted max 0 min 1));

// The RPM base is the published design speed. When the corpus holds none,
// the fallback reads the engine's own target RPM, gated on the advanced
// flight model.
private _baseRpm = _designRpm;
if (difficultyEnabledRTD && _baseRpm <= 0) then {
    private _targetCode = compile "getEngineTargetRPMRTD _this";
    private _targets = _veh call _targetCode;
    if (_targets isEqualType [] && {(_targets select 0) isEqualType 0}) then {
        _baseRpm = _targets select 0;
    };
};

// The previous scripted speed is the spool state in the simple model.
private _currentNg = _idleNg;
private _stored = _veh getVariable [QGVAR(engineNg), -1];
if (_stored isEqualType 0) then {
    if (_stored >= 0) then { _currentNg = _stored; };
};

// Under the advanced flight model the live engine speed seeds the spool,
// scaled to a ratio by the RPM base. The reader is compiled from a string,
// because the RTD command set differs between the game client and the
// dedicated-server binary, exactly as fnc_applyExhaustShimmer does.
if (difficultyEnabledRTD && _baseRpm > 0) then {
    private _reader = "enginesRpmRTD _this";
    private _code = compile _reader;
    private _live = _veh call _code;
    if (_live isEqualType [] && {(_live select 0) isEqualType 0}) then {
        _currentNg = ((_live select 0) / _baseRpm) max 0 min _maxNg;
    };
};

// Spool the speed toward the wanted value with the declared time constant.
private _newNg = [_currentNg, _wantedNg, _deltaTimeS, AEE_ENGINE_SPOOL_TAU_S] call FUNC(calculateEngineNg);
if (_newNg < 0) exitWith { false };

// Command the engine spool. setWantedRPMRTD takes the engine RPM for every
// engine, the time to reach it, and the engine index (-1 is every engine).
// It is RTD-ONLY and is a no-op in the simple flight model. The non-existent
// engine-rpm setter is never used.
if (difficultyEnabledRTD && _baseRpm > 0) then {
    _veh setWantedRPMRTD [(_baseRpm * _newNg) max 0, AEE_ENGINE_SPOOL_TAU_S, -1];
};

private _state = [_newNg, _idleNg, _maxNg, _maxTgtC, _oilMinKpa, _oilMaxKpa] call FUNC(calculateScriptedTgtOil);
if (_state isEqualTo [0, 0]) exitWith { false };

_veh setVariable [QGVAR(engineNg), _newNg];
_veh setVariable [QGVAR(engineTgtC), _state select 0];
_veh setVariable [QGVAR(engineOilKpa), _state select 1];

true
