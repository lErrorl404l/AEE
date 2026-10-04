#include "..\..\script_component.hpp"

/*
Milky Way band sampler, driven at 2 Hz by fnc_renderMilkyWay.

The band follows the galactic plane: the sampler walks MILKY_WAY_SAMPLES
points along galactic latitude 0 and projects each through
FUNC(galacticToHorizontal) with the current sidereal time and observer
latitude, so the band moves with the starfield.  The Draw3D worker
(fnc_drawMilkyWay) draws the result as line segments.

Surface brightness anchor: the published dark-sky value (21.8 mag/arcsec^2,
Crumey 2014).  MILKY_WAY_NELM_MIN derives from that contrast; the colour,
alpha, radius and sample count are render tunables and are UNSOURCED.

Debug hooks, set on missionNamespace:
  - aee_environmental_skyForce       Boolean, force the whole night sky on
  - aee_environmental_milkyWayForce  Boolean, force the Milky Way on
*/

private _skyForce = missionNamespace getVariable ["aee_environmental_skyForce", false];
if !(_skyForce isEqualType false) then { _skyForce = false; };
private _milkyWayForce = missionNamespace getVariable ["aee_environmental_milkyWayForce", false];
if !(_milkyWayForce isEqualType false) then { _milkyWayForce = false; };
private _settingOn = missionNamespace getVariable [QGVAR(dynamicMilkyWay), true];
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), 0];
if !(_sunElev isEqualType 0) then { _sunElev = 0; };
private _overcast = ([] call EFUNC(core,getSmoothedWeather)) select 1;
if !(_overcast isEqualType 0) then { _overcast = 0; };
private _nelm = missionNamespace getVariable [QGVAR(limitingMagnitude), 6.5];
if !(_nelm isEqualType 0) then { _nelm = 6.5; };

// Whether the band is drawn: the forces bypass the physical gates, the
// unforced path needs night, clear sky and a dark enough NELM.
private _active = _skyForce || _milkyWayForce;
if (!_active) then {
    _active = _settingOn && (_sunElev < 0) && (_overcast < 0.8) && (_nelm >= MILKY_WAY_NELM_MIN);
};

if (!_active) exitWith {
    missionNamespace setVariable [QGVAR(milkyWayActive), false];
    missionNamespace setVariable [QGVAR(milkyWaySamples), []];
    missionNamespace setVariable [QGVAR(milkyWaySampleCount), 0];
};

private _lstDeg = [date] call FUNC(siderealTime);
private _latDeg = ([] call EFUNC(core,getWorldLocation)) select 1;
if (_latDeg == 0) then { _latDeg = 40; };

private _samples = [];
for "_i" from 0 to (MILKY_WAY_SAMPLES - 1) do {
    private _lDeg = _i * 360 / MILKY_WAY_SAMPLES;
    _samples pushBack ([_lDeg, 0, _lstDeg, _latDeg] call FUNC(galacticToHorizontal));
};

missionNamespace setVariable [QGVAR(milkyWaySamples), _samples];
missionNamespace setVariable [QGVAR(milkyWayActive), true];
missionNamespace setVariable [QGVAR(milkyWaySampleCount), count _samples];
