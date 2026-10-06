# Post-Process Template Reference

This note records the `CfgPostProcessTemplates` data. It states what the
engine does with a template, what AEE reads at run time, and a reference table
of the observed arrays. The arrays are design reference only. AEE ships none
of them.

## What the class is

`CfgPostProcessTemplates` is engine and terrain data. Each class holds a
`colorCorrections` array and an optional `filmGrain` array. The curator module
`ModulePostprocess_F` calls `BIS_fnc_modulePostprocess`. That function reads
the named template and applies it to the camera.

A template name is a menu entry in the curator module. The base game ships the
classes `Default`, `Survive`, `RealIsBrown`, `BlackAndWhite` and
`Mediterranean`.

## What AEE reads

ADR-014 reads one value at run time. AEE reads the class `Default` and its
`colorCorrections` element from `functions_f.pbo`. AEE keeps only the scalar
triple `[1, 1, 0]`, which is brightness 1, contrast 1 and offset 0. AEE caches
the read once per session. AEE falls back to `[1, 1, 0]` when the read fails.

AEE ships no template class and no template array. AEE defines no curator menu
preset. AEE can define its own template class if a later change needs one. AEE
cannot add a preset to the engine video menu.

## The array shape

A `colorCorrections` array holds seven elements in this order: brightness,
contrast, offset, the blend vector, the colorize vector, the weight vector and
the radial vector. The base-game `Default` array holds six elements and omits
the radial vector. The engine treats a missing radial vector as the default.

## Reference arrays

The arrays below come from the Post Process Effects mod (Workshop 656307117)
`ASCZ_Postprocess/config.cpp`. AEE records them as design reference only. AEE
copies no array.

Default and contrasted:

```
Default            {1,1,0,{0,0,0,0},{1,1,1,1},{0,0,0,0}}
Contrasted         {1,1,-0.15,{-0.15,-0.05,-0.1,-0.15},{1,1,1,0.9},{2,2,2,0},{0,0,0,0,0,0,4}}
```

Night filters:

```
Night Filter 1     {1,1.7,-0.13,{0.2,-0.05,0.05,-0.76},{1,1,1,0.78},{2.8,2,0.25,0},{0,0,0,0,0,0,4}}
Night Filter 2     {1,1.7,-0.13,{0.15,0,-0.05,-0.76},{1,1,1,0.78},{2.8,2,0.25,0},{0,0,0,0,0,0,4}}
Night Filter 3     {1,1.7,-0.13,{0,0,0.1,-0.76},{1,1,1,0.78},{2.8,2,0.25,0},{0,0,0,0,0,0,4}}
```

Movie effects:

```
Movie 1            {1,1.05,-0.25,{0.6,0.15,-0.05,-0.33},{1,1,1,0.8},{2,1,1,0},{0,0,0,0,0,0,4}}
Movie 2            {1,1.1,-0.2,{0.7,0,0,-0.45},{1.23,0.86,0.86,0.8},{3,0,0,0},{0,0,0,0,0,0,4}}
Movie 3            {1,1.1,-0.25,{0,0,0,-0.25},{0.95,1.05,1.05,0.8},{2,1,1,0},{0,0,0,0,0,0,4}}
Movie 4            {1,1.15,-0.3,{-0.2,0,0.5,0.06},{1,0.9,0.7,0.85},{6.14,0.71,2.22,0},{0,0,0,0,0,0,4}}
Movie 5            {1,1.05,-0.25,{2.97,1.76,1.61,-0.08},{0.95,0.95,0.9,0.35},{2.5,2.5,-3,0},{0,0,0,0,0,0,4}}
```

Operation Arrowhead presets:

```
Back Stab          {1.0,1.0,-0.01,{0.7,0.7,1.0,0.005},{1.0,0.5,0.5,0.70},{0.95,0.95,0.95,0.0}}
Good Morning       {1,1.02,-0.005,{0.0,0.0,0.0,0.0},{1,1,0.7,0.65},{0.199,0.587,0.114,0.0}}
Sand Storm         {1,1,0,{0.0,0.0,0.0,0.0},{0.0,0.5,1.0,0.5},{0.5,0.5,0.5,0.0}}
Finishing Touch    {1.0,1.0,-0.02,{0.9,0.1,0.9,-0.01},{1.0,1.0,1.0,1.0},{1.0,1.0,1.0,1.0}}
Dum Spiro Spero    {1,1.1,-0.003,{0.0,0.0,0.0,0.0},{1.0,0.8,0.6,0.64},{0.199,0.587,0.114,0.0}}
Jackal             {1,1.02,0,{0.0,0.0,0.0,0.0},{0.6,0.6,1.0,0.7},{0.199,0.587,0.114,0.0}}
One Shot One Kill  {1,1.2,-0.00,{0.0,0.0,0.0,0.0},{0.6,0.6,1.0,0.4},{0.199,0.587,0.114,0.0}}
```

The Operation Arrowhead arrays hold six elements. They omit the radial vector.
The engine treats the omitted vector as the default.

## The menu ceiling

A mod can declare a template class. A mod can also re-declare the curator
module and extend its template list. The Post Process Effects mod does exactly
that. AEE does neither in this plan. AEE cannot add a preset to the engine
video menu. That menu is engine UI data, not mod config.

## Guardrail

AEE must not add a `CfgPostProcessTemplates` block. The precise check is:

```
grep -rn "class CfgPostProcessTemplates" addons/
```

The command returns nothing. A plain `grep -r "CfgPostProcessTemplates"
addons/` is not empty. That command also finds comments and one run-time read
in the ADR-014 anchor path `fnc_applyBaseGrade.sqf`. The read gets the
base-game config. It is not a block and it ships no template data.

## Sources

- Post Process Effects, Workshop 656307117, `ASCZ_Postprocess/config.cpp`: the
  observed arrays and the extended curator list.
- `functions_f.pbo`, class `CfgPostProcessTemplates`: the base-game classes and
  the `Default` array.
- ADR-014: the run-time read of `Default >> colorCorrections` and the `[1, 1, 0]`
  anchor.
- `image-realism-optics-catalogue.md`: the scriptable post-process set.
