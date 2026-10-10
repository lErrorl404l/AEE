#include "..\script_component.hpp"
/*
Diffuse attenuation from a Secchi-disk depth (issue #14).

The Secchi disk is the classic clarity measurement.  The white disk
disappears at the Secchi depth Zsd.  The diffuse attenuation follows from
the empirical relation:

    clear water:  Kd = 1.7 / Zsd   (Poole and Atkins 1929)
    turbid water: Kd = 1.44 / Zsd  (Holmes 1970)

The 1.7 factor matches the open ocean.  The 1.44 factor matches coastal
and inland water, where scattering is higher.

Typical Secchi depths: open ocean 30-50 m, coastal 5-20 m, lake 1-10 m,
river 0.1-2 m.

Input:  [_secchiDepth, _turbid]
          _secchiDepth - Secchi depth in metres
          _turbid      - true for the coastal and inland factor (default false)
Output: Kd in m^-1.  Zero when the depth is not positive.
*/

params [
    ["_secchiDepth", 0, [0]],
    ["_turbid", false, [false]]
];

if (_secchiDepth <= 0) exitWith { 0 };

private _factor = [1.7, 1.44] select _turbid;
_factor / _secchiDepth
