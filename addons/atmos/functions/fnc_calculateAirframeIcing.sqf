#include "..\script_component.hpp"

/*
Airframe icing from supercooled liquid water (LWC), FAR 25 Appendix C
envelope concept.

Ice accretes while flying through visible moisture (cloud or
precipitation) at temperatures between -20 °C and 0 °C.  The accretion
rate scales with liquid water content and the collection efficiency of
the ice type:

  Glaze — 0 to -10 °C, wet growth, high collection efficiency
  Rime  — below -10 °C, dry growth, lower collection efficiency

Ice mass accumulates per tick and drives the 0-1 severity used for
lift/drag degradation.  Ice sheds when conditions warm or dry out.

Stored in GVAR(airframeIcing)        — float 0-1 severity
Stored in GVAR(airframeIcingDetected) — bool
Stored in GVAR(iceAccretion_kg)       — float 0 to the configured maximum
*/

private _temp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _overcast = overcast;
private _rain = rain;

private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];

// ─── Settings ─────────────────────────────────────────────────────────────
private _maxIceMass = missionNamespace getVariable [QGVAR(maxIceMass), 100];
private _shedRate   = missionNamespace getVariable [QGVAR(icingShedRate), 0.9];
_shedRate = _shedRate ^ (_interval / 5);   // per-tick multiplier scales with interval

// ─── Liquid water content proxy (FAR 25 App C envelope) ──────────────────
// Cloud LWC up to ~0.5 g/m3; precipitation adds up to ~2 g/m3.
private _lwc = (_overcast * 0.5) + (_rain * 2);

// ─── Collection efficiency by ice type ───────────────────────────────────
// Glaze (0 to -10 °C): wet growth, high collection.
// Rime (below -10 °C): dry growth, lower collection.
private _efficiency = 0;
if (_temp > -10) then {
    _efficiency = 0.8;   // glaze
} else {
    _efficiency = 0.4;   // rime
};

// ─── Accretion ───────────────────────────────────────────────────────────
private _iceMass = missionNamespace getVariable [QGVAR(iceAccretion_kg), 0];

if (_temp > -20 && _temp < 0 && (_overcast > 0.5 || _rain > 0)) then {
    private _icingRate = _lwc * _efficiency * 0.05;   // kg/s
    _iceMass = _iceMass + (_icingRate * _interval);
} else {
    // Shedding — warm or dry air removes ice
    _iceMass = _iceMass * _shedRate;
};

_iceMass = _iceMass max 0 min _maxIceMass;

// ─── Performance degradation (0-1) driven by accretion ───────────────────
private _severity = _iceMass / _maxIceMass;

private _detected = _severity > 0.01;

missionNamespace setVariable [QGVAR(iceAccretion_kg), _iceMass];
missionNamespace setVariable [QGVAR(airframeIcing), _severity];
missionNamespace setVariable [QGVAR(airframeIcingDetected), _detected];

_severity
