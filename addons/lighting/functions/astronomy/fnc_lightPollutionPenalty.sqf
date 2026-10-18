#include "..\..\script_component.hpp"

/*
Artificial zenith sky luminance from a nearby settlement, cd/m2.

Albers & Duriscoe (2001), "Modeling light pollution from population data
and implications for National Park Service lands", The George Wright Forum
18(4):56, eq. 1 (Walker's law carried to the zenith): a settlement of
population p adds I = 11,300,000 p r^-2.5 nanolamberts at distance r (m);
inside its radius (2.5 km for the smallest towns) the glow rises linearly by
a further factor 2.5 toward the centre.  The observer is among the houses
counted (within 750 m), so the centre value at the 2.5 km radius applies.
The population is the house count times the average household size of the
country the world portrays (UN DESA 2017; data/settlement_household_size.json:
Greece 2.4, Fiji 4.8, Poland 2.8, France 2.3, Czechia 2.3; the median of 165
countries, 3.8, elsewhere).  1 nL = 3.183e-6 cd/m2.

Arguments:
  0: Number - nearby house count
  1: Number - persons per household
Returns:
  Number - added zenith luminance, cd/m2
*/
params [["_houseCount", 0, [0]], ["_perHouse", 3.8, [0]]];
private _p = (_houseCount max 0) * (_perHouse max 0);
11300000 * _p * (2500 ^ -2.5) * 2.5 * 3.183e-6
