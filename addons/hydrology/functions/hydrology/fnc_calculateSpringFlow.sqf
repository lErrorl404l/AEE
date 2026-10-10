#include "..\..\script_component.hpp"
/*
Spring discharge by Darcy's law (issue #26).

A spring is a point where the water table meets the ground surface.  Its flow
is the Darcy discharge through the saturated conduit that feeds it:

  Q = K_sat * A * i

Q is the discharge (m3/s), K_sat the saturated hydraulic conductivity
(m/day), A the conduit cross-sectional area (m2) and i the hydraulic
gradient (dimensionless, the slope of the water table).  The spring flows
only while the water table stands above the orifice: a water table deeper
than the spring's elevation leaves it dry.

  active = waterTableDepth_m < orificeDepth_m

Source: Darcy, H. (1856), "Les fontaines publiques de la ville de Dijon".
Freeze, R.A. and Cherry, J.A. (1979), "Groundwater", Prentice-Hall, chapter
2 (Darcy's law and its field forms).

Args:
  0: water-table depth below ground (NUMBER, m, default 0)
  1: spring orifice depth below ground (NUMBER, m, default 1)
  2: saturated conductivity K_sat (NUMBER, m/day, default 10)
  3: conduit cross-sectional area (NUMBER, m2, default 1)
  4: hydraulic gradient i (NUMBER, default 0.01)

Returns [flow_m3s, active].
*/

params [
    ["_waterTableDepth", 0, [0]],
    ["_orificeDepth", 1, [0]],
    ["_kSat", 10, [0]],
    ["_area", 1, [0]],
    ["_gradient", 0.01, [0]]
];

if !(_waterTableDepth isEqualType 0) then { _waterTableDepth = 0; };
if !(_orificeDepth isEqualType 0) then { _orificeDepth = 1; };
if !(_kSat isEqualType 0) then { _kSat = 10; };
if !(_area isEqualType 0) then { _area = 1; };
if !(_gradient isEqualType 0) then { _gradient = 0.01; };
_waterTableDepth = _waterTableDepth max 0;
_kSat = _kSat max 0;
_area = _area max 0;
_gradient = _gradient max 0;

// Dry while the water table stands below the orifice.
if (_waterTableDepth >= _orificeDepth) exitWith { [0, false] };

// K_sat (m/day) * A (m2) * i = m3/day; the second per second is m3/s.
private _flowM3s = (_kSat * _area * _gradient) / 86400;

[_flowM3s max 0, true]
