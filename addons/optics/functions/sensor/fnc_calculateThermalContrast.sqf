#include "..\..\script_component.hpp"

/*
Thermal contrast coefficient (0–1) for FLIR/thermal imaging effectiveness,
plus a NETD-based sensor noise floor.

  1.0 = perfect contrast (crisp thermal signature)
  0.0 = no usable contrast

Physics basis:
  - Contrast comes from the object–background temperature gap (delta-T).
    An 8 °C vehicle-background gap gives full contrast; smaller gaps give
    proportionally less.  This is the real FLIR figure of merit: a sensor
    resolves a target when its temperature differs from the background by
    more than the sensor's own noise floor.  The span is wider than the
    old 5 °C because the engine ALREADY renders the native thermal image
    with its own gain; this stage only adds the environmental degradation
    the engine does not model.  A smaller span double-amplifies to white.
  - The scene average uses VEHICLES only.  Infantry run at a near-constant
    ~33 °C body temperature and would skew the average up, washing the
    whole frame to full white-hot.  The engine renders infantry natively.
    Object temperatures come from EGVAR(core,objectTemperatures), the
    per-object surface temperatures computed by
    aee_thermal_fnc_calculateObjectTemperature.  The background is
    EGVAR(core,avgGroundTemp).
  - Rain absorbs LWIR, fog scatters it, and water vapour (humidity)
    absorbs it.  Each multiplies contrast down.
  - Heat (>35 °C) flattens the thermal gradient: everything approaches
    air temperature, so the object–background gap narrows.
  - Cold (<5 °C) widens the gap: objects stay warm while the background
    cools, boosting contrast.
  - NETD (Noise Equivalent Temperature Difference) is the temperature
    change that produces a signal equal to the sensor's own noise.
    Modern uncooled microbolometers run ~0.05 °C.  Atmospheric path
    noise grows with range squared (more air means more scintillation
    and absorption), and humidity adds water-vapour noise.

Stored in GVAR(currentThermalContrast) (0–1) and
GVAR(currentThermalNoise) (0–1) for external query by sensor
simulations, FLIR overlay systems, or AI target-acquisition modifiers.
*/

// ─── Shared inputs ────────────────────────────────────────────────────────
private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_T isEqualType 0) then { _T = 15; };

private _fog = missionNamespace getVariable [QEGVAR(core,currentFogDensity), 0];
if !(_fog isEqualType 0) then { _fog = 0; };

// currentHumidity is 0..100 percent, not a fraction.  Normalise to 0..1.
private _RH = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
if !(_RH isEqualType 0) then { _RH = 50; };
private _humidity = (_RH / 100) max 0 min 1;

// ─── Object temperatures ──────────────────────────────────────────────────
// Average the VEHICLE surface temperatures only.  Infantry run at a near-
// constant ~33 C body temperature and would skew the scene average up,
// inflating delta-T and washing the whole frame to full white-hot.  The
// engine renders per-object thermal natively; this contrast is the display
// gain stage.  Vehicles dominate the scene's usable temperature spread.
// An empty list (no vehicles, or a dedicated server) falls back to air
// temperature so the scene still has a background to contrast against.
private _objectTemps = missionNamespace getVariable [QEGVAR(core,objectTemperatures), []];
private _avgVehicleTemp = _T;
if (_objectTemps isEqualType [] && {count _objectTemps > 0}) then {
    private _vehSum = 0;
    private _vehCount = 0;
    {
        if (_x isEqualType [] && {count _x >= 2}) then {
            private _obj = _x select 0;
            // Type-guard before isKindOf: a nil or non-object entry would
            // raise "Type Object, expected ..." every tick.  Deleted
            // (null) objects are skipped too.
            if (_obj isEqualType objNull && {!isNull _obj}
                && {!(_obj isKindOf "Man")}) then {
                private _temp = _x select 1;
                if (_temp isEqualType 0) then {
                    _vehSum = _vehSum + _temp;
                    _vehCount = _vehCount + 1;
                };
            };
        };
    } forEach _objectTemps;
    if (_vehCount > 0) then { _avgVehicleTemp = _vehSum / _vehCount; };
};

private _groundTemp = missionNamespace getVariable [QEGVAR(core,avgGroundTemp), _T];
if !(_groundTemp isEqualType 0) then { _groundTemp = _T; };

// ─── Base contrast from delta-T ───────────────────────────────────────────
// 8 °C vehicle-background gap = full contrast.  This is the FLIR figure
// of merit: contrast is proportional to the resolved temperature gap.
// Wider span than the old 5 °C because the engine ALREADY renders the
// native thermal image with its own gain; this stage only adds the
// environmental degradation the engine does not model.  A smaller span
// here would double-amp the image to pure white.
private _deltaT = abs (_avgVehicleTemp - _groundTemp);
private _contrast = (_deltaT / 8) min 1.0;

// ─── Atmospheric attenuation ──────────────────────────────────────────────
// Rain absorbs LWIR, fog scatters it, water vapour absorbs it.
_contrast = _contrast * (1 - rain * 0.4);
_contrast = _contrast * (1 - _fog * 0.6);
_contrast = _contrast * (1 - _humidity * 0.3);

// ─── Extreme heat — gradient flattens ────────────────────────────────────
if (_T > 35) then {
    _contrast = _contrast - ((_T - 35) / 10) * 0.7; // linear to 0.3 at 45 °C
};

// ─── Cold boost — widened thermal gap ────────────────────────────────────
if (_T < 5) then {
    _contrast = (_contrast * 1.2) min 1.0;
};

_contrast = _contrast max 0 min 1;

// ─── NETD-based noise floor ───────────────────────────────────────────────
// NETD 0.05 °C for a modern uncooled microbolometer.  Noise grows with
// range squared: the atmospheric path adds scintillation and absorption
// noise.  Range is the sensor's working range, proxied by the engine
// view distance; a dedicated server has no player, so fall back to
// 1000 m.
private _range = viewDistance;
if !(_range isEqualType 0) then { _range = 1000; };
_range = _range max 100 min 5000;

private _netd = 0.05;
private _noise = _netd * ((_range / 1000) ^ 2);
_noise = _noise * (1 + _humidity * 0.5);
_noise = _noise max 0 min 1;

missionNamespace setVariable [QGVAR(currentThermalContrast), _contrast];
missionNamespace setVariable [QGVAR(currentThermalNoise), _noise];
