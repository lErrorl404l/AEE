#include "..\..\script_component.hpp"

/*
Volcanic winter cooling (model).

A large eruption injects SO2 into the stratosphere.  The sulfate aerosol
scatters sunlight for one to three years and cools the surface.  The
stratospheric load, and so the radiative forcing, grows with the Volcanic
Explosivity Index (VEI, Newhall & Self 1982).

The global mean cooling is anchored on the Pinatubo (VEI 6, 1991) response,
about -0.5 C for 1-3 years (Robock 2000).  Each VEI unit is a tenfold rise in
ejecta, and the aerosol load roughly doubles per unit, so the cooling doubles
per unit above the VEI 6 anchor.  The doubling is a MODELLING CHOICE; the
issue's -2 C for VEI 7 is the upper end of the published Tambora (1815) range.

The aerosol is injected into one hemisphere and spreads across the equator
over months, so the same-hemisphere response is larger.  It is transported
poleward, so the mid-to-high latitudes cool more than the tropics.

Sources: Robock, A. (2000) "Volcanic eruptions and climate", Rev. Geophys.
38(2):191-219; Newhall, C.G. & Self, S. (1982) J. Geophys. Res.
87(C2):1231-1238; issue #25.

Arguments:
  0: Volcanic Explosivity Index (NUMBER, 0..8)
  1: Observer latitude (NUMBER, degrees, -90..90)
  2: Eruption in the observer hemisphere (BOOL, default true)

Return Value: HashMap
  globalCooling    global mean cooling, K (positive magnitude)
  regionalCooling  local cooling, K
  hemisphereFactor 0.5 or 1.0
  latitudeFactor   > 1 at higher latitudes
Example: [6, 45, true] call aee_atmos_fnc_calculateVolcanicWinter
Public: No
*/

params [
    ["_vei", 0, [0]],
    ["_latitude", 0, [0]],
    ["_sameHemisphere", true, [true]]
];

// ─── Global mean cooling — doubling per VEI unit above the Pinatubo anchor ──
private _globalCooling = 0;
if (_vei >= 2) then {
    _globalCooling = 0.5 * (2 ^ (_vei - 6));
};

// ─── Hemisphere — same-hemisphere cooling is larger ─────────────────────────
private _hemisphereFactor = [0.5, 1.0] select _sameHemisphere;

// ─── Latitude — poleward transport amplifies the mid-to-high latitudes ──────
private _latitudeFactor = 1 + (abs _latitude / 90) * 0.5;

private _regionalCooling = _globalCooling * _hemisphereFactor * _latitudeFactor;

createHashMapFromArray [
    ["globalCooling", _globalCooling],
    ["regionalCooling", _regionalCooling],
    ["hemisphereFactor", _hemisphereFactor],
    ["latitudeFactor", _latitudeFactor]
]
