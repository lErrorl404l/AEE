#include "..\script_component.hpp"
/*
Surface accretion load on a bound vehicle (W2 runtime coupling).

A vehicle gains mass while it sits or drives through a surface medium.
Snow settles on the hull. The added mass is a published layer model:

    mass = top area * layer depth * bulk density

The top area is the vehicle's own bounding-box length times its width.
The layer depth is the modelled snow depth aee_core_snowDepth_m.
The bulk density is the sourced setting aee_persistence_slabDensity.
The default 300 kg/m3 is settled mid-winter snow. The published snowpack
range is 100 to 500 kg/m3 (see the mobility coupling research note).

Mud has no published accretion-mass coefficient for any vehicle. The
dimensionless mudAccretion state is a visual fraction, and no source gives
the mass of mud that adheres to a wheel, a track or a wheel arch. This
function therefore adds no mud mass. An invented coefficient would violate
the value rule, so the mud mass coupling stays unshipped.

Arguments:
  0: vehicle (OBJECT)
  1: snow depth (NUMBER, metres)

Return Value: NUMBER - the accreted mass in kilograms, 0 or more
Example: [cursorObject, 0.3] call aee_mobility_fnc_calculateAccretionMass
Public: No
*/

params [["_vehicle", objNull, [objNull]], ["_snowDepth", 0, [0]]];

if (isNull _vehicle) exitWith { 0 };
if !(_snowDepth isEqualType 0) exitWith { 0 };

private _depth = _snowDepth max 0;
if (_depth <= 0) exitWith { 0 };

private _density = missionNamespace getVariable [QEGVAR(persistence,slabDensity), 300];
if !(_density isEqualType 0) then { _density = 300; };
if (_density <= 0) exitWith { 0 };

// The vehicle's own upward-facing footprint. The box is engine geometry,
// used as a shape, never as a value source.
private _box = boundingBoxReal _vehicle;
if !(_box isEqualType []) exitWith { 0 };
if ((count _box) < 2) exitWith { 0 };
private _min = _box select 0;
private _max = _box select 1;
if !(_min isEqualType []) exitWith { 0 };
if !(_max isEqualType []) exitWith { 0 };

private _lengthM = abs ((_max select 0) - (_min select 0));
private _widthM = abs ((_max select 1) - (_min select 1));

_lengthM * _widthM * _depth * _density
