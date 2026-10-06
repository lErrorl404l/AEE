#include "..\script_component.hpp"

/*
Ballistics-coupled shot-audio kernel (wildlife ecology, task T26).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
From the projectile's real parameters it derives the four shot events at the
listener: the muzzle report, the supersonic crack, the near-pass snap and the
ricochet.  The projectile VELOCITY is supplied by the caller from AEE's
ballistics kernel; this kernel never re-derives drag.

Ballistics reuse (where the velocity lives):
  addons/ballistics/functions/fnc_calculateBallisticDrag.sqf   drag + c(T)
  addons/ballistics/functions/fnc_calculateInteriorBallistics.sqf  muzzle v
  addons/ballistics/functions/fnc_calculateMachCone.sqf        Mach geometry
  addons/ballistics/functions/fnc_getLoadData.sqf              service v
  addons/ballistics/functions/fnc_parseCaliber.sqf             calibre
The Fired wiring reads the muzzle velocity from the load resolver and the
calibre from the parser, then calls this kernel.

Model:
  - Local speed of sound c = 20.05 * sqrt(T + 273.15) m/s, SOURCED (the dry-air
    relation; the same convention as fnc_calculateBallisticDrag and
    fnc_calculateMachCone, so the transonic band agrees).
  - Muzzle report.  The level rises with the muzzle velocity and falls with
    distance (20*log10 spherical spreading).  The report pitch rises with the
    muzzle Mach number.  Both shapes are UNSOURCED.
  - Supersonic crack.  Present ONLY while the round is above Mach 1 in the
    LOCAL air, so a hot day raises the threshold.  The level scales with the
    Mach excess and falls with distance.  Shape UNSOURCED.
  - Snap/whiz.  The near pass of a round: present only when its closest
    approach to the listener is inside the snap radius.  UNSOURCED.
  - Ricochet.  From the impact energy and the angle from the surface plane: a
    grazing impact ricochets, a perpendicular one penetrates.  UNSOURCED.

Arguments:
  0: Number - calibre, mm
  1: Number - muzzle velocity, m/s
  2: Number - current velocity, m/s (the drag-reduced speed now)
  3: Number - air temperature, Celsius
  4: Number - listener distance, metres
  5: Number - closest approach of the round to the listener, metres, -1 unknown
  6: Number - impact angle from the surface plane, degrees, -1 no impact
  7: Number - impact energy, joules

Returns:
  Array - [reportLevelDb, reportPitch, crack, crackLevelDb, snapLevelDb,
           ricochetLevelDb]
*/

params [
    ["_caliberMm", 7.62, [0]],
    ["_muzzleVelocity", 0, [0]],
    ["_currentVelocity", 0, [0]],
    ["_airTempC", 15, [0]],
    ["_listenerDistanceM", 0, [0]],
    ["_closestApproachM", -1, [0]],
    ["_impactAngleDeg", -1, [0]],
    ["_impactEnergyJ", 0, [0]]
];

if (_caliberMm <= 0) exitWith { [0, 1, false, 0, 0, 0] };
if (_muzzleVelocity <= 0) exitWith { [0, 1, false, 0, 0, 0] };

// Local speed of sound, SOURCED.
private _speedOfSound = 20.05 * (sqrt (_airTempC + 273.15));
if (_speedOfSound <= 0) exitWith { [0, 1, false, 0, 0, 0] };

private _machMuzzle = _muzzleVelocity / _speedOfSound;
private _machNow = _currentVelocity / _speedOfSound;

// Spherical spreading from the muzzle to the listener.
private _spread = 20 * (log ((_listenerDistanceM max 1) min 1e6));

// Muzzle report.
private _reportSource = WILDLIFE_SHOT_REPORT_DB
    + (20 * (log ((_muzzleVelocity max 1) / WILDLIFE_SHOT_REPORT_REF_MV)));
private _reportLevel = _reportSource - _spread;
private _reportPitch = ((1 + (WILDLIFE_SHOT_PITCH_PER_MACH * (_machMuzzle - 1))) max 0.5) min 2.0;

// Supersonic crack: only while the round is above Mach 1 in the local air.
private _crack = (_machNow > 1);
private _crackLevel = 0;
if (_crack) then {
    _crackLevel = (WILDLIFE_SHOT_CRACK_DB + (30 * (_machNow - 1))) - _spread;
};

// Near-pass snap: only inside the snap radius of the listener.
private _snapLevel = 0;
if ((_closestApproachM >= 0) && (_closestApproachM <= WILDLIFE_SHOT_SNAP_RADIUS_M)) then {
    _snapLevel = WILDLIFE_SHOT_SNAP_DB
        * (1 - (_closestApproachM / WILDLIFE_SHOT_SNAP_RADIUS_M));
};

// Ricochet: a grazing impact with energy ricochets, a perpendicular one does
// not.  The angle is measured from the surface plane.
private _ricochetLevel = 0;
if ((_impactAngleDeg >= 0) && (_impactAngleDeg <= WILDLIFE_SHOT_RICOCHET_ANGLE_DEG)) then {
    if (_impactEnergyJ > 0) then {
        private _energyFactor = ((_impactEnergyJ / WILDLIFE_SHOT_RICOCHET_REF_J) min 1);
        private _angleFactor = 1 - (_impactAngleDeg / WILDLIFE_SHOT_RICOCHET_ANGLE_DEG);
        _ricochetLevel = WILDLIFE_SHOT_RICOCHET_DB * _energyFactor * _angleFactor;
    };
};

[_reportLevel, _reportPitch, _crack, _crackLevel, _snapLevel, _ricochetLevel]
