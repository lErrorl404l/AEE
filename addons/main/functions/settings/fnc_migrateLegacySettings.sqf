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
 * The version tag makes the work a one-time event.  A module calls this with
 * its own [oldName, newName] pairs and the version tag; the first call sets
 * profileNamespace "aee_settings_migrated_v<version>".  A later call, from
 * any addon, is a no-op, so the helper is safe to call from every addon and
 * has no side effect on a second call.
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
 *  [[["aee_optics_hudEnabled", "aee_hud_hudEnabled"]], "1"] call FUNC(migrateLegacySettings);
 */

params [["_pairs", [], [[]]], ["_version", "1", [""]]];

// The flag records that THIS version of the migration has run.  A second
// call, from this or any other addon, reads it true and does nothing.
private _flag = format ["aee_settings_migrated_v%1", _version];
if (profileNamespace getVariable [_flag, false]) exitWith { false };

{
    if (!(_x isEqualType []) || {count _x != 2}) then { continue };
    private _old = _x select 0;
    private _new = _x select 1;
    if (!(_old isEqualType "") || {!(_new isEqualType "")}) then { continue };
    if (_old == "" || {_new == ""}) then { continue };

    // Copy only when the new name is unset and the old name is set.  An
    // unset old name means the player never changed the setting, so the
    // new setting registers with its default.  A set new name wins: the
    // migration never overwrites a value the player already saved.
    private _newSet = !(isNil { profileNamespace getVariable [_new, nil] });
    private _oldSet = !(isNil { profileNamespace getVariable [_old, nil] });
    if (!_newSet && {_oldSet}) then {
        profileNamespace setVariable [_new, profileNamespace getVariable _old];
    };
} forEach _pairs;

profileNamespace setVariable [_flag, true];
true
