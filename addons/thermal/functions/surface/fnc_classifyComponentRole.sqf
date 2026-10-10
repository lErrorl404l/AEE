#include "..\..\script_component.hpp"
/*
Component role from an engine anchor name (issue #128).

The engine exposes named selections and hit points as FIXED anchors (ADR-001).
AEE's per-component physics needs to know WHICH physical part an anchor names:
the engine bay, a wheel, the glass, the turret.  This function is the one
anchor-name to component-role mapping, so the per-component consumers agree on
one vocabulary instead of each matching names of its own.

The role vocabulary is closed and shared with the material registry
(fnc_getHitPointMaterials): wheel, track, rotor, glass, engine, fuel, turret,
gun, avionics, hull.  An unknown anchor returns "" and the caller treats the
part as unclassified - no role is invented.

Resolution is by SUBSTRING, because the engine's hit-point names are
standardised across every vehicle (HitLFWheel, HitEngine, HitGlass1, HitTurret,
HitHRotor) and the model selection names follow the same part words
(wheel_1_1, engine, glass_front).  The order below puts the specific part
before the generic body, so "glass" beats "hull" for a "hull_glass" name.

This is a PURE function: no engine call, no namespace read.  It is mirrored by
tools/tests/test_component_anchors.py and executed on the mirror, because the
shared sqf_lite interpreter does not implement the `find` command.

Params:
  0: _name (STRING) - a hit-point name or a model selection name.

Returns: STRING - the component role, or "" when the name is not a known part.
*/

params [["_name", "", [""]]];

if (_name == "") exitWith { "" };

private _n = toLower _name;

if (_n find "wheel" >= 0 || {_n find "tyre" >= 0} || {_n find "tire" >= 0}) exitWith { "wheel" };
if (_n find "track" >= 0) exitWith { "track" };
if (_n find "rotor" >= 0) exitWith { "rotor" };
if (_n find "glass" >= 0 || {_n find "windshield" >= 0} || {_n find "window" >= 0}) exitWith { "glass" };
if (_n find "engine" >= 0 || {_n find "motor" >= 0}) exitWith { "engine" };
if (_n find "fuel" >= 0) exitWith { "fuel" };
if (_n find "turret" >= 0) exitWith { "turret" };
if (_n find "gun" >= 0 || {_n find "barrel" >= 0}) exitWith { "gun" };
if (_n find "avionics" >= 0) exitWith { "avionics" };
if (_n find "hull" >= 0 || {_n find "body" >= 0}) exitWith { "hull" };

""
