#include "..\..\script_component.hpp"

/*
Ground frost detection on terrain surfaces.

Frost forms on a clear, calm night when the surface cools below 0 C
and the air is near saturation.  Uses the Magnus dew-point formula
(Alduchov & Eskridge 1996):

  g  = ln(RH/100) + (17.62 x T) / (243.12 + T)
  Td = (243.12 x g) / (17.62 - g)

Conditions for frost:
  Surface temperature <= 0 C
    (solved by the ground node stack, published per 5 m cell; no frost
    verdict is given for a cell with no solved value)
  Dew-point depression < 2 C   (air near saturation)
  Overcast < 0.3              (clear sky for radiative cooling)
  Wind < 5 m/s                (light wind, strong wind mixes the air)

Intensity (0 to 1):
  (0 - surfaceTemp) x (1 - depression/5), clamped to 0 to 1.

Stores:
  QGVAR(groundFrostIntensity) float, 0 to 1
  QGVAR(groundFrostPresent)   bool
Returns QGVAR(groundFrostIntensity)

Arguments:
  0: ARRAY - the position to read the solved cell for.  Empty means the
     current unit's position.  With no position and no unit (a dedicated
     server) no cell resolves, so no frost verdict is given.
*/

params [["_pos2D", [], [[]]]];

if (!(missionNamespace getVariable [QGVAR(groundFrostEnabled), true])) exitWith {
    missionNamespace setVariable [QGVAR(groundFrostIntensity), 0];
    missionNamespace setVariable [QGVAR(groundFrostPresent), false];
    0
};

// Read environment
private _temp     = missionNamespace getVariable [QEGVAR(core,currentTemperature), 20];
private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _overcast = missionNamespace getVariable [QEGVAR(core,overcast), 0];
private _wind     = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];

// Dew point (Magnus, Alduchov & Eskridge 1996)
private _gamma      = ln (_humidity / 100) + (17.62 * _temp) / (243.12 + _temp);
private _dewPoint   = (243.12 * _gamma) / (17.62 - _gamma);
private _depression = _temp - _dewPoint;

// Surface temperature. The node stack solves it from the full energy
// balance (issue #198, fnc_calculateGroundNodeStack) and publishes it per
// 5 m cell.  Issue #11 asked for the old T_air - 2 C night heuristic to be
// replaced, and it is now gone rather than kept as a fallback: a fixed
// offset is a published cooling law in neither direction, because grass
// minima run several kelvin below screen air on a clear night and the
// offset depends on the sky, the wind and the surface.  A cell the stack has
// not reached carries no solved surface temperature, so this kernel gives no
// frost verdict for it instead of inventing one.
private _unit = call CBA_fnc_currentUnit;
private _surfState = missionNamespace getVariable [QEGVAR(core,groundSurfaceTemp), -1];
if (_surfState isEqualType 0) then { _surfState = createHashMap; };
// The caller's position wins: the core tick runs on a dedicated server,
// where there is no local unit, and it passes the position it already has.
private _readPos = if (_pos2D isEqualType [] && {_pos2D isNotEqualTo []}) then { _pos2D } else { [] };
if (_readPos isEqualTo [] && {!isNil "_unit"} && {!isNull _unit}) then {
    _readPos = getPos _unit;
};
private _stackKey = "";
if (_readPos isNotEqualTo [] && {_surfState isEqualType createHashMap}) then {
    _stackKey = format ["%1_%2_%3", floor ((_readPos select 0) / 5), floor ((_readPos select 1) / 5), "ground"];
};
if (_stackKey == "" || {!(_stackKey in _surfState)}) exitWith {
    missionNamespace setVariable [QGVAR(groundFrostIntensity), 0];
    missionNamespace setVariable [QGVAR(groundFrostPresent), false];
    0
};
private _surfaceTemp = _surfState get _stackKey;

// Frost conditions
private _intensity = 0;
if (_surfaceTemp <= 0 && _depression < 2 && _overcast < 0.3 && _wind < 5) then {
    _intensity = (0 - _surfaceTemp) * (1 - _depression / 5);
    _intensity = _intensity max 0 min 1;
};

missionNamespace setVariable [QGVAR(groundFrostIntensity), _intensity];
missionNamespace setVariable [QGVAR(groundFrostPresent), _intensity > 0];

_intensity
