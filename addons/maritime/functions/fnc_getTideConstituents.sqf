#include "..\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_tide_constituents.py

Tide-gauge harmonic constants for the current world, from TICON-4
(Hart-Davis, M., Dettmering, D., Seitz, F. (DGFI-TUM), 2025, DOI 10.17882/109129,
CC BY 4.0 (SEANOE)).  Constituent order: M2 S2 N2 K2 K1 O1 P1 Q1.
Each entry is [amplitude m, Greenwich phase lag deg].
  samothraki: samothraki-sam-grc-cmems (GRC, 6 yr, Possible quality control issues)
  lautoka: lautoka-67070-fji-bom (FJI, 31 yr, No obvious issues)

Return: [constituents, bound] - bound is false for a world with no
gauge, whose constituents are the Doodson equilibrium ratios scaled by
the M2 amplitude setting with zero phase lag; [] for a world with no
ocean tide (Livonia).
Public: No
*/

private _GAUGES = createHashMapFromArray [
    ["samothraki", [[0.07646, 56.099], [0.05297, 75.925], [0.01197, 66.305], [0.01629, 70.295], [0.02527, 341.614], [0.01319, 306.688], [0.0103, 348.281], [0.00167, 265.416]]],
    ["lautoka", [[0.62907, 191.557], [0.14846, 192.568], [0.14767, 172.208], [0.0422, 185.708], [0.11166, 48.875], [0.06051, 35.855], [0.0327, 44.817], [0.00976, 21.445]]]
];
private _WORLDS = createHashMapFromArray [
    ["altis", "samothraki"],
    ["enoch", ""],
    ["malden", "samothraki"],
    ["stratis", "samothraki"],
    ["tanoa", "lautoka"]
];

private _gid = _WORLDS getOrDefault [toLower worldName, "-"];
if (_gid == "") exitWith { [] };
if (_gid != "-") exitWith { [_GAUGES get _gid, true] };
private _m2 = missionNamespace getVariable [QGVAR(tideAmplitude), 1.0];
if !(_m2 isEqualType 0) then { _m2 = 1.0; };
[[[_m2 * 1, 0], [_m2 * 0.4657, 0], [_m2 * 0.1915, 0], [_m2 * 0.1267, 0], [_m2 * 0.5842, 0], [_m2 * 0.4153, 0], [_m2 * 0.1933, 0], [_m2 * 0.0795, 0]], false]
