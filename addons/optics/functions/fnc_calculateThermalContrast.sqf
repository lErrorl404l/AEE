#include "..\script_component.hpp"

/*
Thermal contrast coefficient (0–1) for FLIR/thermal imaging effectiveness.

  1.0 = perfect contrast (crisp thermal signature)
  0.0 = no usable contrast

Heat flattens the thermal gradient: above 35 °C the contrast drops linearly
to a floor of 0.3 at 45 °C+.  Rain and fog scatter/absorb IR, reducing
effectiveness proportionally.  Cold air (<5 °C) boosts contrast by widening
the object–ambient temperature gap.

Stored in GVAR(currentThermalContrast) for external query by sensor
simulations, FLIR overlay systems, or AI target-acquisition modifiers.
*/

private _contrast = 1.0;

private _T = EGVAR(core,currentTemperature);
private _fog = missionNamespace getVariable [QEGVAR(core,currentFogDensity), 0];

// ─── Extreme heat — gradient flattens ────────────────────────────────────
if (!isNil "_T" && _T > 35) then {
    _contrast = _contrast - ((_T - 35) / 10) * 0.7; // linear to 0.3 at 45 °C
};

// ─── Rain — moisture absorbs IR ──────────────────────────────────────────
if (rain > 0) then {
    _contrast = _contrast * (1 - rain * 0.4);
};

// ─── Fog — scattering and absorption ─────────────────────────────────────
if (_fog > 0) then {
    _contrast = _contrast * (1 - _fog * 0.6);
};

// ─── Cold boost — widened thermal gap ────────────────────────────────────
if (!isNil "_T" && _T < 5) then {
    _contrast = (_contrast * 1.2) min 1.0;
};

_contrast = _contrast max 0 min 1;

missionNamespace setVariable [QGVAR(currentThermalContrast), _contrast];
