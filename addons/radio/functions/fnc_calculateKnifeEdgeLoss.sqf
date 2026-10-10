#include "..\script_component.hpp"

/*
Single knife-edge diffraction loss J(nu).

SOURCE: Recommendation ITU-R P.526-16 (2025-11), Annex 1 section 4.1.
Equation (31):

    J(nu) = 6.9 + 20 * log10( sqrt((nu - 0.1)^2 + 1) + nu - 0.1 )   dB

valid for nu greater than -0.78.  The loss is the Fresnel-Kirchoff loss
for an equivalent knife-edge; equation (30) states it exactly and equation
(31) is the Recommendation's closed-form approximation.  For nu below the
-0.78 threshold the obstruction is fully cleared and the loss is 0 dB.

The dimensionless parameter nu is computed from the link geometry by
fnc_calculateTerrainDiffraction, from equation (26):

    nu = h * sqrt( 2/lambda * (1/d1 + 1/d2) )

Argument:
  0: nu (NUMBER) - the dimensionless diffraction parameter

Returns the diffraction loss in dB.

Example: [0] call aee_radio_fnc_calculateKnifeEdgeLoss   // 6.0 dB (grazing)
Public: No
*/

params [["_nu", 0, [0]]];

// A fully cleared path diffracts nothing.
if (_nu <= -0.78) exitWith { 0 };

// SQF's log is base-10 (verified in-game: log 100 = 2), which is the base
// equation (31) is written in.
private _term = (sqrt (((_nu - 0.1) ^ 2) + 1)) + _nu - 0.1;

6.9 + (20 * log _term)
