# ADR-001: Engine Anchors as the Substrate for All Dynamic Simulation

Status: Accepted
Date: 2026-09-16
Decision: Adopt the engine-anchor architecture as the default design convention for every dynamic simulation in AEE.

## Context

The Real Virtuality engine is a simulator. It exposes anchors throughout: named model selections, hitpoints (fixed model positions), memory points, pilot positions, attachment points, and config inheritance. The engine renders the world from these anchors and gives scripted access to them (`selectionNames`, `getObjectTextures`, `getObjectMaterials`, `setObjectMaterial`, `selectionPosition`, `modelToWorld`, `getHitPointDamage`).

Research across thermal, armour, materials, and vehicles repeatedly found the same pattern: a native command has a limit (three thermal slots, whole-model heat, no terrain material command), and the limit looks like a wall until the anchors underneath are used. The engine exposes the capability; AEE only needs to use it.

## Decision

1. Every dynamic simulation maps its state onto engine anchors — named selections, hitpoints, or memory points — and drives effects through them. Example: per-wheel heat is not "impossible because setVehicleTIPars has three slots"; it is "our wheel-heat model maps to the wheel's selection index and swaps that selection's material".

2. "Impossible" is declared only after exhausting all three override mechanisms in order:
   - **PBO path override**: ship replacement .paa/.rvmat at vanilla paths (last-loaded wins, `requiredAddons` guarantees priority)
   - **Config override**: class inheritance adds/changes materials, values, surfaces for known classes without touching models
   - **Runtime anchors**: setObjectMaterial / setObjectTexture / selection positions per anchor

3. The engine's native limits are workarounds, not walls. Where the engine lacks a command (per-component thermal), AEE simulates the component physics itself and applies it through the nearest anchor.

4. Anchor mapping is cached per class (selection-name lists) and applied one-shot on state change, never per-frame — the existing throttled-swap pattern.

## The Three Mechanisms (each verified by research)

| Mechanism | What it controls | Example |
|---|---|---|
| PBO path override | Baked textures, terrain layers, default TI | Replace `A3\data_f\default.rvmat` → every fallback object (last-loaded wins) |
| Config override | Materials for known classes | `class Land_Rock_01_F : Land_Rock_01_F { hiddenSelectionsMaterials[] = { ... }; }` |
| Runtime anchors | Per-component state | Wheel heat model → that wheel's selection index → `setObjectMaterial [_selIdx, _material]` |

The runtime-anchor row is proven in the shipped code (`setObjectMaterial`
in `fnc_applyWeaponBarrelHeat`, `fnc_applyBuildingThermal`). The PBO
path and config rows are the replacement-material mechanisms the
material library (#124) and baked-control (#128) work ship through.

## Consequences

- **Good**: Full control of baked textures (rocks, buildings, terrain) via path override; per-component vehicle behaviour via selection anchors; zero per-mod compat for appearance/thermal (the baseline-requirement goal).
- **Cost**: Each feature must research the model's actual selection names; some objects have sparse selections.
- **Risk**: Per-selection swaps can corrupt visible appearance if applied to the wrong material (the Zulu uniform bug, #123) — the classification fix (from #96) must feed the swap target.
- **Documented limits** (genuine, not convention): per-pixel temperature, GDT surface mask at runtime, glass TI reflections (custom model), the thermal pass renderer itself.

## References

- #96 universal material detection (classification feeding the swaps)
- #124 rvmat material library (the materials to ship)
- #126 armour and penetration (hitpoints as damage anchors)
- #128 baked texture and per-component control (the three mechanisms + anchor architecture)
- #123 the Zulu camo bug (the risk this convention must guard)

## Notes

This ADR is the design convention for the whole mod, not a single feature. Future feature work should reference it when defining how a simulation reaches the rendered/behaved world.