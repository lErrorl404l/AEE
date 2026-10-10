#include "..\script_component.hpp"
/*
Speed of sound in seawater (issue #113).

Mackenzie (1981), "Nine-term equation for sound speed in the oceans",
Journal of the Acoustical Society of America 70(3):807-812,
DOI 10.1121/1.386920.

    c = 1448.96 + 4.591 T - 5.304e-2 T^2 + 2.374e-4 T^3
        + 1.340 (S - 35) + 1.630e-2 D + 1.675e-7 D^2
        - 1.025e-2 T (S - 35) - 7.139e-13 T D^3

  T  temperature, degC
  S  salinity, psu (practical salinity units)
  D  depth, m
  c  sound speed, m/s

Validity: T 0..30 C, S 30..40 psu, D 0..8000 m.  The nine-term form is the
full published equation.  The two cross terms (-1.025e-2 T (S-35) and
-7.139e-13 T D^3) are zero at S=35, D=0, so a seven-term truncation agrees
on the axis but diverges off it; the full form is used here.

Worked example: T=10, S=35, D=0 -> c = 1489.8 m/s.  The common "1481 m/s"
estimate is wrong; the issue records the same correction.

Input:  [T, S, D]
Output: sound speed in m/s
*/

params [
    ["_T", 10, [0]],
    ["_S", 35, [0]],
    ["_D", 0, [0]]
];

private _c =
      1448.96
    + 4.591 * _T
    - 5.304e-2 * _T ^ 2
    + 2.374e-4 * _T ^ 3
    + 1.340 * (_S - 35)
    + 1.630e-2 * _D
    + 1.675e-7 * _D ^ 2
    - 1.025e-2 * _T * (_S - 35)
    - 7.139e-13 * _T * _D ^ 3;

_c
