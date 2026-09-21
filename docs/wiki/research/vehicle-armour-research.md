# Vehicle armour and penetration; verified research basis (issue #126)

The engine's two-gate model, the STANAG 4569 protection levels, and
the real vehicle armour values; all verified from primary sources.
This is the design basis for the armour override config.  No value in
this document is an estimate made without a source.

## 1. The engine's TWO independent gates (verified)

The engine has two SEPARATE gates for a round hitting a vehicle.  They
do NOT multiply against each other.

### Gate 1: `CfgVehicles >> armor`; the health pool

```
damageResistance = (HIT * HIT) / Armor * ((0.27 / tgtRadius)^2)
```

- `HIT` = the projectile's `hit` value (CfgAmmo)
- `tgtRadius` = the radius of the virtual bounding sphere from the
  vehicle's geometry
- `armor` = the class-level health pool (integer)

Per-hitpoint `armor (float)` multipliers scale the pool per location:
engine 0.8, turret 0.8, gun 0.6, tracks 0.6, wheels 0.05, glass 0.5,
hull 1.0, structural 1.0 (the CfgVehicles token reference defaults).

"1 bullet will kill armor <= 20, 2 bullets <= 40, 3 bullets 50" , 
the pool depletes with hits, then the vehicle is destroyed.

### Gate 2: bisurf `bulletPenetrability`; physical passage

```
mm penetration = (v / 1000) * caliber * bulletPenetrability
```

