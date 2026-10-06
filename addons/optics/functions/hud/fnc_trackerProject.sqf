#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_trackerProject
 *
 * Pure, argument-driven tracker projector.  It maps the three aee GNSS
 * kernels (the error ellipse, the fix state and the datalink state) onto an
 * exact position and returns the position the tracker DISPLAYS.  It reads no
 * world, no config, no player and no engine state.
 *
 * Mechanism: the displayed position is the exact position displaced by the
 * modelled error.  The displacement magnitude is the error-ellipse R95 radius
 * plus the datalink added position error plus the fix lag offset.  The
 * bearing is a deterministic per-track phase; the step 137.508 degrees is the
 * golden angle, so two adjacent tracks scatter instead of stacking.
 *
 * UNSOURCED shapes (listed for the per-constant register in task 18):
 *   TRACKER_PHASE_STEP  golden-angle track phase step, degrees
 *   the displacement sum and the bearing choice
 *
 * The R95, the added error and the lag are the kernel outputs, so the error
 * itself is sourced by the kernels from GPS SPS PS 5th edition, April 2020
 * (gps.gov).
 *
 * Arguments:
 *   0: exactPos <ARRAY>  exact world position [x, y, z], metres
 *   1: ellipse  <ARRAY>  the gnssErrorEllipse return
 *   2: fix      <ARRAY>  the gnssFixState return
 *   3: link     <ARRAY>  the datalinkState return
 *   4: seed     <NUMBER> per-track phase seed
 *
 * Return: [displayedPos, semiMajor, semiMinor, orientation, trackAge, totalError]
 *   displayedPos is [x, y, z] metres.  The axes are metres.  orientation is
 *   the semi-major bearing in degrees.  trackAge is seconds.  totalError is
 *   the displacement magnitude in metres.
 */
params [
    ["_exactPos", [0, 0, 0], [[]]],
    ["_ellipse", [0, 0, 0, 0, 0, 0, 0, 0], [[]]],
    ["_fix", ["none", 0, 0, 0, 0], [[]]],
    ["_link", ["lost", 0, 0, 0], [[]]],
    ["_seed", 0, [0]]
];

// Read the kernel fields by explicit bounded index.  A short array from a
// fixture stays safe.
private _r95 = 0;
private _semiMajor = 0;
private _semiMinor = 0;
private _orientation = 0;
if ((count _ellipse) > 7) then {
    _r95 = _ellipse select 7;
    _semiMajor = _ellipse select 3;
    _semiMinor = _ellipse select 4;
    _orientation = _ellipse select 5;
};
private _lagOffset = 0;
if ((count _fix) > 3) then { _lagOffset = _fix select 3; };
private _addedError = 0;
private _trackAge = 0;
if ((count _link) > 3) then {
    _addedError = _link select 3;
    _trackAge = _link select 2;
};

// The displacement magnitude.  Every term is a kernel output; the sum is the
// UNSOURCED composition.
private _totalError = ((_r95) max 0) + ((_addedError) max 0) + ((_lagOffset) max 0);

private _phaseStep = 137.508;                            // UNSOURCED
private _bearing = ((_seed * _phaseStep) mod 360);
private _rad = _bearing * (pi / 180);

private _displayed = [
    (_exactPos select 0) + ((sin _rad) * _totalError),
    (_exactPos select 1) + ((cos _rad) * _totalError),
    _exactPos select 2
];

[_displayed, _semiMajor, _semiMinor, _orientation, _trackAge, _totalError]
