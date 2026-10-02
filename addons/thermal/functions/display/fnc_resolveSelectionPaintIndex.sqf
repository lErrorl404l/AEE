#include "..\..\script_component.hpp"
/*
 * Resolve a selection name to the paint index setObjectTexture accepts (issue #204).
 *
 * setObjectTexture takes a NUMBER that is the position of the slot in the
 * class's CfgVehicles >> hiddenSelections list.  Runtime measurement confirms it:
 * setting index 0 changes the object's first texture for every class, while
 * setting the position the name happens to hold in the model's default-LOD
 * selectionNames list (63 for the APC camo1, 26 for the MRAP, 51 for the
 * artillery) changes NO texture at all.  The paint passes a number because the
 * same index feeds getSolarAbsorptance and the EXIT restore, so the number must
 * be the hiddenSelections position.
 *
 * The decision is PURE and lives in fnc_resolvePaintIndexFromSelections, so the
 * test harness runs it on synthetic lists.  This function owns only the engine
 * reads and the object guard:
 *   - the class's hiddenSelections name list (the config source the vehicle
 *     discovery and fnc_applyBuildingThermal pass names from);
 *   - the object's default-LOD selectionNames list (the model source
 *     fnc_getThermalSelectionNames and the radiative / contact / exhaust
 *     callers pass names from).
 *
 * A Man or a building declares no hiddenSelections entry, so getArray returns
 * [] and the model list carries the uniform slots.  A name on neither list is
 * genuinely not paintable, so -1 is returned and the caller skips it safely.
 *
 * Params:
 *   0: _object (OBJECT)
 *   1: _sel    (STRING) the selection name
 *
 * Returns: NUMBER - the paint index, or -1 when the name is not addressable.
 */
params [["_object", objNull, [objNull]], ["_sel", "", [""]]];

private _idx = -1;
if (isNull _object || _sel == "") exitWith { _idx };

private _hidden = getArray (configOf _object >> "hiddenSelections");
private _model = selectionNames _object;
_idx = [_hidden, _model, _sel] call FUNC(resolvePaintIndexFromSelections);

_idx
