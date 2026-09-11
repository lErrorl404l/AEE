#include "..\script_component.hpp"

/*
Atmospheric seeing / turbulence index (0.1–1.0) for extreme long-range optics.

Higher values = worse seeing (more shimmer, distortion).
Lower values = clearer air (better for observation >1000 m).

Seeing degrades from thermal mixing (sun-heated ground → rising thermals →
refractive-index shimmer) and, to a lesser extent, wind shear and humidity haze.
Night-time seeing is significantly better because thermal convection stops.

  • Hot clear day (T >25 °C, overcast <30 %): strong shimmer
  • Warm clear day (T >15 °C, overcast <50 %): moderate shimmer
  • Turbulence >0.3: additional wind-shear contribution
  • High humidity (>70 %): haze component
  • Night-time: multiply by 0.3 (virtually no thermal convection)

ponytail: empirical thermal-mixing model, not a full optical-propagation model.
Stored in QGVAR(atmosphericSeeing). Lower = better.
*/

// ─── Inputs ────────────────────────────────────────────────────────────────
private _turbulence = missionNamespace getVariable [QEGVAR(core,currentTurbulence), 0];
private _temp       = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _humidity   = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _overcast   = overcast;
private _daytime    = sunOrMoon == 1;

// ─── Base seeing (clear-air floor) ─────────────────────────────────────────
private _seeing = 0.2;

// ─── Thermal mixing (daytime only) ─────────────────────────────────────────
if (_daytime) then {
    if (_temp > 25 && _overcast < 0.3) then {
        _seeing = _seeing + 0.5; // strong shimmer
    } else {
        if (_temp > 15 && _overcast < 0.5) then {
            _seeing = _seeing + 0.2; // moderate shimmer
        };
    };
};

// ─── Wind shear contribution ───────────────────────────────────────────────
if (_turbulence > 0.3) then {
    _seeing = _seeing + (_turbulence * 0.3);
};

// ─── Humidity haze ─────────────────────────────────────────────────────────
if (_humidity > 70) then {
    _seeing = _seeing + ((_humidity - 70) * 0.005);
};

// ─── Night-time improvement ────────────────────────────────────────────────
if (!_daytime) then {
    _seeing = _seeing * 0.3;
};

// ─── Clamp ─────────────────────────────────────────────────────────────────
_seeing = _seeing max 0.1 min 1.0;

missionNamespace setVariable [QGVAR(atmosphericSeeing), _seeing];

_seeing
