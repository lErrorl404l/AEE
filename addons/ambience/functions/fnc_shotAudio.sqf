#include "..\script_component.hpp"
/*
Ballistics-coupled shot-audio kernel (wildlife ecology, task T26).
Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
From the projectile's real parameters it derives the shot events at the
listener: the muzzle report and the ballistic shock wave (the supersonic
"crack" of a near pass).  The projectile velocity is the caller's, from
AEE's ballistics kernels.

  - Local speed of sound c = SOUND_SPEED_COEFF * sqrt(T + KELVIN_OFFSET).
  - Muzzle report.  The reference is the measured peak of an M4 (5.56 mm,
    ~900 m/s), WILDLIFE_SHOT_REPORT_DB at 1 m (NIOSH HHE 2013-0124-3208).
    Other weapons scale by Hopkinson-Cranz cube-root blast scaling (Cranz
    1926; Baker, Explosions in Air, 1973): at a fixed distance the far-field
    overpressure goes as W^1/3 and the blast duration as W^1/3, so
      L = L_ref + (20/3) log10(E / E_ref),  pitch = (E / E_ref)^(-1/3),
    E the muzzle energy, which for geometrically similar projectiles goes
    as d^3 v^2 (projectile mass ~ d^3).
  - Ballistic shock wave.  Only while the round is above Mach 1 in the local
    air.  The N-wave peak overpressure at miss distance b is Whitham's
    (1952, Comm Pure Appl Math 5:301), the form used by Stoughton (1997,
    JASA 102:781) and Hamernik et al. for small arms:
      dp = 0.53 p0 (M^2 - 1)^1/8 d / (b^3/4 l^1/4)
    p0 101325 Pa, d the calibre and l the bullet length, l = 3.9 d (the
    M80 7.62 mm ball is 3.7 calibres long, the M855 5.56 mm 4.1; l enters at
    the quarter power, so +-10 % is +-0.2 dB).  The level is
    20 log10(dp / 20 uPa).  With no closest approach the listener distance
    is taken as the miss distance.  The snap is that wave at the closest
    approach.
  - Ricochet is not modelled (no published level law); it returns 0.

Arguments:
  0: Number - calibre, mm
  1: Number - muzzle velocity, m/s
  2: Number - current velocity, m/s
  3: Number - air temperature, Celsius
  4: Number - listener distance from the muzzle, metres
  5: Number - closest approach of the round to the listener, m, -1 unknown
  6: Number - impact angle from the surface plane, degrees (unused)
  7: Number - impact energy, joules (unused)
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
private _speedOfSound = SOUND_SPEED_COEFF * (sqrt (_airTempC + KELVIN_OFFSET));
if (_speedOfSound <= 0) exitWith { [0, 1, false, 0, 0, 0] };

// Muzzle report: cube-root blast scaling on the muzzle energy.
private _energyRatio = ((_caliberMm / 5.56) ^ 3) * ((_muzzleVelocity / WILDLIFE_SHOT_REPORT_REF_MV) ^ 2);
private _spread = 20 * (log ((_listenerDistanceM max 1) min 1e6));
private _reportLevel = WILDLIFE_SHOT_REPORT_DB + ((20 / 3) * (log _energyRatio)) - _spread;
private _reportPitch = ((_energyRatio ^ (-1 / 3)) max 0.25) min 4;

// Ballistic shock wave (Whitham).
private _machNow = _currentVelocity / _speedOfSound;
private _crack = (_machNow > 1);
private _dM = _caliberMm / 1000;
private _lM = 3.9 * _dM;
private _whitham = {
    params ["_b"];
    private _dp = 0.53 * 101325 * (((_machNow ^ 2) - 1) ^ 0.125) * _dM / (((_b max 0.05) ^ 0.75) * (_lM ^ 0.25));
    20 * (log (_dp / 2e-5))
};
private _crackLevel = 0;
private _snapLevel = 0;
if (_crack) then {
    private _miss = [_listenerDistanceM max 1, _closestApproachM] select (_closestApproachM >= 0);
    _crackLevel = _miss call _whitham;
    if (_closestApproachM >= 0) then { _snapLevel = _crackLevel; };
};
[_reportLevel, _reportPitch, _crack, _crackLevel, _snapLevel, 0]
