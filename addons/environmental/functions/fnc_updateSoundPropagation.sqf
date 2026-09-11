#include "..\script_component.hpp"

/*
Sound propagation index (1.0 = baseline).

Factors that increase range (>1.0):
  • Temperature inversion (clear calm night) — sound refracts downward
  • Downwind propagation

Factors that decrease range (<1.0):
  • Rain — water droplets absorb high frequencies
  • Dense vegetation — foliage scatters and absorbs
  • Snow cover — porous surface absorbs

Stored in GVAR(currentSoundPropagation) for external query by
sound-intensity systems or ACE3 hearing-range modifiers.
*/

private _index = 1.0;
private _hour = dayTime;
private _windSpeed = vectorMagnitude wind;

// ─── Temperature inversion ──────────────────────────────────────────────
// Forms on clear, calm nights when the ground radiates heat away faster
// than the air above.  Sound waves refract toward the cooler surface,
// increasing ground-level range.
private _isNight  = (_hour < 6 || _hour > 20);
private _isCalm   = (_windSpeed < 4);
private _isClear  = (overcast < 0.4);

if (_isNight && _isCalm && _isClear) then {
    _index = _index + 0.6;   // strong inversion
} else {
    if (_isNight && _isCalm) then {
        _index = _index + 0.3;  // moderate (thin cloud cover still traps)
    };
};

// ─── Wind ― shear carries ──────────────────────────────────────────────
if (_windSpeed > 3) then {
    _index = _index + (_windSpeed * 0.04);  // +0.12 at 3 m/s, +0.4 at 10 m/s
};

// ─── Rain absorption ───────────────────────────────────────────────────
if (rain > 0) then {
    _index = _index - (rain * 0.5);
};

// ─── Vegetation absorption ─────────────────────────────────────────────
private _foliageDensity = missionNamespace getVariable [QGVAR(currentFoliageDensity), 0.5];
_index = _index - (_foliageDensity * 0.15);

// ─── Snow cover absorption ─────────────────────────────────────────────
private _groundState = missionNamespace getVariable [QGVAR(groundState), "Normal"];
if (_groundState == "Snow") then {
    _index = _index - 0.25;
};

_index = _index max 0.3 min 2.0;
missionNamespace setVariable [QGVAR(currentSoundPropagation), _index];
