#include "..\script_component.hpp"

/*
NVG tube tier index.

A testability shim: sqf_lite has no `switch`, so the parent's tier switch
cannot run in the test harness.  This kernel maps the classifier tier string
to a stable integer the other imperfection kernels key off.  It mirrors the
parent's default case: an unrecognised tier falls back to Gen 1.

Arguments:
  0: String - tube tier ("GEN1", "GEN2", "GEN3", "PVS31")

Returns:
  Number - tier index: 0 GEN1, 1 GEN2, 2 GEN3, 3 PVS31.  Any other value
  returns 0 (the parent's default case).
*/

params [["_tier", "", [""]]];

if (_tier == "PVS31") exitWith { 3 };
if (_tier == "GEN3") exitWith { 2 };
if (_tier == "GEN2") exitWith { 1 };

0
