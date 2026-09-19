# ADR-002: Facts-Only Dynamic Biome Detection (no hardcoded map names)

Status: Accepted
Date: 2026-09-17
Decision: The biome system classifies a map from engine-exposed facts
(latitude, water fraction, surface textures, vegetation model paths,
structures, elevation) and never from a map-name table or a description
keyword.

## Context

This ADR builds on the engine-anchor convention of [ADR-001](ADR-001-engine-anchors.md):
the biome is derived from engine-exposed facts, and the terrain
refinement is applied through the confidence gate defined here.

Issue #123 exposed three hardcoded-assumption defects in the released
code. The most brittle was the biome system: a hardcoded table of 17 map
names mapped each known world to a biome, and a description-keyword
fallback guessed unknown maps. On the Scottish Highlands map (oski_corran)
the lookup missed, the latitude vote produced a wrong Dfb biome, and a
negative latitude in the solar model inverted the seasons — the player
froze.

The hardcoded table fails against arbitrary Workshop content by design:
a new map is an unknown name, and its biome is a fact of its terrain and
position, not its label.

## Decision

1. The biome is a weighted fusion of facts, all readable at runtime:
   - **Latitude climate** (CfgWorlds latitude, abs-corrected): a
     12-month climatology (mean 27 - 0.42*|lat|, continental amplitude,
     maritime moderation by water fraction, hemisphere peak month)
     classified by the real Koppen rules. Weight 10.
   - **Terrain signals** (one-time map scan): surface textures (the
     map's own CfgSurfaces entries), vegetation model paths (t_palm.p3d
     is a palm whatever its class), structure model paths, water
     fraction, mean elevation. Weights 8/4/3.
   - **Elevation override**: mean > 1500 m shifts toward Dfc/ET.

2. No map name, no CfgWorlds description keyword, no special case. A
   map works "because the system reads its facts".

3. The module/EDEN override is retained as the explicit user escape
   hatch.

4. The terrain refinement is confidence-gated (peak-to-sidelobe): the
   winner must clear the runner-up by the ratio 1.4, else the system
   ABSTAINS and the climate anchor holds.  This is the position-fixing
   doctrine of TERCOM/DSMAC (a terrain match is accepted only when
   unambiguous; an ambiguous match is discarded, never forced) and the
   Kalman innovation gate / RAIM (a measurement is accepted only when
   its normalised residual passes the chi-square threshold; a failing
   measurement is rejected).  The terrain never has an override path
   against a weak match.

## Doctrine Basis

The design is not novel - it is the established military method for
deriving environment from position plus observable terrain:

- **AR 70-38** (US Army Research, Development and Acquisition of
  Materiel; worldwide use of materiel) tabulates 19 Military Operating
  Environments built "based primarily upon the Koppen (1931) and
  Trewartha (1968) climate classifications", each with 22 factor
  values (atmospheric, terrain, biological).  The Koppen climate is the
  top anchor; terrain and vegetation refine within it.  AEE follows the
  same hierarchy (climate weight 10, vegetation 8, surface 4, structure
  3, elevation 15 for high terrain).
- **ATP 2-01.3** (Intelligence Preparation of the Battlefield, 2019)
  describes terrain analysis as an overlay ON the environmental basis,
  not a replacement for it.
- **TERCOM/DSMAC** (Tomahawk terrain contour matching): INS/coordinates
  are authoritative; terrain matching is a position-fixing aid that
  refines within the constraint of the primary solution, only when the
  match is unambiguous (peak-to-sidelobe ratio gate, else abstain).
- **Kalman innovation gate / RAIM**: a measurement is fused only when
  its residual passes the gate; a failing measurement is rejected,
  never forced.  There is NO override path.

The fusion confidence gate in this ADR is the direct application of
the last two: terrain refines only when it unambiguously clears the
alternatives.

## Consequences

- New maps classify correctly with zero config effort.
- The Koppen classification and the latitude physics are unit-tested
  against published climate references (test_biome_dynamic.py, 36
  tests, including the Hadley-cell desert belt and the fusion gate).
- The map-rotation docker test asserts plausibility against the
  latitude band (validate_biome_plausible.py), never a name — the
  no-hardcoding contract is itself tested.
- The scan cost is one-time (cached in QGVAR(terrainSignals); the
  biome result is cached and re-read in microseconds).
- An ambiguous terrain match leaves the climate verdict in place: the
  system abstains rather than guessing (the "reject, never override"
  rule).