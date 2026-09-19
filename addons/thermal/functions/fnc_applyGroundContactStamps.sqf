#include "..\script_component.hpp"
/*
Lay ground thermal stamps from contact events (issue #124).

This is the emitter side of thermal painting: it turns the physical
contact between an object and the ground into a decaying temperature
stamp at that position.  The stamps are then summed by
fnc_getGroundStampOffset inside fnc_calculateGroundTemperature.

Three contact classes, each with real heat-transfer physics:

1. Tyre contact (moving or just-moved vehicle):
   The tyre is warm from friction and its own per-selection solve; the
   ground under it warms by conduction from a hot contact.  The offset
   is the tyre-to-ground temperature difference scaled by a contact
   factor - a hot brake disc under a standing vehicle's wheels does not
   heat 5 m of soil, but a tracked vehicle's tracks lay a real band.
   A tyre stamp is +2 C per ~20 C of tyre elevation, decaying over the
   ground tau (~600 s soil, faster on asphalt).

2. Parked-vehicle shade (the "cool patch" under a car parked a while):
   While the vehicle body covers the ground, solar loading drops to
   near zero, so the patch relaxes below the surrounding sun-heated
   equilibrium.  When the vehicle moves away the patch is cooler than
   its surroundings and rewarms with the ground tau.  The offset is
   negative: -1 C per ~10 C of solar equilibrium elevation, decaying
   over the ground tau.

3. Soldier boots (footprints):
   A standing soldier's sole is at skin temperature (~30 C) and
   conducts into the ground; each footprint is a small +1..2 C offset
   with a SHORT tau (a shallow contact patch loses heat fast).

All three reuse the per-selection temperatures the solver already
produces - no new physics, just the contact coupling.

Input:
  0: object (OBJECT) - the vehicle or unit laying the stamp

Output: nothing
*/

params [["_obj", objNull, [objNull]]];
if (isNull _obj) exitWith {};
if !(EGVAR(core,enabled)) exitWith {};

private _pos = getPosATL _obj;
if (count _pos < 2) exitWith {};

private _selTemps = missionNamespace getVariable [QGVAR(selTemperature), createHashMap];
if (isNil "_selTemps") then { _selTemps = createHashMap; };
private _key = str _obj;

private _groundT = [_pos] call FUNC(calculateGroundTemperature);
if (isNil "_groundT") then { _groundT = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15]; };

private _isVehicle = (_obj isKindOf "LandVehicle") || {_obj isKindOf "Tank"};
private _isSoldier = _obj isKindOf "CAManBase";

// ─── 1. Tyre / track contact ──────────────────────────────────────────────
if (_isVehicle) then {
    // A parked vehicle (no engine, no movement) still keeps its wheels
    // at tyre temperature; the stamp strength scales with how hot the
    // wheel selection is vs the ground.
    private _wheelTemp = nil;
    {
        if ((["wheel", _x] call BIS_fnc_inString) && {(_selTemps getOrDefault [_key + "_" + _x, nil]) isNotEqualTo nil}) exitWith {
            _wheelTemp = _selTemps getOrDefault [_key + "_" + _x, nil];
        };
    } forEach (selectionNames _obj);

    if (!isNil "_wheelTemp") then {
        private _delta = _wheelTemp - _groundT;
        if (_delta > 5) then {
            // Contact conduction: only a fraction of the tyre delta
            // transfers into the soil patch (tyre is a thin tread).
            private _offset = _delta * 0.10 max 0.5 min 5;
            [_pos, _offset, 600] call FUNC(addGroundStamp);
        };
    };

    // ─── 2. Parked shade patch ────────────────────────────────────────────
    // A vehicle that has been stationary long enough for the body to
    // cool the ground under it leaves a negative stamp.  The stamp is
    // laid ONCE when the vehicle starts moving again (the "it was
    // parked" signature); while parked the ground under it is simply
    // solved with reduced exposure (handled by the selection solve).
    private _still = speed _obj < 0.5;
    private _wasStill = _obj getVariable [QGVAR(wasParked), false];
    if (!_still && _wasStill) then {
        // Solar equilibrium elevation above air - the patch under the
        // car was shielded from this, so it is this far below.
        private _solar = missionNamespace getVariable [QEGVAR(core,currentSolarFlux), 0];
        if (isNil "_solar") then { _solar = 0; };
        private _elevation = _solar * 0.012;  // ~12 C per 1000 W/m2 (asphalt)
        if (_elevation > 3) then {
            private _offset = -(_elevation * 0.6);  // partial shielding
            [_pos, _offset, 1200] call FUNC(addGroundStamp);  // long tau: body mass held the ground cool
        };
    };
    _obj setVariable [QGVAR(wasParked), _still, true];

// ─── 3. Boot footprints ───────────────────────────────────────────────────
} else {
    if (_isSoldier) then {
        // A moving soldier's soles conduct body heat into the ground.
        // Skin ~30 C vs cold ground = small warm stamp, short tau (a
        // shallow contact patch re-equilibrates in minutes).
        if (speed _obj > 0.5) then {
            private _delta = 30 - _groundT;
            if (_delta > 5) then {
                private _offset = _delta * 0.04 max 0.2 min 1.5;
                [_pos, _offset, 180] call FUNC(addGroundStamp);
            };
        };
    };
};
