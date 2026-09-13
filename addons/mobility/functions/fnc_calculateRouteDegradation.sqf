#include "..\script_component.hpp"

/*
Route degradation accumulator (0–1) and traction modifier (0.5–1.0).

NRMM (NATO Reference Mobility Model) cone-index approach: each vehicle
passage reduces the soil cone index in proportion to the vehicle ground
pressure, and the soil recovers exponentially toward its nominal value.

  • Cone index starts at 1.0 (nominal firm soil)
  • Ground pressure estimated as getMass / 8 (nominal track area)
  • Recovery per 5 s tick toward 1.0 (setting routeRecoveryRate)
  • Passability = current CI / required CI (1.0), clamped 0–1

The passability feeds the legacy stores:
    degradation      = 1 − passability
    tractionModifier = 1.0 − (degradation × 0.5)

This is a global (mission-wide) value — route condition affects all vehicles.

ponytail: single global cone index, not a per-tile erosion model.
Stored in QGVAR(routeConeIndex), QGVAR(routePassability),
QGVAR(routeDegradation) and QGVAR(tractionModifier).
*/

// ─── Load current cone index ───────────────────────────────────────────────
private _coneIndex = missionNamespace getVariable [QGVAR(routeConeIndex), 1.0];
private _recoveryRate = missionNamespace getVariable [QGVAR(routeRecoveryRate), 1.001];
private _damageRate = missionNamespace getVariable [QGVAR(routeDamageRate), 0.00002];
private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];

// ─── Exponential recovery toward nominal 1.0 ───────────────────────────────
_coneIndex = (_coneIndex * (_recoveryRate ^ (_interval / 5))) min 1.0;

// ─── Vehicle passage damage ─────────────────────────────────────────────────
private _player = call CBA_fnc_currentUnit;
if (!isNil "_player") then {
    private _vehicles = _player nearEntities [["Car", "Tank", "Motorcycle"], 200];
    {
        if (isNull _x) then { continue; };
        if (abs speed _x < 1) then { continue; };   // parked vehicles do not pass
        private _groundPressure = (getMass _x) / 8;
        _coneIndex = _coneIndex - (_groundPressure * _damageRate * (_interval / 5));
    } forEach _vehicles;
};

// ─── Clamp ─────────────────────────────────────────────────────────────────
_coneIndex = _coneIndex max 0.1 min 1.0;

// ─── Passability and legacy stores ─────────────────────────────────────────
private _requiredCI = 1.0;
private _passability = (_coneIndex / _requiredCI) max 0 min 1;
private _degradation = 1 - _passability;
private _tractionModifier = (1 - _degradation * 0.5) max 0.5 min 1.0;

missionNamespace setVariable [QGVAR(routeConeIndex), _coneIndex];
missionNamespace setVariable [QGVAR(routePassability), _passability];
missionNamespace setVariable [QGVAR(routeDegradation), _degradation];
missionNamespace setVariable [QGVAR(tractionModifier), _tractionModifier];

_degradation
