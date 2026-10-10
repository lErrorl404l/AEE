#include "..\..\script_component.hpp"
/*
Rainfall kinetic energy per unit rainfall (RUSLE R-factor building block,
issue #21).

The R factor of the RUSLE is the rainfall erosivity, the sum over a year of
the storm erosivity index EI30. Its first term is the kinetic energy a
storm delivers per millimetre of rain. That energy is a function of the
rainfall INTENSITY, not the depth: a hard convective burst breaks far more
soil loose per millimetre than a long drizzle.

Brown and Foster (1987), adopted in Renard et al. (1997) USDA Agriculture
Handbook 703, chapter 2, give the energy per millimetre as

  e = 0.29 * (1 - 0.72 * exp(-0.05 * I))     MJ/ha/mm

with I the rainfall intensity in mm/h. At I = 25 mm/h this is 0.2302
MJ/ha/mm. The value 0.226 in the issue text is a transcription error and
is NOT reproducible from the published form; the kernel uses the published
form.

Wischmeier and Smith (1978), USDA Agriculture Handbook 537, give the older
logarithmic form, still used where a dataset is calibrated on it:

  e = 0.119 + 0.0873 * log10(I)   for I <= 76 mm/h
  e = 0.283                        for I > 76 mm/h

Args:
  0: rainfall intensity (NUMBER, mm/h, default 0)
  1: form (STRING, "brownFoster" or "wischmeier", default "brownFoster")

Returns the energy in MJ/ha/mm.

Example:
  [25] call aee_hydrology_fnc_calculateKineticEnergy -> 0.2302
*/

params [["_intensity", 0, [0]], ["_form", "brownFoster", [""]]];

if !(_intensity isEqualType 0) then { _intensity = 0; };
if !(_form isEqualType "") then { _form = "brownFoster"; };
_intensity = _intensity max 0;

private _e = 0;
if (_intensity > 0) then {
    if (toLower _form == "wischmeier") then {
        // Wischmeier and Smith (1978) AH-537.
        _e = if (_intensity <= 76) then {
            0.119 + (0.0873 * log _intensity)
        } else {
            0.283
        };
    } else {
        // Brown and Foster (1987), as adopted in AH-703.
        _e = 0.29 * (1 - (0.72 * exp (-0.05 * _intensity)));
    };
};

_e
