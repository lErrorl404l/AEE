# AEE MIL-STD-2525 taxonomy marker attribution

The taxonomy markers (see `addons/symbology/config_taxonomy.hpp` and
`data/symbology/app6_taxonomy.json`) are function glyphs the pulled Commons
catalogue does not hold. They fill the missing subtrees (Military Intelligence,
Signal Unit, Administrative and Personnel, Equipment, Installation) and the Air,
Sea Surface, Subsurface and Space branches.

The geometry is the standard's own. MIL-STD-2525 is a US Government work and is
public domain. Each glyph is rendered from its SIDC by milsymbol:

- milsymbol 3.0.4, Copyright (c) 2017 Mans Beckman (www.spatialillusions.com)
- Licence: MIT. The full text is in `LICENCE-milsymbol.txt`.
- Source: https://github.com/spatialillusions/milsymbol

The AEE-rendered markers (mission tasks, modifiers, echelon overlays) are AEE's
own work under GPL-2.0-or-later. Their geometry comes from MIL-STD-2525D and FM
3-90 Appendix B, both public domain.

The catalogue markers keep their per-file attribution in `ATTRIBUTION.md`.
