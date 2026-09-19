#include "..\script_component.hpp"

/*
Atmospheric seeing / turbulence index (0.1–1.0) for extreme long-range optics.

Higher values = worse seeing (more shimmer, distortion).
Lower values = clearer air (better for observation >1000 m).

Model chain: thermal convection + wind shear → refractive-index structure
parameter Cn² → Fried parameter r0 → seeing index.

  Cn² (boundary layer) = [C_T² · (79e-6 · P / T)²] + mechanical term
  r0 = 0.185 · (λ² / Cn²)^(3/5)          (Fried, Kolmogorov turbulence)
  seeing ∝ Cn²^(1/5)                     (r0 ∝ Cn²^(−3/5), θ ∝ λ/r0)

  • Daytime sun heats the ground → C_T² rises → Cn² rises → poor seeing
  • Night: thermal convection stops, only mechanical turbulence remains
  • High wind shear (turbulence index) adds mechanical Cn²
  • High humidity adds water-vapour refractive-index fluctuation

Stored in QGVAR(atmosphericSeeing). Lower = better.
*/

// ─── Inputs ────────────────────────────────────────────────────────────────
private _turbulence = missionNamespace getVariable [QEGVAR(core,currentTurbulence), 0];
private _temp       = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _humidity   = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _overcast   = ([] call EFUNC(core,getSmoothedWeather)) select 1;
private _daytime    = sunOrMoon == 1;

// ─── Thermal convection Cn² (daytime boundary-layer heating) ───────────────
// Globe temperature: T + 15 in full sun, T in full shade, linear by overcast.
// C_T² scales with the ground-air delta AND absolute temperature (hotter
// air convects harder), so hot clear days degrade seeing far more than
// mild ones. Night convection drops ~100x.
private _Tg = _temp + 15 * (1 - _overcast);
private _C_T2 = 1e-3 * ((_Tg - _temp) / 10) * ((_temp max 1) / 15);
if (!_daytime) then { _C_T2 = _C_T2 * 0.01; };  // night: convection stops

// Refractivity of air N ≈ 79e-6 · P/T; Cn² = C_T² · (79e-6 · P / T²)²
private _T_K = _temp + 273.15;
private _Cn2 = _C_T2 * ((79e-6 * 1013) / (_T_K ^ 2)) ^ 2;
_Cn2 = _Cn2 max 0;

// ─── Mechanical turbulence (shear-driven, dominates in storms) ─────────────
_Cn2 = _Cn2 + 1e-14 * (_turbulence max 0);

// ─── Humidity (water vapour refractive-index fluctuation) ──────────────────
if (_humidity > 50) then {
    _Cn2 = _Cn2 * (1 + (_humidity - 50) * 0.002);
};

// ─── Map Cn² to seeing index (log scale over the Cn² decade range) ─────────
// Cn² ~1e-17 (excellent night) → 0.1; Cn² ~1e-12 (storm/hot afternoon) → 1.0.
// SQF log is BASE-10 (log 100 = 2), so log10(Cn²) is `log _Cn2` directly.
// The earlier /2.302585 conversion was written assuming natural log and
// inverted the scale — a cool rainy day (Cn² 2.5e-15) saturated seeing to
// 1.0 (verified via sqfvm: correct value is 0.53).
private _logCn2 = log (_Cn2 max 1e-17);
private _seeing = (0.1 + 0.9 * ((_logCn2 + 17) / 5)) min 1;
_seeing = _seeing max 0.1 min 1.0;

missionNamespace setVariable [QGVAR(atmosphericSeeing), _seeing];

_seeing
