#include "..\..\script_component.hpp"
/*
Per-selection thermal material registry (issue #124).

Maps the AEE material classes from the #96 detector to the real
thermo-physical parameters used by the per-selection temperature solve.
Every value traces to a published source - no invented numbers:

  material class    eps   alpha_solar  rho kg/m3  cp J/kgK  k W/mK   phi    source
  ---------------   ----  ----------   ---------  -------  ------   -----  ------
  metal (steel)     0.90  0.70         7850       490      50       0.00   Incropera; NASA TP-2005-212792
  aluminium (bare)  0.05  0.30         2700       900      205      0.00   FLIR T505002 (alum sheet LW 0.03-0.06)
  aluminium (paint) 0.90  0.30         2700       900      205      0.00   NASA Z93 paint data
  glass             0.90  0.15         2500       840      1.1      0.00   Incropera
  rubber (tyre)     0.95  0.90         1314       1898     0.22     0.00   Guo et al. 2023; FLIR T505002
  plastic (ABS)     0.95  0.50         1040       1506     0.17     0.00   Thermtest; FLIR T505002
  concrete          0.92  0.60         2300       880      1.4      0.12   Incropera; Neville (10-15%)
  asphalt           0.88  0.90         2300       900      1.5      0.06   Li 2015; Asphalt Inst. MS-2 (4-8%)
  wood              0.88  0.60         700        1700     0.15     0.53   Incropera; Siau 1984
  leather           0.78  0.50         1000       1500     0.18     0.00   FLIR T505002 (tanned, 0.75-0.80 T)
  vegetation        0.98  0.60         300        2000     0.20     0.90   Incropera (foliage); Bonan 2019
  water             0.96  0.10         1000       4186     0.60     0.00   Incropera
  rock              0.90  0.70         2600       850      2.0      0.05   Incropera; Freeze & Cherry 1979
  ground (soil)     0.92  0.65         1600       1100     0.30     0.40   Incropera; Rawls et al. 1982
  engine (cast iron)0.80  0.90         7200       500      50       0.00   Incropera
  ceramic (armour)  0.85  0.60         3900       880      32       0.00   DTIC ADA362926 (Al2O3)
  human (skin)      0.98  0.60         1100       3500     0.35     0.00   Steketee 1973; FLIR T505002

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
  - phi (porosity, 0-1): the Johansen 1975 Kersten number is a function of
    the degree of saturation Sr = theta / phi, so the soil node stack needs
    phi.  Only porous media carry a non-zero value.  Soil 0.40 is derived as
    1 - rho_bulk/rho_particle = 1 - 1600/2650, and Rawls, Brakensiek &
    Saxton 1982 (Trans. ASAE 25:1316-1320) put loam total porosity at
    0.40-0.46.  Compacted asphalt 0.06 is the 4-8% air-void band (Asphalt
    Institute MS-2).  Concrete 0.12 is the 10-15% total porosity (Neville,
    Properties of Concrete).  Wood 0.53 is 1 - rho/cell-wall density =
    1 - 700/1500 (Siau 1984).  Rock 0.05 is representative intact rock
    (Freeze & Cherry 1979: sedimentary 0.1-0.2, crystalline near 0).
    Vegetation 0.90 is the canopy void fraction (Bonan 2019).  Classes that
    are not porous media (metal, aluminium, glass, rubber, plastic, leather,
    water, engine, ceramic, human) carry 0.00; they are object skins, not
    soil columns.

Stored in GVAR(materialThermal) as class -> [eps, alpha, rho, cp, k, phi].

Arguments:
  0: material class (STRING) - one of the #96 classes

Return Value:
  ARRAY [eps, alpha, rho, cp, k, phi] - or the ground defaults for unknown
*/

params [["_class", "ground", [""]]];

if (isNil QGVAR(materialThermal)) then {
    GVAR(materialThermal) = createHashMapFromArray [
        ["metal",    [0.90, 0.70, 7850, 490,  50, 0.00]],
        ["aluminium",[0.05, 0.30, 2700, 900, 205, 0.00]],
        ["aluminium_painted",[0.90, 0.30, 2700, 900, 205, 0.00]],
        ["glass",    [0.90, 0.15, 2500, 840,  1.1, 0.00]],
        ["rubber",   [0.95, 0.90, 1314, 1898, 0.22, 0.00]],
        ["plastic",  [0.95, 0.50, 1040, 1506, 0.17, 0.00]],
        ["concrete", [0.92, 0.60, 2300, 880,  1.4, 0.12]],
        ["asphalt",  [0.88, 0.90, 2300, 900,  1.5, 0.06]],
        ["wood",     [0.88, 0.60,  700, 1700, 0.15, 0.53]],
        ["leather",  [0.78, 0.50, 1000, 1500, 0.18, 0.00]],
        ["vegetation",[0.98, 0.60, 300, 2000, 0.20, 0.90]],
        ["water",    [0.96, 0.10, 1000, 4186, 0.60, 0.00]],
        ["rock",     [0.90, 0.70, 2600, 850,  2.0, 0.05]],
        ["ground",   [0.92, 0.65, 1600, 1100, 0.30, 0.40]],
        ["engine",   [0.80, 0.90, 7200, 500,  50, 0.00]],
        ["ceramic",  [0.85, 0.60, 3900, 880,  32, 0.00]],
        ["human",    [0.98, 0.60, 1100, 3500, 0.35, 0.00]]
    ];
};

GVAR(materialThermal) getOrDefault [_class, [0.92, 0.65, 1600, 1100, 0.30, 0.40]]
