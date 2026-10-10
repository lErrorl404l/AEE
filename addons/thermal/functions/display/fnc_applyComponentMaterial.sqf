#include "..\..\script_component.hpp"
/*
Apply an AEE material to a component by role (issue #128, ADR-001).

The material library (#124) reaches the rendered world through one of three
mechanisms (ADR-001).  This function is the RUNTIME-ANCHOR path: it resolves a
component ROLE to the model selections that name that part
(fnc_getComponentAnchors), then applies the material to each selection with
setObjectMaterial.

  - The RUNTIME anchor (this function): setObjectMaterial per selection.
    Client-local, reversible, needs no model edit.  The material is selected
    from existing .rvmat assets only (no custom shader).
  - The PBO path override: ship a replacement .paa/.rvmat at the vanilla
    path.  Load-time, global, last-loaded wins.  AEE cannot author the binary
    asset here, so this function does not perform it.
  - The config override: add hiddenSelectionsMaterials[] to a class that had
    none.  Load-time, needs the selection to exist in the P3D.  AEE cannot
    verify the model's selections without the model, so this is not performed
    here either.

CEILINGS (what this cannot reach; recorded so the next worker does not retry):

  - setObjectMaterial selects an EXISTING material; it cannot define a new
    shader or a per-object material program.
  - The swap is CLIENT-LOCAL.  Every client must apply the same material for a
    consistent view; setObjectMaterialGlobal exists but is not used here.
  - The selection must exist in the model.  A role with no resolved selection
    applies to nothing (fnc_getComponentAnchors returns no entry for it).
  - setObjectMaterial accepts the hiddenSelections index, not a name.  The
    index is resolved by fnc_resolveSelectionPaintIndex.

Params:
  0: _vehicle  (OBJECT) - the vehicle.
  1: _role     (STRING) - a component role (engine, wheel, turret, glass ...).
  2: _material (STRING) - the .rvmat path, or "#reset" to restore the default
                          (the engine supports "#reset" since 2.20).

Returns: NUMBER - the number of selections the material was applied to.
*/

params [
    ["_vehicle", objNull, [objNull]],
    ["_role", "", [""]],
    ["_material", "", [""]]
];

if (isNull _vehicle || _role == "" || _material == "") exitWith { 0 };

private _sels = ([_vehicle] call FUNC(getComponentAnchors)) getOrDefault [_role, []];
if (_sels isEqualTo []) exitWith { 0 };

private _applied = 0;
{
    private _idx = [_vehicle, _x] call FUNC(resolveSelectionPaintIndex);
    if (_idx >= 0) then {
        _vehicle setObjectMaterial [_idx, _material];
        _applied = _applied + 1;
    };
} forEach _sels;

_applied
