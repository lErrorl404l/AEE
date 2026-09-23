#include "..\..\script_component.hpp"

/*
Author: AEE
Description: Determines the precipitation phase (rain, sleet, snow, freezing
rain) from the WET-BULB temperature and surface temperature, and derives a
snowfall rate from the engine rain rate.

Phase physics: in dry air the wet-bulb sits several degrees below the
dry-bulb, so precipitation can fall as snow well above 0 °C dry-bulb when
the air is dry (evaporative cooling).  The wet-bulb 0 °C line is the
accepted phase boundary:
  Twb <= 0        → snow
  0 < Twb <= 0.5  → sleet (mixed phase)
  Twb > 0.5       → rain
Freezing rain: warm air aloft (wet-bulb > 0) falling onto a frozen surface.

Arguments: None
Return Value: STRING: precipitation phase ("rain", "sleet", "snow", "freezing_rain")
Sets: aee_core_precipitationPhase, aee_core_snowfallRate,
      aee_core_orographicFactor, aee_core_hailActive (hail gate, #151)
Example: [] call aee_atmos_fnc_calculatePrecipitationPhase
Public: No
*/

private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _RH = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _surfaceT = missionNamespace getVariable [QEGVAR(core,surfaceTemperature), _T];
private _rainRate = rain;

// ─── Wet-bulb temperature (Stull 2011, same formula as fnc_calculateWBGT) ─
// SQF atan returns degrees; Stull 2011 needs radians, so each term is
// converted with the rad operator.
private _sqrtRHP1 = sqrt (_RH + 8.313659);
private _Tw = _T * (atan (0.151977 * _sqrtRHP1)) * 0.0174532925
    + (atan (_T + _RH)) * 0.0174532925
    - (atan (_RH - 1.676331)) * 0.0174532925
    + 0.00391838 * (_RH ^ 1.5) * (atan (0.023101 * _RH)) * 0.0174532925
    - 4.686035;

// Freezing rain: warm air aloft (wet-bulb > 0), frozen surface
private _phase = switch (true) do {
    case ((_Tw > 0) && (_surfaceT < 0)): { "freezing_rain" };
    case (_Tw > 0.5):                    { "rain" };
    case (_Tw > 0):                      { "sleet" };
    default                              { "snow" };
};

private _snowfallRate = if (_phase in ["snow", "sleet", "freezing_rain"]) then { _rainRate min 1 } else { 0 };

// ─── Hail gate (issue #151) ───────────────────────────────────────────────
// Hail needs a strong updraft and a wet-bulb below freezing in the layer
// where the stone grows.  The updraft indicator is the CAPE proxy that
// fnc_calculateCloudDevelopment publishes (lapse rate above the dry
// adiabat); it is computed later in the same tick, so this reads the
// previous tick's value.  The convective state changes over minutes, so a
// 5 s lag is immaterial.
//
// The growth layer is taken at 3 km, the mid-range of the 2-4 km hail
// growth zone (Browning 1977).  The wet-bulb aloft is the surface wet-bulb
// minus the standard lapse over that depth (0.0065 C/m, the lapse
// fnc_updateTemperature applies).  Rain must be falling: hail comes from a
// convective storm, so the gate cannot fire in clear air.
private _capeProxy = missionNamespace getVariable [QGVAR(capeProxy), 0];
if !(_capeProxy isEqualType 0) then { _capeProxy = 0; };
private _hailGrowthM = 3000;
private _lapseCPerM = 0.0065;
private _twAloft = _Tw - (_lapseCPerM * _hailGrowthM);
private _hailActive = (_capeProxy > 0) && (_twAloft < 0) && (_rainRate > 0.05);

// ─── Orographic enhancement ──────────────────────────────────────────────
// Air forced up a slope condenses more, so a ridge receives more
// precipitation than the flat land around it.  The model is the published
// upslope form (Smith 1979); fnc_calculateOrographicPrecipitation holds it.
// The setting gates the effect, so a mission can turn it off.
private _orographic = 1;
if (missionNamespace getVariable [QEGVAR(core,precipOrographicEnabled), true]) then {
    private _unit = call CBA_fnc_currentUnit;
    if (!isNil "_unit" && {!isNull _unit}) then {
        _orographic = [getPosASL _unit] call FUNC(calculateOrographicPrecipitation);
    };
};

missionNamespace setVariable [QEGVAR(core,precipitationPhase), _phase];
missionNamespace setVariable [QEGVAR(core,snowfallRate), _snowfallRate * _orographic];
missionNamespace setVariable [QEGVAR(core,orographicFactor), _orographic];
missionNamespace setVariable [QEGVAR(core,hailActive), _hailActive];

_phase
