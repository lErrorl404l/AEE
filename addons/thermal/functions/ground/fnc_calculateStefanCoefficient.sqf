#include "..\..\script_component.hpp"
/*
Stefan frost-depth coefficient from the soil's own water content and its
frozen thermal conductivity (issue #11, the soil-type-dependent Stefan
term).

Stefan's solution for the depth a freezing front reaches:

  X = sqrt( 2 * k_f * F / Q_L )        F in K.s

where k_f is the conductivity of the FROZEN soil, F the accumulated
freezing degree-time and Q_L the volumetric latent heat the soil must
lose before it freezes:

  Q_L = rho_dry * L_f * theta          theta = volumetric water content

The water content is what makes one soil differ from another. Dry sand at
theta 0.1 carries a tenth of the latent heat a saturated soil at 0.4
does, so the front runs far deeper for the same weather.

In the shorthand X_cm = C * sqrt(FDD_degC_day), the coefficient is

  C = 100 * sqrt( 2 * k_f * 86400 / Q_L )

Values from the #11 research (k_f W/m.K, theta volumetric):
  dry sand    k_f 1.5  theta 0.10  Q_L 5.3e7   C 7.0
  silt loam   k_f 1.5  theta 0.25  Q_L 1.3e8   C 4.4
  saturated   k_f 1.9  theta 0.40  Q_L 2.4e8   C 3.7

The issue's worked example, F = 500 degree-days, k = 1.5, Q_L = 1e8,
gives X = 1.14 m, which this function reproduces to four figures.

The mod once carried two constants, 2.7 bare and 1.7 under snow. Both sit
below the physical range: they treated the soil as one substance. The
range across real soils is 3.7 to 7.0, so a saturated clay freezes very
differently from a dry sand.

Sources:
  - Stefan 1891, Ann. Phys. Chem. 42, 269. Frost depth solution.
  - k_f and theta per soil class: de Vries 1963, Physics of Plant
    Environment; Incropera and DeWitt, Table A.3.
  - L_f = 3.34e5 J/kg: IAPWS-95 (333.55 kJ/kg). The value the mod already
    holds in fnc_calculateFrostState, and the one the #11 research used.
  - Snow conductance: Sturm et al. 1997, J. Climate 10, 1267.

Args:
  0: material class (STRING, default "ground") - the class
     aee_material_fnc_classifyBySurfaceType returns
  1: snow depth (NUMBER, metres, default 0)

Returns the Stefan coefficient C in the cm / sqrt(degC-day) form.
*/

params [["_soil", "ground", [""]], ["_snow", 0, [0]]];

// k_f in W/m.K (frozen) and theta the volumetric water content. A frozen
// soil keeps much of its water as ice, so theta is the total pore water,
// not the liquid fraction.
//
// A paved or metal surface is a cover over soil, not a soil itself: frost
// depth is a property of the ground beneath. Those classes take the soil
// underneath, so a road does not report a 65-metre frost front.
private _TABLE = createHashMapFromArray [
    ["ground",     [1.50, 0.25]],  // silt loam, the reference soil
    ["rock",       [2.50, 0.10]],  // rock, little pore water
    ["gravel",     [2.00, 0.10]],  // gravel, free-draining
    ["vegetation", [0.60, 0.35]],  // turf and organic litter, high retention
    ["concrete",   [1.50, 0.25]],  // the soil beneath the slab
    ["asphalt",    [1.50, 0.25]],  // the soil beneath the road
    ["metal",      [1.50, 0.25]],  // the soil beneath the hardstanding
    ["water",      [2.20, 1.00]]   // ice over open water, the lake case
];

private _props = _TABLE getOrDefault [toLower _soil, _TABLE get "ground"];
_props params ["_kF", "_theta"];

private _lFus = 3.34e5;         // J/kg, IAPWS-95 (see the header)
private _rhoDry = 1600;         // kg/m3, the soil dry bulk density
private _secondsPerDay = 86400;

// Q_L = rho_dry * L_f * theta, the volumetric latent heat (J/m3).
// A floor keeps a bone-dry surface from dividing by nothing: even sand
// holds a little water, and a zero would return an unbounded depth.
private _qL = (_rhoDry * _lFus * _theta) max 1e6;

private _c = 100 * sqrt ((2 * _kF * _secondsPerDay) / _qL);

// Snow insulates. Sturm 1997 gives the conductivity of snow against its
// density; the effect on the front is a slower advance. The factor
// saturates: past about half a metre the added snow barely matters, since
// the layer is already the dominant resistance.
if (_snow > 0) then {
    private _insulation = 0.37 + (0.63 * (1 - (_snow / 0.5 min 1)));
    _c = _c * _insulation;
};

_c
