#include "..\..\script_component.hpp"
/*
Sound propagation index: how far a sound carries now, relative to the
reference conditions, from ISO 9613 (1.0 = the reference).

The index is d_now / d_ref, the distances at which the ISO 9613-2 path loss
(aee_lib_fnc_soundPathLoss: divergence, ISO 9613-1 air absorption at
500 Hz, porous-ground attenuation, dense foliage) uses up the same level
budget.  The reference is the standard's own: 10 C, 70 % RH, 101.325 kPa
(ISO 9613-2 Table 2), open porous ground (G = 1), no foliage, 1.5 m source
and receiver, a quiet-rural 30 dB(A) floor, and the 400 m engine hearing
baseline the AI uses.  Now:
  - the air absorption from the temperature, humidity and pressure;
  - the ground at the listener: hard (G = 0) for water, paving, rock and
    ice, porous (G = 1) otherwise and over snow (ISO 9613-2 7.3.1);
  - the foliage: the seasonal foliage density is taken as the fraction of
    the path through dense foliage;
  - the ambient floor (aee_weather_currentAmbientNoise, published first):
    every dB it rises above the reference removes a dB of budget.
ISO 9613-2 assumes downwind / moderate-inversion propagation; the upwind
refractive shadow is not modelled, so wind and the lapse rate do not enter.
Rain does not attenuate sound measurably in air; it raises the ambient
floor, which is where it enters.

Arguments: 0: listener position ASL (optional)
Stores GVAR(currentSoundPropagation), GVAR(soundAlpha500) (dB/m).
*/
params [["_posASL", [], [[]]]];

private _t = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_t isEqualType 0) then { _t = 15; };
private _rh = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
if !(_rh isEqualType 0) then { _rh = 50; };
private _p = missionNamespace getVariable [QEGVAR(core,currentPressure), 1013.25];
if !(_p isEqualType 0) then { _p = 1013.25; };
private _alpha = [500, _t, _rh, _p] call EFUNC(lib,atmosphericAbsorption);
private _alphaRef = [500, 10, 70, 1013.25] call EFUNC(lib,atmosphericAbsorption);

private _g = 1;
if ((count _posASL) >= 2) then {
    private _snow = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];
    if !(_snow isEqualType 0) then { _snow = 0; };
    if (_snow <= 0.01) then {
        if (surfaceIsWater _posASL) then { _g = 0; } else {
            private _surface = toLower (surfaceType _posASL);
            {
                if ((_surface find _x) >= 0) exitWith { _g = 0; };
            } forEach ["asphalt", "tarmac", "concrete", "road", "runway", "pavement", "cobble", "rock", "stony", "ice", "glacier"];
        };
    };
};
private _foliage = missionNamespace getVariable [QGVAR(currentFoliageDensity), 0];
if !(_foliage isEqualType 0) then { _foliage = 0; };
_foliage = (_foliage max 0) min 1;
private _ambient = missionNamespace getVariable [QGVAR(currentAmbientNoise), 30];
if !(_ambient isEqualType 0) then { _ambient = 30; };

private _dRef = 400;
private _budget = ([_dRef, 1.5, 1.5, _alphaRef, 1, 0] call EFUNC(lib,soundPathLoss)) - ((_ambient max 30) - 30);

// Bisection on the monotone path loss for the distance that spends the budget.
private _lo = 1;
private _hi = 50000;
for "_i" from 1 to 40 do {
    private _mid = sqrt (_lo * _hi);
    private _loss = [_mid, 1.5, 1.5, _alpha, _g, _foliage * _mid] call EFUNC(lib,soundPathLoss);
    if (_loss > _budget) then { _hi = _mid; } else { _lo = _mid; };
};
private _index = ((sqrt (_lo * _hi)) / _dRef) * GVAR(SoundPropagationScale);
_index = (_index max 0.05) min 5;

missionNamespace setVariable [QGVAR(currentSoundPropagation), _index];
missionNamespace setVariable [QGVAR(soundAlpha500), _alpha];
_index
