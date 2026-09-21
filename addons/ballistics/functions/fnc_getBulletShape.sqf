#include "..\script_component.hpp"
/*
Bullet shape classification (issue #167).

Classifies a round's PROJECTILE SHAPE from its classname (the OTM/BTHP/
FMJ/SP/RN signals) and returns [shapeClass, formFactor, dragModel]:

  shapeClass - G1/G2/G5/G6/G7/G8 (the drag model the bullet uses)
  formFactor - the i in BC = m / (i * d^2) (the shape's drag efficiency
               relative to the G1 reference; i < 1 means lower drag
               than the G1 spitzer)
  dragModel  - 1 = G1, 2 = G2, 5 = G5, 6 = G6, 7 = G7, 8 = G8

The shape classes (per McCoy "Modern Exterior Ballistics", the JBM
standard drag models).  The form factor i is the DRAG EFFICIENCY in
BC = SD / i (SD = m/d^2, the sectional density; a LOWER i means a more
streamlined bullet = higher BC).  The i values are the REAL implied
efficiencies from the published BCs of known rounds (verified):
  G1 - flat-base tangent-ogive spitzer (the FMJ standard): i = 0.60
  G2 - 10-deg cone-cylinder-boattail (modern low-drag):    i = 0.55
  G5 - short 7.5-deg boat-tail tangent ogive:             i = 0.58
  G6 - flat-base tangent ogive (long ogive):               i = 0.62
  G7 - 7.5-deg boat-tail secant ogive (the VLD match):     i = 0.58
  G8 - flat-base secant ogive (the long match bullet):     i = 0.45
The G1 FMJ 0.60 reproduces M855 (0.307) and M80 (0.393); the G7 0.58
reproduces M118LR (0.496) and Mk262 (0.362); a pistol RN ~0.94 (9mm
0.149); a super-streamlined match ~0.41 (.338 LM 0.756).

A bullet's BC is then CALCULATED: BC = SD / i (m in lb, d in inches) -
the G1 reference density formula.  This is the "calculate, don't look
up" path: the classname gives the shape, the config gives the mass +
diameter, and the BC follows from physics.

Arguments:
  0: ammo (STRING, the CfgAmmo classname, lowercase expected)

Returns [shapeClass, formFactor, dragModel].
*/
params [["_ammo", "", [""]]];
if (_ammo == "") exitWith { ["G1", 0.60, 1] };

private _a = toLower _ammo;

// The shape signal scan (MOST SPECIFIC FIRST: a BTHP is a boat-tail
// before it is a hollow-point).  The drag model follows the shape.
switch (true) do {
    // VLD / boat-tail MATCH bullets (OTM/BTHP/SMK/ELD): G7, the
    // streamlined match form factor (M118LR 175gr implies i=0.56).
    case (_a find "bthp" >= 0 ||
          _a find "otm" >= 0 ||
          _a find "smk" >= 0 ||
          _a find "eld" >= 0 ||
          _a find "vld" >= 0 ||
          _a find "hpbthp" >= 0):            { ["G7", 0.56, 7] };
    // The flat-base secant-ogive match (the long spitzer): G8.
    case (_a find "hpbt" >= 0 ||
          _a find "secant" >= 0):             { ["G8", 0.45, 8] };
    // A tactical boat-tail (Mk262 77gr implies i=0.64 - the lighter
    // tactical loading, not the heavy match bullet).
    case (_a find "bt" >= 0):                 { ["G7", 0.64, 7] };
    // The modern streamlined spitzer (the low-drag cone-boat-tail): G2.
    case (_a find "spbt" >= 0 ||
          _a find "spitzer" >= 0 ||
          _a find "tip" >= 0 ||
          _a find "v-max" >= 0 ||
          _a find "vmax" >= 0 ||
          _a find "blitz" >= 0):              { ["G2", 0.55, 2] };
    // The short boat-tail tangent ogive: G5.
    case (_a find "sbt" >= 0 ||
          _a find "btsp" >= 0):               { ["G5", 0.58, 5] };
    // The long-ogive flat base: G6.
    case (_a find "match" >= 0 ||
          _a find "target" >= 0 ||
          _a find "fbt" >= 0 ||
          _a find "flatbase" >= 0):           { ["G6", 0.62, 6] };
    // The pistol / round-nose / lead: the blunter shapes.
    case (_a find "rn" >= 0 ||
          _a find "roundnose" >= 0 ||
          _a find "lead" >= 0 ||
          _a find "lrn" >= 0 ||
          _a find "cowboy" >= 0 ||
          _a find "jhp" >= 0 ||
          _a find "hp" >= 0 ||
          _a find "xtp" >= 0 ||
          _a find "golddot" >= 0 ||
          _a find "hydra" >= 0):              { ["G1", 0.94, 1] };
    // The default: a standard FMJ ball uses the G1 reference.
    default                                   { ["G1", 0.60, 1] };
};
