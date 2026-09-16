# ADR-002: Facts-Only Dynamic Biome Detection (no hardcoded map names)

Status: Accepted
Date: 2026-09-17
Decision: The biome system classifies a map from engine-exposed facts
(latitude, water fraction, surface textures, vegetation model paths,
structures, elevation) and never from a map-name table or a description
keyword.

## Context

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

## Consequences

- New maps classify correctly with zero config effort.
- The Koppen classification and the latitude physics are unit-tested
  against published climate references (test_biome_dynamic.py, 22
  tests).
- The map-rotation docker test asserts plausibility against the
  latitude band (validate_biome_plausible.py), never a name — the
  no-hardcoding contract is itself tested.
- The scan cost is one-time (cached in QGVAR(terrainSignals); the
  biome result is cached and re-read in microseconds).