#include "..\script_component.hpp"

/*
Heat haze / mirage intensity (0.0–1.0).

Requires sufficient surface heating to create a thermal gradient
strong enough for visible refractive distortion.  Surface temperature
is estimated from air temperature plus solar loading on
sun-exposed arid/reflective surfaces (desert, asphalt, rock).

Conditions:
  • Estimated surface temp >35 °C
  • Arid biome (BWh, BWk, BSh, BSk) OR ground state is Dusty
  • Solar elevation >15° (true daytime)

Overcast proportionally reduces the effect since cloud cover
reduces direct insolation.

Stored in QGVAR(mirageIntensity) for consumption by visual-effect
and thermal-imaging systems.
*/

params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith { 0 };  // no unit on dedicated server

// ─── Inputs ────────────────────────────────────────────────────────────
private _temp        = EGVAR(core,currentTemperature);
private _overcast    = overcast;
private _biome       = missionNamespace getVariable [QEGVAR(core,biome), ""];
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
// Sun elevation from dayTime (Arma has no getSunPosition command);
// sine model, peak at noon, horizon at 06:00 / 18:00.
private _sunElev = (sin (((dayTime / 24) - 0.25) * 360) * 90) max 0;

if (isNil "_temp") exitWith {
    missionNamespace setVariable [QGVAR(mirageIntensity), 0];
    0
};

// ─── Surface temperature estimate ──────────────────────────────────────
// Solar loading: +10 °C on bare/reflective surfaces in clear daytime
private _surfaceType = toLower (surfaceType (getPos _unit));
private _isAridSurf  = _surfaceType in [
    "#gdtbare", "#gdtconcrete", "#gdtdesert", "#gdtrocky",
    "#gdtsundesert", "#gdtstony", "#gdtasphalt"
];

private _solarLoading = 0;
if (sunOrMoon > 0 && _isAridSurf && _overcast < 0.3) then {
    _solarLoading = 10;
};

private _surfaceTemp = _temp + _solarLoading;

// ─── Eligibility ──────────────────────────────────────────────────────
private _onsetTemp   = missionNamespace getVariable [QGVAR(mirageOnsetTemp), 35];
private _minSunElev  = missionNamespace getVariable [QGVAR(mirageMinSunElev), 15];
private _aridBiome   = _biome in ["BWh", "BWk", "BSh", "BSk"];
private _dustyGround = _groundState == "Dusty";
private _hotEnough   = _surfaceTemp > _onsetTemp;

if (!_hotEnough || (!(_aridBiome || _dustyGround)) || (_sunElev <= _minSunElev)) exitWith {
    missionNamespace setVariable [QGVAR(mirageIntensity), 0];
    0
};

// ─── Intensity ─────────────────────────────────────────────────────────
private _intensity = ((_surfaceTemp - _onsetTemp) / 30) min 1.0;

// Overcast reduction — cloud cover reduces direct insolation
_intensity = _intensity * (1 - _overcast);

// Floor at zero, cap at 1
_intensity = _intensity max 0 min 1;

// ─── Store ─────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(mirageIntensity), _intensity];

_intensity
