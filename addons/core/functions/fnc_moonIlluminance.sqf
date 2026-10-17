#include "..\script_component.hpp"
/*
 * aee_core_fnc_moonIlluminance
 *
 * Horizontal illuminance from the Moon, clear sky.  Pure.
 *
 *   V(a) = -12.73 + 0.026 |a| + 4e-9 a^4      (Krisciunas & Schaefer 1991,
 *                                              PASP 103:1033, eq. 9;
 *                                              a = phase angle, deg)
 *   E_n  = 2.54e-6 lx x 10^(-0.4 V)           (a V = 0 star outside the
 *                                              atmosphere; Schlyter, held
 *                                              in data/astronomy/sources)
 *   E    = E_n sin(h) 10^(-0.4 k X)           X: Kasten & Young 1989 air
 *                                              mass at altitude h
 * The phase angle comes from the illuminated fraction f = (1 + cos a) / 2.
 * Full moon at the zenith: ~0.26 lx through k = 0.2 mag.
 *
 * Arguments:
 *   0: Moon altitude, deg
 *   1: illuminated fraction, 0..1
 *   2: extinction coefficient k, mag per air mass
 * Return: lux (0 below the horizon)
 */
params [["_alt", -90, [0]], ["_frac", 0, [0]], ["_k", 0.2, [0]]];
if (_alt <= 0 || _frac <= 0) exitWith { 0 };
private _a = acos ((((2 * (_frac min 1)) - 1) max -1) min 1);
private _v = -12.73 + (0.026 * _a) + (4e-9 * (_a ^ 4));
private _x = 1 / ((sin _alt) + (0.50572 * ((_alt + 6.07995) ^ -1.6364)));
2.54e-6 * (10 ^ (-0.4 * _v)) * (sin _alt) * (10 ^ (-0.4 * (_k max 0) * _x))
