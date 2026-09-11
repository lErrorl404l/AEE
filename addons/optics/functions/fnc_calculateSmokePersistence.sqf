#include "..\script_component.hpp"

/*
Smoke dispersal time modifier (0.2–3.0).

Computes how long smoke persists relative to baseline:
  1.0 = default
  <1.0 = disperses faster (wind, hot/dry, rain)
  >1.0 = persists longer (high humidity)

Wind is the primary dispersive force. High humidity (RH >0.6) extends
persistence by weighting the excess moisture. Hot-and-dry conditions
(temp >30 °C, RH <0.4) accelerate dispersal. Rain washes smoke out
of the air column.

Stored in QGVAR(smokeDispersalModifier) for consumption by
smoke-effect duration systems.
*/

params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith { 0 };  // no unit on dedicated server

// ─── Inputs ────────────────────────────────────────────────────────────
private _windSpeed = vectorMagnitude (missionNamespace getVariable [QEGVAR(core,currentWind), [0, 0]]);
private _humidity  = EGVAR(core,currentHumidity);
private _temp      = EGVAR(core,currentTemperature);
private _rain      = rain;

if (isNil "_humidity") then { _humidity = 0.5; };
if (isNil "_temp")     then { _temp     = 20;  };
if (isNil "_rain")     then { _rain     = 0;   };

// ─── Modifier ──────────────────────────────────────────────────────────
private _modifier = 1.0;

// Wind: primary dispersal force
_modifier = _modifier / (1 + _windSpeed * 0.15);

// High humidity (>60 %) extends persistence (moist air holds smoke longer)
if (_humidity > 0.6) then {
    _modifier = _modifier * (1 + (_humidity - 0.5) * 0.5);
};

// Hot and dry (temp >30 °C, RH <40 %) — faster dispersal
if (_temp > 30 && _humidity < 0.4) then {
    _modifier = _modifier * 0.7;
};

// Rain washes smoke
if (_rain > 0) then {
    _modifier = _modifier * 0.6;
};

// Clamp
_modifier = _modifier max 0.2 min 3.0;

// ─── Store ─────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(smokeDispersalModifier), _modifier];

_modifier
