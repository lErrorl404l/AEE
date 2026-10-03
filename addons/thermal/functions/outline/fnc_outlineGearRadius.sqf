#include "..\..\script_component.hpp"
/*
 * Gear-aware capsule radii and the sensor blur (issue #204, fusion outline).
 *
 * Copied from the per-capsule role switch and the final descriptor in
 * workshop 3811605241 whale_ecoti_llll functions/fn_drawOutlines.sqf.  The
 * source sizes each capsule to what the soldier actually wears, which is why
 * its silhouette reads as a clothed body instead of a bare skeleton:
 *
 *   role 1 head:     _dh = [0, 0.005, 0.012] select _gH, both radii += _dh,
 *                    _ext += [0, 0.02, 0.045] select _gH   (:436-443)
 *   role 2 torso:    _dv = [0, 0.012, 0.03] select _gV, both radii += _dv
 *                                                         (:444-448)
 *   role 3 backpack: no pack -> both radii forced to 0.02 (:449-451)
 *   every radius:    += _infl, the sensor blur
 *                    _infl = (_mpp * 0.5) min 0.12        (:298, :466)
 *
 * _gH is the headgear class (0 none, 1 soft cover, 2 helmet) and _gV the vest
 * class (0 none, 1 light rig, 2 plate).  fnc_outlineDraw resolves those from
 * the unit's headgear / vest and their HitpointsProtectionInfo armor, the same
 * way the source does, and caches the reads for 3 s (:344-371).  This kernel
 * is the arithmetic only, so the harness executes it.
 *
 * Params:
 *   0: _r    (SCALAR) radius at the first bone.
 *   1: _rB   (SCALAR) radius at the second bone.
 *   2: _ext  (SCALAR) capsule extension past the second bone, metres.
 *   3: _role (SCALAR) 0 normal | 1 head | 2 torso | 3 backpack.
 *   4: _gH   (SCALAR) headgear class 0/1/2.
 *   5: _gV   (SCALAR) vest class 0/1/2.
 *   6: _gP   (BOOL)   a backpack is worn.
 *   7: _infl (SCALAR) sensor blur, metres.
 *
 * Returns: ARRAY [extension, radius at A, radius at B], all adjusted.
 *
 * Pure: arithmetic and select only, no engine state, so the harness runs it.
 */
params [
    ["_r", 0, [0]],
    ["_rB", 0, [0]],
    ["_ext", 0, [0]],
    ["_role", 0, [0]],
    ["_gH", 0, [0]],
    ["_gV", 0, [0]],
    ["_gP", false, [true]],
    ["_infl", 0, [0]]
];

// The source's role cases, fn_drawOutlines.sqf:434-452.  The source selects
// the role with a switch; the headless harness has no switch, so the same
// three cases are expressed as if guards.  The tables and arithmetic are
// unchanged.
private _dh = 0;
private _de = 0;
if (_role == 1) then {
    // Headgear inflates both radii and extends the skull capsule.
    _dh = [0, 0.005, 0.012] select _gH;
    _de = [0, 0.02, 0.045] select _gH;
};
if (_role == 2) then {
    // Vest inflates the torso radii only.
    _dh = [0, 0.012, 0.03] select _gV;
};
if ((_role == 3) && {!_gP}) then {
    // No backpack: the pack capsule shrinks into the torso.
    _r = 0.02;
    _rB = 0.02;
};

// The source adds _infl to both radii at the descriptor (fn_drawOutlines:466).
_ext = _ext + _de;
_r = _r + _dh;
_rB = _rB + _dh;
[_ext, _r + _infl, _rB + _infl]
