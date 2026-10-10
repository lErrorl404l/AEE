#include "..\..\script_component.hpp"

/*
Dense-gas dispersion driver (issue #120).

Reads the environment state and the selected agent, calls the pure
dispersion kernels, and publishes the dense-gas state for consumers.  The
sibling of the neutral Gaussian plume (#105): the dense model supplies the
slumping velocity, the Richardson number, the entrainment and the
dense/neutral transition the plume model lacks.

The agent is a scenario selection (CBA setting aee_weather_denseGasAgent,
default "none") until a release event exists; the release geometry is the
cloud height and the pool diameter (their own settings).  With no agent
selected the driver returns at once.

The published state is
  [densityRatio, reducedGravity, frontalVelocity, richardson,
   entrainmentVelocity, denseActive, transitionConcentration, toxicTier,
   poolDepth, pooledConcentration, evaporationFlux]
stored in aee_weather_denseGasState.

Driven by EFUNC(core,updateEnvironment) under GVAR(environmentalEnabled).
*/

private _agent = missionNamespace getVariable [QGVAR(denseGasAgent), "none"];
if ((_agent == "") || (_agent == "none")) exitWith {};

private _props = [_agent] call FUNC(getGasProperties);
if ((count _props) == 0) exitWith {};

private _molarMass = _props select 0;
private _ratio = _props select 1;
private _boilingC = _props select 2;
private _vapourPa = _props select 3;
private _aegl2 = _props select 4;
private _aegl3 = _props select 5;
private _idlh = _props select 6;
private _tlv = _props select 7;

private _windSpd = vectorMagnitude (missionNamespace getVariable [QEGVAR(core,currentWind), [0, 0]]);
private _tempC = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _cloudHeight = missionNamespace getVariable [QGVAR(denseGasCloudHeight), 1];
private _poolDiameter = missionNamespace getVariable [QGVAR(denseGasPoolDiameter), 2];

// Slumping: reduced gravity, frontal velocity, Richardson number,
// entrainment velocity, the dense flag.
private _slump = [_ratio, _cloudHeight, _windSpd] call FUNC(calculateDenseGasSlumping);

// Dense/neutral transition: the concentration at which the cloud becomes
// passive (independent of C, so evaluated at C = 0).
private _mix = [0, _ratio] call FUNC(calculateGasMixtureDensity);
private _transition = _mix select 2;

// The toxic tier at the transition concentration: for a dense agent the
// hazardous band is at or below the dense/passive transition, so a
// hazardous cloud is always in the dense regime.
private _tier = [_transition, _aegl2, _aegl3, _idlh, _tlv] call FUNC(classifyToxicExposure);

// Pooling at the release origin: flat ground until a terrain sampler
// supplies the cell and neighbour heights, so the term is 0 here.
private _pool = [0, 0, _transition, 0.5] call FUNC(calculateDenseGasPooling);

// A liquefied agent (boiling point below the ambient temperature) holds a
// pool at its boiling point, where the vapour pressure is one atmosphere.
private _surfaceK = _tempC + 273.15;
private _poolVapourPa = _vapourPa;
if (_boilingC < _tempC) then {
    _surfaceK = _boilingC + 273.15;
    _poolVapourPa = 101325;
};
private _evap = [_windSpd, _poolDiameter, _molarMass, _poolVapourPa, _surfaceK] call FUNC(calculatePoolEvaporation);

private _state = [
    _ratio,
    _slump select 0,
    _slump select 1,
    _slump select 2,
    _slump select 3,
    _slump select 4,
    _transition,
    _tier,
    _pool select 0,
    _pool select 1,
    _evap
];

missionNamespace setVariable [QGVAR(denseGasState), _state];

_state
