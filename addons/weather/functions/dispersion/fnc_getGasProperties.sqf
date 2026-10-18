#include "..\..\script_component.hpp"

/*
Dense-gas agent properties (issue #120).

The physical properties of a dense (or buoyant) agent and its published
acute toxic endpoints, from one table so no value is an independent
literal.  The density ratio is the ideal-gas result at equal temperature
and pressure:

  rho_g / rho_a = M_gas / M_air        M_air = 28.97 g/mol (ISO 2533)

so chlorine 70.90/28.97 = 2.447 and CS 188.61/28.97 = 6.511.  The issue's
"1.98 / 3.2" figures are densities at 0 C in kg/m3, not ratios.

Molar masses are the IUPAC/CIAAW atomic weights.  The acute endpoints are
the published values:

  chlorine (CAS 7782-50-5)
    EPA AEGL final (25 C, molar volume 24.45 L/mol): AEGL-2 2.0 ppm,
    AEGL-3 20 ppm at 60 min; NIOSH IDLH 10 ppm; NIOSH REL 0.5 ppm
    ceiling.  ppm -> mg/m3 = ppm * M / 24.45.
  CS (CAS 2698-41-1)
    EPA AEGL final, mg/m3: AEGL-2 0.083 (all durations), AEGL-3 11 at
    60 min; NIOSH IDLH 2 mg/m3 (Pocket Guide 0122); ACGIH TLV ceiling
    0.4 mg/m3.  Saturation vapour pressure 3.4e-5 mmHg at 20 C.
  phosgene (CAS 75-44-5)
    EPA AEGL final, 60 min: AEGL-2 0.30 ppm, AEGL-3 0.75 ppm; NIOSH IDLH
    2 ppm; ACGIH TLV-TWA 0.1 ppm.  Converted with the relation above, so
    AEGL-2 1.21, AEGL-3 3.03, IDLH 8.09, TLV 0.40 mg/m3.
  hydrogen cyanide (CAS 74-90-8)
    EPA AEGL final, 60 min: AEGL-2 7.1 ppm, AEGL-3 15 ppm; NIOSH IDLH
    50 ppm; NIOSH REL ceiling 4.7 ppm (5 mg/m3, 10 min).  Converted with
    the relation above, so AEGL-2 7.85, AEGL-3 16.6, IDLH 55.3, TLV
    5.20 mg/m3.

PENDING and labelled, not filled: the sarin and carbon-dioxide acute
endpoints.  An EPA AEGL final exists for both and was not read for this
model, so both keep 0 and classify as "none".  The vapour pressure stays 0
for phosgene, sarin, carbon-dioxide and hydrogen-cyanide: no property table
was read for them, and an AEGL page does not carry one.

A liquefied agent (normal boiling point below the ambient temperature)
evaporates from a pool held at its boiling point, where the vapour
pressure is one atmosphere; the table value is the saturation vapour
pressure at 20 C for the non-boiling case.  The chlorine figure is
approximately 6.8 bar at 20 C (CRC Handbook of Chemistry and Physics).

An agent whose acute endpoints are not in a source read for this model
carries 0; the classifier then returns "none".  Those zeros are not
invented values, they are the absence of a published figure.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: STRING - the agent key, case-insensitive.  One of: chlorine, cs,
     phosgene, sarin, carbon-dioxide, hydrogen-cyanide.

Returns:
  ARRAY [molarMass g/mol, densityRatio rho_g/rho_a, boilingPointC,
         vapourPressurePa, aegl2MgM3, aegl3MgM3, idlhMgM3, tlvMgM3],
  or [] for an unknown agent.
*/

params [["_agent", "", [""]]];

private _key = toLower _agent;

private _p = [];
if (_key == "chlorine") then {
    _p = [70.90, 2.447, -34.04, 680000, 5.80, 58.0, 29.0, 1.45];
};
if (_key == "cs") then {
    _p = [188.61, 6.511, 310.0, 0.00453, 0.083, 11.0, 2.0, 0.4];
};
if (_key == "phosgene") then {
    _p = [98.91, 3.414, 7.6, 0, 1.21, 3.03, 8.09, 0.40];
};
if (_key == "sarin") then {
    _p = [140.09, 4.836, 158.0, 0, 0, 0, 0, 0];
};
if (_key == "carbon-dioxide") then {
    _p = [44.01, 1.519, -78.5, 0, 0, 0, 0, 0];
};
if (_key == "hydrogen-cyanide") then {
    _p = [27.03, 0.933, 25.6, 0, 7.85, 16.6, 55.3, 5.20];
};

_p