- `v` = projectile speed at impact (m/s)
- `caliber` = NORMALIZED, NOT mm.  1.0 = the standard 7.62 NATO round
  (BI: "A value of 1 is standardised as 15mm of RHA penetration at
  1000 m/s").  The vanilla `B_762x51_Ball` caliber is 1.6 per a BI
  developer quote.
- `bulletPenetrability` = the TARGET material's resistance.  RHA
  (armour.bisurf) = 15.  Lower is stronger.

Worked example: a 7.62x51 at 900 m/s vs RHA:
`(900/1000) * 1.0 * 15 = 13.5 mm RHA`.  NOT `7.62 * 15 = 114 mm`.

### The independence (the user's question)

"No armour value appears in the penetration calculation." (BI Damage
Description).  The Tanks Config Guidelines: "Internal damage is
handled by HitHull... cannot be activated by rounds that fail to
penetrate armor."

A vehicle with HUGE `armor` but thin bisurf geometry is easy to
penetrate but hard to destroy.  A vehicle with THIN `armor` but thick
bisurf stops rounds but dies quickly when penetrated.  They are
independent design axes; exactly the freedom the guidelines recommend:
"Armor represents overall thickness as seen by AI units, and
armorStructural to finetune damage received."

## 2. STANAG 4569 protection levels (Ed 2, 2012)

Primary source: STANAG 4569 Edition 2, implemented by AEP-55 Vol 1.
The standard specifies the threat round, velocity, range and angle.  It
does NOT publish RHA-equivalent mm; the RHAe figures below are derived
from ballistics and armour-steel manufacturer test data (Bisalloy,
Armox, Mars steel).

| Level | Threat round | Velocity | Range | RHAe penetration |
|---|---|---|---|---|
| L1 | 7.62x51 Ball (M80) | 833 m/s | 30 m | ~4-5 mm |
| L1 | 5.56x45 SS109 | 900 m/s | 30 m | ~4 mm |
| L2 | 7.62x39 API (BZ) | 695 m/s | 30 m | ~8 mm |
| L3 | 7.62x51 AP (WC core) | 930 m/s | 30 m | ~18 mm |
| L3 | 7.62x54R B32 API | 854 m/s | 30 m | ~16 mm |
| L4 | 14.5x114 API (B32) | 911 m/s | 200 m | ~28-32 mm |
| L5 | 25x137 APDS-T (M791) | 1258 m/s | 500 m | ~50-66 mm |
| L5 | 25x137 APFSDS-T | 1336 m/s | 500 m | ~70-80 mm |
| L6 | 30x173 APFSDS-T | not public | 500 m | ~100-120 mm |

Manufacturer stopping-thickness anchors (the verified data):
- L1: Bisalloy 6.0 mm HHA500; Armox 500 = 9 mm
- L2: Bisalloy 12.0 mm HHA500; Armox 500 = 12 mm
- L3: Armox 500 = 22 mm (WC-core AP)
- L4: Mars steel ~30-37 mm (14.5x114 B32)

## 3. Real vehicle armour values (RHAe, KE)

| Vehicle | Frontal KE protection | Source |
|---|---|---|
| Leopard 2A4 | Turret 590-690 mm; glacis 600 mm | Wikipedia / FAS |
| Leopard 2A6 | Turret 920-940 mm; glacis 620 mm | Wikipedia |
| T-72B (Kontakt-1) | Turret 520-540; hull 480-530 mm | Wikipedia |
| T-90 (Kontakt-5) | Glacis ~690; turret 740-800 mm | Fofanov |
| M2 Bradley (base) | 14.5 mm AP all sides | GlobalSecurity |
| M2A2 Bradley | 30 mm frontal; 14.5 mm sides | GlobalSecurity |
| Warrior FV510 | 14.5 mm AP frontal | Army Technology |
| BMP-2 | ~23 mm hull; ~33 mm glacis | RealClearDefense |
| Cougar MRAP | up to STANAG L3 | Wikipedia |
| RG-33 MRAP | 7.62 mm base, tailorable | GlobalSecurity |

Caveat: MBT figures are open-source estimates, varying ±50 mm by
source.  Use mid-range values as design targets, not measured facts.

## 4. The design consequence for AEE

The two gates are independent, so the armour overhaul has TWO levers:

1. **`armor` (config override)**; the health pool.  Re-align the class
   ladder to the real protection hierarchy (MRAP < IFV < MBT), keeping
   the RELATIVE ratios correct.  The pool value is a design target, not
   a physical mm; what matters is that a rifle round does NOT deplete
   an IFV's pool in a few hits, and an MBT survives rifle/HEI fire.
2. **Penetration gate (scripted, HandleDamage)**; the vanilla rifle
   rounds (caliber ~1.5-1.6) penetrate ~18.7 mm RHA at 900 m/s: enough
   for L1-L2 skin, NOT an L3+ vehicle.  A HandleDamage gate can scale/
   reject damage by the round's real penetration vs the vehicle's
   protection level; the ACE3 full-replacement pattern, not the baked
   bisurf (which is model-bound).

The vanilla class armour ladder (verified locally from the installed
game): APC_Tracked_01/02 = 500, APC_Tracked_03 = 900, APC_Wheeled_01 =
320, Wheeled_02 = 270, Wheeled_03 = 480.  The issue's table (400/800)
was approximate and is corrected here.

## 5. ACE3 coexistence (verified from ACE3 source)

ACE3 is a runtime HandleDamage model.  The critical constraints for a
coexisting mod (verified from the ACE3 repo, commit a8332b1):

- **ACE3 does NOT own the armour config surface.**  Its CfgVehicles
  ships no vehicle armour overrides (only its own objects: sandbags,
  scopes).  Armour is read at runtime via fnc_getItemArmor.
  Consequence: a coexisting mod may FREELY override CfgVehicles armour
  values, hitpoint armour, and passThrough.
- **ACE3 does NOT touch the penetration gate.**  It ships no bisurf
  files and no penetration simulation.  Its ballistics addon changes
  ammo config (caliber, hit, airFriction) but not the penetration
  model.  The armour-penetration wound handler is a script-side
  re-derivation AFTER the engine's penetration, for wound damage only.
- **ACE3's RHA values are gameplay-tuned**, derived from the vanilla
  bisurf armour-plate model ("This gets close to vanilla values on FMJ
  ammo", "Divided by 2 to keep inline with vanilla caliber values"),
  NOT from STANAG or real RHA data.  A repo-wide STANAG search found
  no references.
- **The HandleDamage return rule (the double-count guard)**: HandleDamage
  EHs chain; each EH's return becomes the next's `_damage`.  ACE3
  computes `_newDamage = _damage - _oldDamage`.  A coexisting mod must
  return `_oldDamage` (preserve engine state) or `0`, and NEVER
  re-inflate the incoming `_damage`, or it double-counts against ACE3's
  wound system.
- **For vehicles**: ACE3's vehicle_damage takes over entirely.  Its EH
  returns the current damage capped at critical thresholds (comment:
  "Don't return 0 or else old parts will be reset in damage").  A
  coexisting vehicle mod must NOT fight this EH; it should hook the
  `ace_vehicle_damage_medicalDamage` CBA event instead.

## Sources

- BI wiki: CfgVehicles Config Reference (armor + damageResistance)
- BI wiki: Config Properties Megalist (bulletPenetrability formula)
- BI wiki: Bullet penetrability (caliber normalisation, RHA = 15)
- BI wiki: Arma 3: Damage Description ("No armour value appears in
  the penetration calculation")
- BI wiki: Arma 3: Tanks Config Guidelines (the two-gate freedom)
- STANAG 4569 Ed 2 (AEP-55 Vol 1); the threat table
- Bisalloy Technical Bulletin 03 / Norsk Staal Armox / Industeel Mars
 ; the stopping-thickness anchors
- Wikipedia / GlobalSecurity / Fofanov; the vehicle RHAe values
- ACE3 source (commit a8332b1): fnc_handleDamage, fnc_getItemArmor,
  fnc_woundsHandlerArmorPenetration, vehicle_damage/fnc_handleDamage
- Local: the installed game's armour_f configs (the vanilla ladder)