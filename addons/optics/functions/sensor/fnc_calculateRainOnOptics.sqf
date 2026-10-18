#include "..\..\script_component.hpp"

/*
Rain drops on an exposed lens (0-1, the wetted fraction of the glass).

The objective faces the horizon, so it collects WIND-DRIVEN rain: the flux on
a vertical surface is (2/9) v R^(8/9) mm/h for a wind v (m/s) against it
and a rain rate R (mm/h) (the Lacy free-field relation of ISO 15927-3:2009,
2/9 s/m being the inverse terminal speed of a typical drop).  Drops arrive
with the Marshall-Palmer median volume diameter D0 = 0.89 R^0.21 mm
(Marshall & Palmer 1948) and sit as hemispherical beads (a hydrophobic
lens coating), radius a = (D0^3 / 4)^1/3, each holding (2/3) a of water
per unit of wetted area, so the wetted fraction grows as
  dC/dt = (1 - C) q / ((2/3) a),   q the vertical flux in m/s.
Out of the rain the film clears at the rainDecayRate setting, a DISPLAY rate.

Stored in QGVAR(rainOnOptics) for consumption by visual overlay systems.
*/

params [];

if (!(missionNamespace getVariable [QEGVAR(core,opticsEnabled), true])) exitWith {
    missionNamespace setVariable [QGVAR(rainOnOptics), 0];
    0
};

private _rainRate = rain;
if !(_rainRate isEqualType 0) then { _rainRate = 0; };

// The engine `rain` command is a 0..1 level, not a rate.  Convert it to mm/h
// with the mapping the optics module owns: 1.0 engine rain = 25 mm/h, heavy
// rain (fnc_calculatePrecipitationVisibility.sqf).
private _rainMMH = _rainRate * ENGINE_RAIN_FULL_MMH;

private _droplets = missionNamespace getVariable [QGVAR(rainOnOptics), 0];
if !(_droplets isEqualType 0) then { _droplets = 0; };
private _dt = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
if !(_dt isEqualType 0) then { _dt = 5; };
private _decayRate = (missionNamespace getVariable [QGVAR(rainDecayRate), 0.02]) * (_dt / 5);
if (_rainMMH > 0.1) then {
    private _wind = vectorMagnitude (missionNamespace getVariable [QEGVAR(core,currentWind), [0, 0]]);
    private _qMMh = (2 / 9) * (_wind max 0.5) * (_rainMMH ^ (8 / 9));
    private _q = _qMMh / 1000 / 3600;
    private _d0 = 0.89e-3 * (_rainMMH ^ 0.21);
    private _a = ((_d0 ^ 3) / 4) ^ (1 / 3);
    _droplets = 1 - ((1 - _droplets) * exp (-(_q * _dt) / ((2 / 3) * _a)));
} else {
    _droplets = (_droplets - _decayRate) max 0;
};
missionNamespace setVariable [QGVAR(rainOnOptics), _droplets];
_droplets
