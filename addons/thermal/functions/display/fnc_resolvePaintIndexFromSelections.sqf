#include "..\..\script_component.hpp"
/*
 * Pure selection-name to paint-index decision (issue #204).
 *
 * setObjectTexture takes a NUMBER that is the position of the slot in the
 * class's CfgVehicles >> hiddenSelections list.  This function owns the
 * decision only; fnc_resolveSelectionPaintIndex reads the two lists from the
 * engine and calls this.  Keeping the decision free of engine calls lets the
 * test harness run it on synthetic lists.
 *
 * A name arrives from one of two lists, and they disagree in form:
 *   - the class's hiddenSelections list: fnc_getThermalSelections resolves a
 *     vehicle's slots from it and fnc_applyBuildingThermal passes those names;
 *   - the model's default-LOD selectionNames list: fnc_getThermalSelectionNames
 *     and the radiative / contact / exhaust callers.
 * B_MRAP_01_F declares Camo1/Camo2/riotpolice while its default LOD carries no
 * camo name at all.  B_UAV_05_F declares Camo1 where the model carries camo1,
 * and its order differs.  B_MBT_01_arty_F declares Camo1..CamoNet with a
 * different model order.  A case-sensitive search (SQF array find is
 * case-sensitive) returned -1 for every one of those, so the loop skipped at
 * the guard and the part was never painted.
 *
 * Resolve the hiddenSelections position FIRST (exact, then case-insensitive),
 * then fall back to the default-LOD selection name for an object that declares
 * no hiddenSelections (a man's uniform).  A name on neither list is genuinely
 * not paintable, so -1 is returned and the caller skips it safely.
 *
 * Params:
 *   0: _hidden (ARRAY of STRING) - the class's hiddenSelections names
 *   1: _model  (ARRAY of STRING) - the object's default-LOD selection names
 *   2: _sel    (STRING) - the requested selection name
 *
 * Returns: NUMBER - the paint index, or -1 when the name is not addressable.
 */
params [
    ["_hidden", [], [[]]],
    ["_model", [], [[]]],
    ["_sel", "", [""]]
];

private _idx = -1;
if (_sel == "") exitWith { _idx };

// Exact hiddenSelections match first, across the whole list.
private _hiddenCount = count _hidden;
for "_i" from 0 to (_hiddenCount - 1) do {
    if ((_idx < 0) && ((_hidden select _i) == _sel)) then { _idx = _i; };
};

// The config and the model disagree on case (Camo1 against camo1), so a
// second pass ignores case.
if (_idx < 0) then {
    private _want = toLower _sel;
    for "_i" from 0 to (_hiddenCount - 1) do {
        if ((_idx < 0) && ((toLower (_hidden select _i)) == _want)) then { _idx = _i; };
    };
};

// Fallback: a model-only name (a man's uniform declares no hiddenSelections).
private _modelCount = count _model;
for "_i" from 0 to (_modelCount - 1) do {
    if ((_idx < 0) && ((_model select _i) == _sel)) then { _idx = _i; };
};

_idx
