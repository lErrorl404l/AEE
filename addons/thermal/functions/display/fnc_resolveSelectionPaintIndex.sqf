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
 * A name arrives from one of two lists, and they disagree in form:
 *   - the class's hiddenSelections list: fnc_getThermalSelections resolves a
 *     vehicle's slots from it and fnc_applyBuildingThermal passes those names;
 *   - the model's default-LOD selectionNames list: fnc_getThermalSelectionNames
 *     and the radiative / contact / exhaust callers.
 * B_MRAP_01_F declares Camo1/Camo2/riotpolice while its default LOD carries no
 * camo name at all.  B_UAV_05_F declares Camo1 where the model carries camo1,
 * and its order differs.  B_MBT_01_arty_F declares Camo1..CamoNet with a
 * different model order.  A case-sensitive `selectionNames find` (SQF array find
 * is case-sensitive) returned -1 for every one of those, so the loop skipped at
 * the guard and the part was never painted.
 *
 * Resolve the hiddenSelections position FIRST (exact, then case-insensitive),
 * then fall back to the default-LOD selection name for an object that declares
 * no hiddenSelections (a man's uniform).  A name on neither list is genuinely
 * not paintable, so -1 is returned and the caller skips it safely.
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
if (_hidden isNotEqualTo []) then {
    _idx = _hidden find _sel;
    if (_idx < 0) then {
        // SQF array find is case-sensitive, and the config and the model
        // disagree on case (Camo1 against camo1), so a second pass ignores
        // case.  exitWith here leaves the forEach scope only.
        private _want = toLower _sel;
        {
            if ((toLower _x) == _want) exitWith { _idx = _forEachIndex; };
        } forEach _hidden;
    };
};
if (_idx < 0) then {
    _idx = (selectionNames _object) find _sel;
};

_idx
