#include "..\..\script_component.hpp"
#include "\z\aee\addons\main\script_debug.hpp"
/*
 * Thermal same-object selection breadth (issue #204, operator recursive-tree
 * directive).
 *
 * fnc_getThermalSelections resolves the object's LEVEL 0 selections and caches
 * them per class.  This function is the class-static walk that widens the SAME
 * object: every named LOD and every turret config's declared hiddenSelections.
 * Separate nested objects are PER INSTANCE and are handled by
 * fnc_getThermalNestedObjects, which records them for the caller to paint as
 * their own object.
 *
 * INDEX CONTRACT.  setObjectTexture takes the position in the class's
 * CfgVehicles >> hiddenSelections list.  Runtime measurement confirms it: a
 * model default-LOD selectionNames position is a silent no-op.  Level 0
 * already returns config hiddenSelections positions, so a candidate is
 * resolved through the SAME config list - fnc_resolveSelectionPaintIndex is
 * the one resolver that knows that contract - and is added only when the
 * resolved slot IS a declared hiddenSelection.  The resolver's model fallback
 * is rejected here: for a vehicle it is a no-op on the texture channel.
 *
 * A candidate is added only when it is not already covered, so the level-0
 * order is not disturbed.  _MAX_TARGETS is a wide-tree cap.
 *
 * CEILING (honest, do not attempt): a proxy appears only as a placement NAME
 * in the parent's selectionNames ("proxy:\a3\...\weapon.001"): no script handle
 * exists for a proxy, so its INTERNAL selections are unreachable.  A
 * name matching "proxy:" is skipped and is never returned as a paint target.
 * The model.cfg / CfgModels tree is consumed at binarization, not
 * script-readable.
 *
 * Params:
 *   0: _object     (OBJECT) - the vehicle to widen.
 *   1: _selections (ARRAY)  - the level-0 indices on THIS object.
 *
 * Returns: ARRAY of config hiddenSelections positions on _object (level-0
 *   indices plus level-1 breadth).
 */
params [
    ["_object", objNull, [objNull]],
    ["_selections", [], [[]]]
];

if (isNull _object) exitWith { _selections };

// The module trace switch, resolved once for the walk rather than at every
// cap site inside the candidate loop.
private _traceOn = AEE_TRACE_ON;

private _MAX_TARGETS = 512;
// selectionNames accepts exactly these six LOD type names.  Runtime measured
// on the docker harness: "ViewPilot", "ViewGunner", "ViewCargo" and "Shadow"
// are rejected with "Unknown enum value" and abort the call, so the walk
// cannot reach the per-view or Shadow LODs and they are not listed.  A name
// from any LOD is still admitted only when it is a config hiddenSelection
// (the setObjectTexture index space), so an LOD-only name adds nothing.
private _LODS = ["Memory", "Geometry", "FireGeometry", "LandContact", "HitPoints", "ViewGeometry"];
// The parent object's own config hiddenSelections: the EXACT list
// setObjectTexture indexes.  A LOD or turret candidate is accepted only when
// its name appears here.  The turret's own hiddenSelections is a candidate
// NAME source, never an index space, because setObjectTexture addresses the
// vehicle's hiddenSelections alone.
private _hidden = getArray (configOf _object >> "hiddenSelections");

// Names level 0 already covers, in the config hiddenSelections space.
private _covered = [];
{
    if ((_x isEqualType 0) && (_x >= 0) && (_x < count _hidden)) then {
        _covered pushBack (_hidden select _x);
    };
} forEach _selections;

// ── Level 1: same-object breadth ────────────────────────────────────────────
private _candidates = [];
{
    {
        _candidates pushBack _x;
    } forEach (_object selectionNames _x);
} forEach _LODS;

{
    // BIS_fnc_turretConfig returns configNull for a bad path, and getArray on
    // configNull is empty, so no separate null check is needed.
    private _turretCfg = [_object, _x] call BIS_fnc_turretConfig;
    if (isArray (_turretCfg >> "hiddenSelections")) then {
        {
            _candidates pushBack _x;
        } forEach (getArray (_turretCfg >> "hiddenSelections"));
    };
} forEach (allTurrets _object);

// animationSources: the names of the object's animation sources, read from the
// array form and the AnimationSources config class.  An animation source is an
// animation target, not a texture slot, so most yield nothing here.  A name
// that is ALSO a config hiddenSelection is addressable and the same filter
// below admits it; every other name is dropped, so no false selection is added.
{
    _candidates pushBack _x;
} forEach (getArray (configOf _object >> "animationSources"));
{
    _candidates pushBack (configName _x);
} forEach (configProperties [configOf _object >> "AnimationSources", "isClass _x", true]);

{
    private _name = _x;
    // A proxy name is a placement marker, not a texture target: skip it.
    if ((_name isEqualType "") && ((_name find "proxy:") != 0)) then {
        private _idx = [_object, _name] call FUNC(resolveSelectionPaintIndex);
        // Accept only a real CONFIG hiddenSelections slot that carries this
        // name, so a model-only candidate cannot alias a different slot.
        private _slotName = if ((_idx >= 0) && (_idx < count _hidden)) then {
            _hidden select _idx
        } else {
            ""
        };
        private _isConfigSlot = (_slotName != "") && {((toLower _slotName) == (toLower _name))};
        if (_isConfigSlot && {!(_slotName in _covered)}) then {
            if ((count _selections) >= _MAX_TARGETS) then {
                if (_traceOn) then {
                    private _capMsg = format ["selection walk: target cap %1 hit on %2, candidate %3 not added", _MAX_TARGETS, typeOf _object, _name];
                    AEE_LOG_DEBUG(_capMsg);
                };
            } else {
                _selections pushBackUnique _idx;
                _covered pushBack _slotName;
            };
        };
    };
} forEach _candidates;

_selections
