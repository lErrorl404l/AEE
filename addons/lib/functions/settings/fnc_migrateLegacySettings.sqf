#include "..\..\script_component.hpp"
/*
 * aee_<component>_fnc_migrateLegacySettings
 *
 * One-time migration of renamed CBA settings (ADR-032, plan section 3).
 *
 * A renamed setting loses its stored value: CBA keeps each setting in
 * profileNamespace under its exact name and has no alias facility.  This
 * helper copies each set old value to its new name ONCE, before the module
 * registers the new setting, so CBA_fnc_addSetting reads the migrated value.
 *
 * The flag makes the work a one-time event PER PAIR-SET.  A module calls this
 * with its own [oldName, newName] pairs and the shared version tag.  The flag
 * is keyed on the version AND the caller's pairs, so each module's table
 * migrates once and a repeat call from the same module is a no-op.  Keying on
 * the version alone let the first caller migrate and made every later module a
 * silent no-op (issue #249).
 *
 * Arguments:
 *  0: pairs (Array) - array of [oldName, newName] STRING pairs to migrate
 *  1: version (String, optional) - the migration version tag, default "1"
 *
 * Return Value:
 *  Boolean - true when this call performed the migration, false when the
 *  version flag was already set (the idempotent no-op)
 *
 * Example:
 *  [[["aee_hud_hudEnabled", "aee_hud_hudEnabled"]], "1"] call FUNC(migrateLegacySettings);
 */

params [["_pairs", [], [[]]], ["_version", "1", [""]]];

// The flag records that THIS pair-set has migrated at THIS version.  Every
// module calls the helper with the same version tag and its own table, so a
// version-only flag let the first caller win and made the rest no-ops.  The
// tag is the first new name, which carries the aee_<module>_ token.
private _pairTag = "";
if ((_pairs isNotEqualTo []) && {(_pairs select 0) isEqualType []}) then {
    _pairTag = (_pairs select 0) param [1, ""];
};
private _flag = format ["aee_settings_migrated_v%1_%2", _version, _pairTag];
if (profileNamespace getVariable [_flag, false]) exitWith { false };

{
    if (!(_x isEqualType []) || {count _x != 2}) then { continue };
    private _old = _x select 0;
    private _new = _x select 1;
    if (!(_old isEqualType "") || {!(_new isEqualType "")}) then { continue };
    if (_old == "" || _new == "") then { continue };

    // Copy only when the new name is unset and the old name is set.  An
    // unset old name means the player never changed the setting, so the
    // new setting registers with its default.  A set new name wins: the
    // migration never overwrites a value the player already saved.
    private _newSet = !(isNil { profileNamespace getVariable _new });
    private _oldSet = !(isNil { profileNamespace getVariable _old });
    if (!_newSet && _oldSet) then {
        profileNamespace setVariable [_new, profileNamespace getVariable _old];
    };
} forEach _pairs;

profileNamespace setVariable [_flag, true];
true
