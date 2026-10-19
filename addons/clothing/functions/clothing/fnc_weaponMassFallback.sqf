#include "..\..\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_weapon_mass_fallback.py

Weapon-mass fallback by classname family.

fnc_getWeaponMass returns the maker's published mass whenever the weapon
catalogue identifies the classname.  This table is only reached when it does
not, and every figure in it is the MEDIAN of the measured masses the corpus
(data/ballistics/weapons.json) already holds for that family, so the fallback
invents nothing.

A weapon joins a family by its chambering where the chambering defines the
family, and by its model name where it does not (a belt-fed machine gun and a
submachine gun share cartridges with other families).

Per-family sample, from 426 corpus weapons carrying a published mass:
  carbine       109 weapons, median 3.54 kg
  dmr            68 weapons, median 4.3 kg
  machinegun_light    8 weapons, median 7.6 kg
  machinegun_medium    2 weapons, median 9.88 kg
  pistol        163 weapons, median 0.79 kg
  revolver       11 weapons, median 0.992 kg
  shotgun         2 weapons, median 3.04 kg
  smg            12 weapons, median 2.88 kg
  sniper         14 weapons, median 6.35 kg

A classname matching no family takes the all-weapon median, 2.97 kg.

Returns: ARRAY of [keyword, massKg] rows, most specific family first, and the
         all-weapon median as the last element.
*/

[
    [
        ["srifle", 6.35],   // sniper: median of 14 published masses
        ["sniper", 6.35],   // sniper: median of 14 published masses
        ["dmr", 4.3],   // dmr: median of 68 published masses
        ["lmg", 7.6],   // machinegun_light: median of 8 published masses
        ["saw", 7.6],   // machinegun_light: median of 8 published masses
        ["mmg", 9.88],   // machinegun_medium: median of 2 published masses
        ["machinegun", 9.88],   // machinegun_medium: median of 2 published masses
        ["smg", 2.88],   // smg: median of 12 published masses
        ["pdw", 2.88],   // smg: median of 12 published masses
        ["revolver", 0.992],   // revolver: median of 11 published masses
        ["hgun", 0.79],   // pistol: median of 163 published masses
        ["pistol", 0.79],   // pistol: median of 163 published masses
        ["shotgun", 3.04],   // shotgun: median of 2 published masses
        ["carbine", 3.54],   // carbine: median of 109 published masses
        ["arifle", 3.54]    // carbine: median of 109 published masses
    ],
    2.97
]
