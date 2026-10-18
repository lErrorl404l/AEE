#include "..\..\script_component.hpp"

/*
Boundary-layer turbulence at the observer: the eddy dissipation rate (EDR,
the ICAO Annex 3 metric) from fnc_turbulenceDissipation (Monin-Obukhov
surface layer, convective mixed-layer scaling), with:
  - the local wind at 10 m (FUNC(getLocalWind), the spatial field);
  - the roughness length z0 of the surface underfoot
    (aee_lib_fnc_roughnessLength, the revised Davenport classification);
  - the surface-air temperature difference from the ground solve
    (aee_core_surfaceTemperature), which sets the heat flux and stability;
  - the convective layer top: the parcel LCL (aee_atmos_lclHeight), the
    cloud base that caps the daytime mixed layer.
Classes (ICAO, medium aircraft, peak EDR): NIL < 0.1, LIGHT 0.1-0.2,
MODERATE 0.2-0.45, SEVERE >= 0.45.  aee_core_currentTurbulence is EDR over
the severe threshold, 0..1, for the consumers that take a fraction.
Sets QEGVAR(core,currentTurbulence), GVAR(edrValue), GVAR(turbulenceClass).
*/

private _player = call CBA_fnc_currentUnit;
private _posASL = [worldSize / 2, worldSize / 2, 0];
private _agl = 2;
if (!isNil "_player" && {!isNull _player}) then {
    _posASL = getPosASL _player;
    _agl = ((_posASL select 2) - (getTerrainHeightASL _posASL)) max 2;
};
private _wind10 = vectorMagnitude ([_posASL, 10] call FUNC(getLocalWind));

private _z0 = [_posASL] call EFUNC(lib,roughnessLength);

private _tAir = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_tAir isEqualType 0) then { _tAir = 15; };
private _tSurf = missionNamespace getVariable [QEGVAR(core,surfaceTemperature), _tAir];
if !(_tSurf isEqualType 0) then { _tSurf = _tAir; };
private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), AERO_ISA_SEA_LEVEL_DENSITY];
if !(_rho isEqualType 0) then { _rho = AERO_ISA_SEA_LEVEL_DENSITY; };
private _zi = missionNamespace getVariable [QGVAR(lclHeight), 1000];
if !(_zi isEqualType 0) then { _zi = 1000; };
private _lat = ([] call EFUNC(lib,getWorldLocation)) param [0, 45];

private _pHpa = missionNamespace getVariable [QEGVAR(core,currentPressure), 1013.25];
if !(_pHpa isEqualType 0) then { _pHpa = 1013.25; };
private _diss = [_wind10, _agl, _z0, _tSurf - _tAir, _tAir, _rho, _lat, _zi, _pHpa] call FUNC(turbulenceDissipation);
// Optical turbulence along a sight line 2 m above the ground.
private _cn2 = ([_wind10, 2, _z0, _tSurf - _tAir, _tAir, _rho, _lat, _zi, _pHpa] call FUNC(turbulenceDissipation)) select 4;
private _edr = _diss select 1;

private _turbulenceClass = switch (true) do {
    case (_edr >= 0.45): { "SEVERE" };
    case (_edr >= 0.2):  { "MODERATE" };
    case (_edr >= 0.1):  { "LIGHT" };
    default              { "NIL" };
};
private _turbulence = (_edr / 0.45) min 1;

missionNamespace setVariable [QEGVAR(core,currentTurbulence), _turbulence];
missionNamespace setVariable [QGVAR(edrValue), _edr];
missionNamespace setVariable [QGVAR(turbulenceClass), _turbulenceClass];
missionNamespace setVariable [QEGVAR(core,opticalCn2), _cn2];
