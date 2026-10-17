#include "..\script_component.hpp"
/*
Deterministic pseudo-random value in (0, 1) from two integer seeds.

The engine's numbers are 32-bit floats: an integer is exact only below
2^24.  The previous linear congruential generator multiplied the seeds by
1103515245, far past that, so in-game it returned badly non-uniform values
(the Python test harness, in double precision, could not show it).

This is L'Ecuyer's combined multiplicative generator for 16-bit arithmetic
(P. L'Ecuyer, "Efficient and portable combined random number generators",
Comm. ACM 31(6):742-751, 1988): three generators with moduli 32363, 31727
and 31657 and multipliers 157, 146 and 142, combined by difference.  Every
product stays below 2^24, so each step is exact in float32 and every
machine computes the same value.  The seeds are folded into the generator
states (each addend reduced before it is added, so the fold is exact too)
and mixed for six cross-fed steps.

Arguments:
  0: seed 1 (Number, an integer; e.g. a time block)
  1: seed 2 (Number, an integer; the event-specific salt)
Return Value:
  Number in (0, 1)
*/
params [["_seed1", 0, [0]], ["_seed2", 0, [0]]];

private _a = (floor (abs _seed1)) mod 1048576;
private _b = (floor (abs _seed2)) mod 1048576;
// Each addend is reduced before it is added.  The unwrapped sum
// _a + (_b mod 4096) * 4096 reaches 1.78e7 for a large seed2 (in game an event
// tick, ~1.2e7), above 2^24, where a float32 integer is no longer exact and
// the mod would read a rounded value.  Reducing per addend is the same value
// ((X mod m) + (Y mod m) mod m == (X + Y) mod m) and every intermediate stays
// below 2^24.
private _s1 = 1 + (((_a mod 32362) + (((_b mod 4096) * 4096) mod 32362)) mod 32362);
private _s2 = 1 + (((((_a mod 4096) * 4096) mod 31726) + (_b mod 31726)) mod 31726);
private _s3 = 1 + ((floor (_a / 4096) + floor (_b / 4096) * 256 + (_a mod 7919)) mod 31656);
for "_i" from 1 to 6 do {
    _s1 = (157 * _s1) mod 32363;
    _s2 = (146 * _s2) mod 31727;
    _s3 = (142 * _s3) mod 31657;
    // Cross-feed so neighbouring seeds decorrelate (lag-1 |r| < 0.01 over
    // 1e5 consecutive seeds; tools/tests/test_deterministic_random.py).
    _s1 = 1 + ((_s1 + _s3) mod 32362);
    _s2 = 1 + ((_s2 + _s1) mod 31726);
    _s3 = 1 + ((_s3 + _s2) mod 31656);
};
private _z = (_s1 - _s2 + _s3) mod 32362;
if (_z < 1) then { _z = _z + 32362; };
_z / 32363
