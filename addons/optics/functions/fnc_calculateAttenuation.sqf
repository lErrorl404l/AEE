#include "..\script_component.hpp"

/*
Attenuation coefficients (0–1) for laser/IR and visible light transmission.

  1.0 = full transmission (clear air)
  0.1 = near-total attenuation

Divided into two bands:
  • Laser/IR (e.g. rangefinders, IR pointers, NVD illuminators)
  • Visible (human eye, white-light optics)

Each is degraded by rain, fog, airborne dust, and — for visible light —
heavy overcast.  The same environmental factors affect the two bands at
different strengths.

Stored in GVAR(currentLaserAttenuation) and GVAR(currentVisibleAttenuation).
*/

private _laserAtten  = 1.0;
private _visibleAtten = 1.0;

private _RH = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _fog = missionNamespace getVariable [QEGVAR(core,currentFogDensity), 0];

// ─── Rain ────────────────────────────────────────────────────────────────
private _rainS = ([] call FUNC(getSmoothedWeather)) select 0;
if (_rainS > 0) then {
    _laserAtten  = _laserAtten  - (_rainS * 0.3);
    _visibleAtten = _visibleAtten - (_rainS * 0.4);
};

// ─── Fog ─────────────────────────────────────────────────────────────────
if (_fog > 0) then {
    _laserAtten  = _laserAtten  - (_fog * 0.5);
    _visibleAtten = _visibleAtten - (_fog * 0.6);
};

// ─── Dust ────────────────────────────────────────────────────────────────
if (_groundState == "Dusty") then {
    _laserAtten  = _laserAtten  * 0.6;
    _visibleAtten = _visibleAtten * 0.5;
};

// ─── Heavy humidity (laser/IR only) ──────────────────────────────────────
if (!isNil "_RH" && _RH > 80) then {
    _laserAtten = _laserAtten * 0.9;
};

// ─── Heavy overcast (visible only) ───────────────────────────────────────
private _overcastS = ([] call FUNC(getSmoothedWeather)) select 1;
if (_overcastS > 0.8) then {
    _visibleAtten = _visibleAtten * 0.85;
};

_laserAtten  = _laserAtten  max 0.1 min 1.0;
_visibleAtten = _visibleAtten max 0.1 min 1.0;

missionNamespace setVariable [QGVAR(currentLaserAttenuation),  _laserAtten];
missionNamespace setVariable [QGVAR(currentVisibleAttenuation), _visibleAtten];
