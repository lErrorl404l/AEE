#include "..\script_component.hpp"

/*
Fire danger index (0–1) for wildfire and combat-fire spread modelling.

Factors — each adds to the risk when its threshold is crossed:
  • Temperature  >30 °C   +0.4
  • Humidity     <30 %    +0.3
  • Wind speed   >5 m/s   +0.2
  • Ground state "Dusty"  +0.2
  • Foliage density <0.2  +0.1  (sparse fuel = less shade, drier duff)

Rain instantly suppresses fire risk to zero.

The sum is capped at 1.0 — diminishing returns at high fire danger are
deliberately omitted so the index serves as a crisp binary indicator for
systems that need a yes/no fire-spread gate.

Stored in GVAR(currentFireRisk) for consumption by wildfire propagation,
AI behaviour (e.g. avoid fire), and pyrotechnic effect systems.
*/

private _risk = 0;

private _T = EGVAR(core,currentTemperature);
private _RH = EGVAR(core,currentHumidity);
private _windSpeed = vectorMagnitude wind;
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _foliage = missionNamespace getVariable [QEGVAR(environmental,currentFoliageDensity), 0.5];

// ─── Temperature ─────────────────────────────────────────────────────────
if (!isNil "_T" && _T > 30) then { _risk = _risk + 0.4; };

// ─── Low humidity ────────────────────────────────────────────────────────
if (!isNil "_RH" && _RH < 30) then { _risk = _risk + 0.3; };

// ─── Wind ────────────────────────────────────────────────────────────────
if (_windSpeed > 5) then { _risk = _risk + 0.2; };

// ─── Dusty ground ────────────────────────────────────────────────────────
if (_groundState == "Dusty") then { _risk = _risk + 0.2; };

// ─── Sparse foliage (dry duff, less shade) ──────────────────────────────
if (_foliage < 0.2) then { _risk = _risk + 0.1; };

// ─── Rain — immediate suppression ────────────────────────────────────────
if (rain > 0) then { _risk = 0; };

_risk = _risk min 1;

missionNamespace setVariable [QGVAR(currentFireRisk), _risk];
