#include "..\..\script_component.hpp"
/*
Per-selection thermal material registry (issue #124).

Maps the AEE material classes from the #96 detector to the real
thermo-physical parameters used by the per-selection temperature solve.
Every value traces to a published source - no invented numbers:

  material class    eps   alpha_solar  rho kg/m3  cp J/kgK  k W/mK   source
  ---------------   ----  ----------   ---------  -------  ------   ------
  metal (steel)     0.90  0.70         7850       490      50       Incropera; NASA TP-2005-212792
  metal (alum)      0.90  0.30         2700       900      205      NASA Z93 paint data
  glass             0.90  0.15         2500       840      1.1      Incropera
  rubber (tyre)     0.95  0.90         1314       1898     0.22     Guo et al. 2023; FLIR T505002
  plastic (ABS)     0.95  0.50         1040       1506     0.17     Thermtest; FLIR T505002
  concrete          0.92  0.60         2300       880      1.4      Incropera
  asphalt           0.88  0.90         2300       900      1.5      Li 2015; Hoehne (NSF); Kim & Lee 2024 (albedo 0.05-0.15)
  wood              0.88  0.60         700        1700     0.15     Incropera
  leather           0.78  0.50         1000       1500     0.18     FLIR T505002
  vegetation        0.98  0.60         300        2000     0.20     Incropera (foliage)
  water             0.96  0.10         1000       4186     0.60     Incropera
  rock              0.90  0.70         2600       850      2.0      Incropera
  ground (soil)     0.92  0.65         1600       1100     0.30     Incropera
  engine (cast iron)0.80  0.90         7200       500      50       Incropera
  ceramic (armour)  0.85  0.60         3900       880      32       DTIC ADA362926 (Al2O3)
  human (skin)      0.98  0.60         1100       3500     0.35     Steketee 1973; FLIR T505002

  Notes:
  - eps (emissivity, 0-1): LWIR 8-14 um band.  Painted surfaces all sit
    ~0.9 regardless of visible colour (FLIR T505002: Paint 8 colours
    0.88-0.96 SW, 0.92-0.94 LW) - colour matters in the SOLAR band, not
    the LWIR emission band.
  - alpha_solar: NASA TP-2005-212792 absorptance tables - Z93 white
    0.14-0.17, black 0.90-0.96.  The camo-colour classifier overrides
    this per texture source.
  - rho*cp/k sets the thermal time constant tau via the lumped-capacity
    model: tau = rho*cp*V/(h*A).  For a surface shell V/A ~ thickness t
    (0.001-0.01 m), tau = rho*cp*t/h.

Stored in GVAR(materialThermal) as class -> [eps, alpha, rho, cp, k].

Arguments:
  0: material class (STRING) - one of the #96 classes

Return Value:
  ARRAY [eps, alpha, rho, cp, k] - or the ground defaults for unknown
*/

params [["_class", "ground", [""]]];

if (isNil QGVAR(materialThermal)) then {
    GVAR(materialThermal) = createHashMapFromArray [
        ["metal",    [0.90, 0.70, 7850, 490,  50]],
        ["aluminium",[0.90, 0.30, 2700, 900, 205]],
        ["glass",    [0.90, 0.15, 2500, 840,  1.1]],
        ["rubber",   [0.95, 0.90, 1314, 1898, 0.22]],
        ["plastic",  [0.95, 0.50, 1040, 1506, 0.17]],
        ["concrete", [0.92, 0.60, 2300, 880,  1.4]],
        ["asphalt",  [0.88, 0.90, 2300, 900,  1.5]],
        ["wood",     [0.88, 0.60,  700, 1700, 0.15]],
        ["leather",  [0.78, 0.50, 1000, 1500, 0.18]],
        ["vegetation",[0.98, 0.60, 300, 2000, 0.20]],
        ["water",    [0.96, 0.10, 1000, 4186, 0.60]],
        ["rock",     [0.90, 0.70, 2600, 850,  2.0]],
        ["ground",   [0.92, 0.65, 1600, 1100, 0.30]],
        ["engine",   [0.80, 0.90, 7200, 500,  50]],
        ["ceramic",  [0.85, 0.60, 3900, 880,  32]],
        ["human",    [0.98, 0.60, 1100, 3500, 0.35]]
    ];
};

GVAR(materialThermal) getOrDefault [_class, [0.92, 0.65, 1600, 1100, 0.30]]
