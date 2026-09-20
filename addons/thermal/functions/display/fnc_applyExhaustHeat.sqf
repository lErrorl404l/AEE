#include "..\..\script_component.hpp"
/*
 * Exhaust / emission heat field (issue #204).
 *
 * A hot gas emission warms everything around it: a firing muzzle blows
 * hot gas over the ground and air in front of it, a jet afterburner
 * heats the tarmac behind the nozzle, a vehicle exhaust plume warms the
 * wall or ground behind the tailpipe.  This is a POINT-SOURCE field -
 * distinct from the object-pair radiative exchange, which transfers
 * between two specific objects.
 *
 * Mechanism: each emission source (a firing weapon, a running engine)
 * produces a heat flux that falls off with distance from the source
 * point.  The field warms:
 *   - the GROUND beneath/around the source (a prone shooter heats the
 *     floor in front of the muzzle; an idling truck warms the tarmac
 *     behind its exhaust),
 *   - nearby OBJECTS within the plume cone.
 *
 * The field is transient: it decays over a few seconds after the source
 * stops (the plume dissipates).  Implemented with the ground-stamp
 * system (a positive warm stamp near the source) and a per-object flux
 * for nearby objects.
 *
 * Params:
 *   0: _mode (STRING, optional) - unused.
 *
 * Returns: SCALAR - the number of emission sources applied.
 */
params [["_mode", ""]];

if (!hasInterface) exitWith { 0 };

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith { 0 };

private _applied = 0;

// ─── 1. Muzzle blast (firing weapon) ──────────────────────────────────────
// The weapon's barrel heat is the firing state.  A hot barrel means hot
// gas has been expelled recently; the plume warms the ground at the
// BARREL END and any object there.  The emission point is the real
// muzzle - captured by the Fired EH from the projectile's position (the
// round and the hot gas come from the same place).  Falls back to a
// position in front of the player only if no shot was captured.
private _weaponHeat = missionNamespace getVariable [QGVAR(barrelHeat), 0];
if !(_weaponHeat isEqualType 0) then { _weaponHeat = 0; };
if (_weaponHeat > 0.1) then {
    private _muzzlePos = missionNamespace getVariable [QEGVAR(thermal,muzzlePos), []];
    private _muzzleT = missionNamespace getVariable [QEGVAR(thermal,muzzleTime), -999];
    private _nowT = diag_tickTime;
    if (count _muzzlePos < 3 || {_nowT - _muzzleT > 10}) then {
        _muzzlePos = _player modelToWorld [0, 1.2, 0.6];   // fallback
    };
    // Ground stamp: hot gas warms the ground exactly at the barrel end.
    private _stampOffset = _weaponHeat * 6;   // ~+6 C at full heat
    [_muzzlePos, _stampOffset, 15] call FUNC(addGroundStamp);
    // Nearby objects within the blast cone get a short radiative kick.
    {
        private _obj = _x;
        if (_obj isKindOf "Man") then { continue; };
        private _dist = _obj distance _muzzlePos;
        if (_dist < 3) then {
            private _sels = [_obj] call FUNC(getThermalSelections);
            if (count _sels > 0) then {
                private _names = selectionNames _obj;
                private _sel = _sels select 0;
                if (_sel < count _names) then {
                    private _flux = _weaponHeat * 800 * (1 - (_dist / 3));
                    [_obj, (_names select _sel), "", _flux, 0.5] call FUNC(applySelectionThermal);
                    _applied = _applied + 1;
                };
            };
        };
    } forEach (_player nearObjects 3);
};

// ─── 2. Engine exhaust (the player's vehicle) ─────────────────────────────
// A running engine's exhaust plume warms the ground and nearby objects
// behind the tailpipe.  The vehicle heat state is the proxy.
private _veh = vehicle _player;
if (_veh != _player && isEngineOn _veh) then {
    private _vehState = _veh getVariable [QGVAR(vehicleHeatState), []];
    private _vehHeat = if (count _vehState >= 1) then { _vehState select 0 } else { 0 };
    if !(_vehHeat isEqualType 0) then { _vehHeat = 0; };
    if (_vehHeat <= 0) then { _vehHeat = [_veh] call FUNC(calculateVehicleHeat); };
    if (_vehHeat > 0.3) then {
        // Tailpipe at the vehicle rear.
        private _exhaustPos = _veh modelToWorld [0, -3, 0.6];
        private _stampOffset = _vehHeat * 8;   // ~+8 C under a hot exhaust
        [_exhaustPos, _stampOffset, 30] call FUNC(addGroundStamp);
        _applied = _applied + 1;
    };
};

_applied
