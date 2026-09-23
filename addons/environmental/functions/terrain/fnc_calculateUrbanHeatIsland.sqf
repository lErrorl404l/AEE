#include "..\..\script_component.hpp"

/*
Urban heat island intensity (issue: the urbanHeatIsland setting).

A city is warmer than its countryside. The relation is published, and this
computes it rather than scaling a curve.

SOURCE (primary): Oke, T.R. (1973) "City size and the urban heat island",
Atmospheric Environment 7(8) 769-779, DOI 10.1016/0002-6981(73)90140-6.
The average-survey regression (Fig. 2, mean wind 2.3 m/s, cloudless):

    dT = 1.93 * log10(P) - 4.76,  r2 = 0.97,  S = +/- 0.3 C

and the maximum, cloudless relation (Eq. 5, North America):

    dT_max = 2.96 * log10(P) - 6.41,  r2 = 0.96,  S = +/- 0.7 C

P is population in inhabitants, dT is the urban-rural temperature
difference in degrees Celsius, and the logarithm is base 10 (the paper's
figure axes are powers of ten).

REPRESENTING POPULATION.  Arma has no population data, so the built-up
density the terrain scan already computes stands in for it: the structure
vote is the fraction of sampled objects that are buildings.  The mapping
is stated here rather than implied, and it is monotonic in the way the
relation needs: a village and a capital city must differ by the log of
their populations.

VALIDITY, as the paper states it:
  - cloudless skies (N = 0). The effect is a clear-sky phenomenon, so
    cloud cover suppresses it linearly toward zero.
  - the paper reports no data for wind above 5 m/s, so wind above that
    value is carried as a suppression rather than extrapolated.
  - the relation is for nocturnal minima; the effect is strongest after
    sunset and weakest near solar noon.

Arguments:
  0: position (ARRAY, PositionASL, default [])
  1: structure density 0..1 (NUMBER, default 0)

Returns the urban heat island temperature addition in degrees Celsius
(zero or positive).  The caller scales it by the user setting.
*/

params [["_pos", [], [[]]], ["_structure", 0, [0]]];

if (count _pos < 2) exitWith { 0 };
if (_structure <= 0) exitWith { 0 };

// ─── Built-up density -> an effective population ─────────────────────────
// The structure vote is the fraction of sampled objects that are
// buildings.  A dense city core reads near 1 and open ground near 0.
// The band is anchored on two known cases: a sparse settlement (about
// 1e3 inhabitants) and a large city (about 1e6), so the logarithm spans
// the range the paper's regression was fitted over.
private _structureClamped = _structure max 0 min 1;
private _population = 10 ^ (3 + _structureClamped * 3);

// ─── The published relation ──────────────────────────────────────────────
private _delta = 1.93 * (log _population / log 10) - 4.76;

// A settlement smaller than the regression's range would give a negative
// difference, which is not physical: the countryside then simply offers
// no island.  Clamp at zero rather than reporting a cold city.
if (_delta < 0) then { _delta = 0; };

// ─── Validity limits ─────────────────────────────────────────────────────
// Cloudless skies: the effect is a clear-sky phenomenon, so cloud cover
// suppresses it.  The paper's relations hold at N = 0.
private _overcast = overcast;
if !(_overcast isEqualType 0) then { _overcast = 0; };
_delta = _delta * (1 - (_overcast max 0 min 1));

// Wind: the paper reports no data above 5 m/s, so a stronger wind is
// carried as a suppression toward zero rather than extrapolated past the
// fitted range.
private _windStr = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];
if !(_windStr isEqualType 0) then { _windStr = 0; };
if (_windStr > 5) then {
    // Ventilation removes the accumulated warmth; the falloff is linear
    // from the documented limit to calm-equivalent at three times it.
    _delta = _delta * (1 - (((_windStr - 5) / 10) min 1));
};

// Nocturnal: the island is a night phenomenon, strongest just before
// dawn and absent near solar noon.
private _solar = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), 0];
if !(_solar isEqualType 0) then { _solar = 0; };
_delta = _delta * (1 - (_solar max 0 min 1) * 0.6);

_delta
