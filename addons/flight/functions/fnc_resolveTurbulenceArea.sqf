#include "..\script_component.hpp"

/*
Effective drag area for the turbulence force, from an aircraft corpus row.

The gust force needs the airframe's drag reference area Cd S.  The aircraft
corpus already holds it, so this kernel reads the row the matcher returns; it
adds no parallel data table.  The row order is the generated value row:

  [operating_weight_kg, rated_power_w, drag_area_m2, rotor_disc_area_m2]

A fixed-wing entry holds drag_area_m2, the product drag_coefficient *
wing_area_m2 (data/aircraft/SCHEMA.md section 5), so the coefficient is already
in the area.  A rotary-wing entry holds rotor_disc_area_m2, pi * (D / 2)^2, the
disc the corpus uses as the rotor reference area; drag_area_m2 is a fixed-wing
field and is zero for a rotary airframe.  When neither is held the kernel
default AERO_DRAG_AREA_M2 stands.

Arguments:
  0: ARRAY - the aircraft value row, or [] when the class is unknown

Return Value: NUMBER - effective drag area in m^2, > 0
Example: [[752, 313000, 0, 50.9]] call aee_flight_fnc_resolveTurbulenceArea
Public: No
*/

params [["_aircraftRow", [], [[]]]];

private _dragArea = 0;
private _rotorArea = 0;
if ((count _aircraftRow) > 2) then { _dragArea = _aircraftRow select 2; };
if ((count _aircraftRow) > 3) then { _rotorArea = _aircraftRow select 3; };

if (_dragArea > 0) exitWith { _dragArea };
if (_rotorArea > 0) exitWith { _rotorArea };

AERO_DRAG_AREA_M2
