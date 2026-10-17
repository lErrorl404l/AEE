#include "..\..\script_component.hpp"
/*
Radar cross section (RCS) by target class, m^2.

The table maps a target class token to a representative monostatic RCS in
the optical region (the SHF case: the target is many wavelengths across, so
a flat RCS is correct and the Rayleigh lambda^-4 region does not apply).
It is the input to the radar range equation.

SOURCED rows.  The value is the published figure, quoted from the table:

  class        RCS m^2   row in Skolnik Table 2.2
  fighter      6         "Large fighter"
  bomber       40        "Large bomber or large jet airliner"
  person       1         "Man"
  vehicle      100       "Automobile" (the table also gives "Pickup truck" 200)
  boat         0.02      "Small open boat"

GAME TUNABLE rows.  No single published scalar exists for these classes, so
the value is a game tunable, declared here with its reason:

  stealth      0.00316   no figure in Skolnik Table 2.2 or NAWCWD TP 8347;
                         the issue's range (0.001-0.01) is used as a tunable
  helicopter   3         no scalar in the held sources; helicopter RCS is
                         dominated by dynamic rotor scattering and no single
                         representative figure is published
  ship         3000      NAWCWD TP 8347 (2012) section 4-11 publishes only a
                         range, "ships 3,000 to 1,000,000 sq m"; the low end
                         is used, and the choice within the range is a tunable

Sources.
  M. I. Skolnik, "Introduction to Radar Systems", 2nd ed., McGraw-Hill,
  1981, Table 2.2 "Example radar cross sections at microwave frequencies",
  p. 44.
  US Navy, "Electronic Warfare and Radar Systems Engineering Handbook",
  NAWCWD TP 8347 (DTIC ADA566236), rev. 4, 2012, section 4-11, p. 4-11.2.

The issue cited Skolnik's "Radar Handbook", which does not carry this table.
Its class range mid-points conflict with the published figures (its vehicle
5-20 m^2 against the published automobile 100 m^2) and were replaced.

Pure: reads no engine state, writes none.

Arguments:
  0: String - target class token

Returns:
  Number - representative RCS sigma, m^2 (0 when the class is unknown)
*/
params [
    ["_class", "", [""]]
];

private _key = toLower _class;

private _table = [
    ["stealth", 0.00316],   // GAME TUNABLE: no published scalar
    ["fighter", 6],          // Skolnik Table 2.2, "Large fighter"
    ["bomber", 40],          // Skolnik Table 2.2, "Large bomber or large jet airliner"
    ["helicopter", 3],       // GAME TUNABLE: no published scalar
    ["person", 1],           // Skolnik Table 2.2, "Man"
    ["vehicle", 100],        // Skolnik Table 2.2, "Automobile"
    ["ship", 3000],          // GAME TUNABLE within NAWCWD range 3,000-1,000,000
    ["boat", 0.02]           // Skolnik Table 2.2, "Small open boat"
];

private _sigma = 0;
{
    if ((_x select 0) == _key) then {
        _sigma = _x select 1;
    };
} forEach _table;

_sigma
