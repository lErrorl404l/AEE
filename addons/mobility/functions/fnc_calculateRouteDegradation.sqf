#include "..\script_component.hpp"

/*
Route degradation accumulator (0–1) and traction modifier (0.5–1.0).

Tracks cumulative traffic-induced surface wear on unpaved terrain.

  • Wet/Muddy conditions degrade faster (vehicle churning soft ground).
  • Snow cover degrades slowly (compacts but hides damage).
  • Frozen/Normal ground recovers (freeze-thaw heals ruts, or firm
    surface resists new damage).

The degradation feeds a traction modifier:
    tractionModifier = 1.0 − (degradation × 0.5)
so at full degradation (1.0) traction is halved.

This is a global (mission-wide) value — route condition affects all vehicles.

ponytail: scalar accumulator, not a per-tile erosion model.
Stored in QGVAR(routeDegradation) and QGVAR(tractionModifier).
*/

// ─── Inputs ────────────────────────────────────────────────────────────────
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _humidity    = EGVAR(core,currentHumidity);

if (isNil "_humidity") then { _humidity = 50; };

// ─── Load current degradation ──────────────────────────────────────────────
private _degradation = missionNamespace getVariable [QGVAR(routeDegradation), 0];

// ─── Degradation / recovery per tick ───────────────────────────────────────
if (_groundState == "Mud") then {
    _degradation = _degradation + 0.005;
} else {
    if (_groundState == "Frozen" || _groundState == "Normal") then {
        _degradation = _degradation - 0.01;
    } else {
        if (_groundState == "Snow") then {
            _degradation = _degradation + 0.002;
        };
    };
};

// Also degrade if very humid (soft ground without standing water)
if (_groundState != "Frozen" && _humidity > 70) then {
    _degradation = _degradation + 0.005;
};

// ─── Clamp ─────────────────────────────────────────────────────────────────
_degradation = _degradation max 0 min 1;

// ─── Compute traction modifier ─────────────────────────────────────────────
private _tractionModifier = (1 - _degradation * 0.5) max 0.5 min 1.0;

missionNamespace setVariable [QGVAR(routeDegradation), _degradation];
missionNamespace setVariable [QGVAR(tractionModifier), _tractionModifier];

_degradation
