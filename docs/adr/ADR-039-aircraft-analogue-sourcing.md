# ADR-039: Aircraft Analogue Sourcing for Fictional Classes

Status: Accepted
Date: 2026-10-10
Decision: A fictional Arma aircraft class binds to a real-world analogue at grade `claimed`. The catalogue entry the binding points to carries values only from held sources at grade `documented`. A family with no held analogue stays `no_source` with a reason that names the exact next source and its licence. The licence boundary admits US Government public-domain works, FAA and EASA type certificate data sheets, maker datasheets with the facts cited, and CC-BY-SA compilations for identity only.

## Context

The aircraft corpus reported 66 of its 139 roster classes as `no_source`. Every one is a fictional Arma 3 airframe. No published source names a fictional class, so the class-to-analogue link is always a claim. The corpus already holds the real figures for three of the nine affected families. The held OPFOR Worldwide Equipment Guide documents the Mil Mi-26, and the held ODIN Worldwide Equipment Guide 2025 documents the General Atomics MQ-9A and the CASC CH-5. The other six families have no held document and no single named analogue.

ADR-018 already records that the real-world mapping of a fictional Arma airframe to a real aircraft is a claim. This record extends that decision from the identity layer to the whole corpus, and it fixes the licence boundary and the rule for the entry values.

## Decision

1. The identity rule. A fictional Arma class never reaches grade `documented` for its identity. The binding cites a registered source at grade `claimed`. The binding source is `src_armedassault_wiki` (tier 5 compilation) when the community wiki names the analogue, else `aee_air_class_table` (tier 5 class table) with the concrete class token named in the evidence. The `identity_evidence` names the concrete game class, the real analogue, the judgement, and the held source that documents the analogue's figures.

2. The three bound families. Twenty-six class bindings are added to `data/aircraft/class_bindings.json`. `Heli_Transport_04` (16 classes) binds to the existing `mi26_halo` entry. `UAV_02` (9 classes) binds to a new `mq9a_reaper` entry. `UAV_04` (1 class) binds to a new `ch5_rainbow` entry. Every new binding is grade `claimed`. The 73 existing bindings are unchanged.

3. The entry values. The two new catalogue entries carry values only from held sources at grade `documented`. The `mi26_halo` entry is unchanged. The ODIN engine-power field for the MQ-9A is corrupt, so the entry writes no `rated_power_w` and no `net_power_kw`. The ODIN guide gives the CH-5 maximum takeoff weight as an approximate figure, so the entry writes no such weight. A held source that states no runtime-required figure gives an absent value, never an invented one.

4. The roster reasons. The three bound families leave `NO_SOURCE_FAMILIES`. The six remaining families (`UAV_01`, `UAV_03`, `UAV_05`, `UAV_06`, `VTOL_01`, `VTOL_02`) each keep a reason that names the exact next source and its licence. The `no_source` class count falls from 66 to 40.

5. The claimed-lead mechanism. A registered source may name a single analogue while no held source states its figures. A `claimed` binding may then point to a lead entry that holds no value and names its next source. This record states the mechanism. It does not apply the mechanism, because no registered source names a single analogue for the six remaining families.

6. The licence boundary. The allowed value sources are US Government public-domain works (TMs, FMs, TOs, the OPFOR and ODIN Worldwide Equipment Guides, DTIC and NASA reports), FAA and EASA type certificate data sheets, maker datasheets with the facts cited, and CC-BY-SA compilations for identity only. The forbidden sources are RHS (CC BY-NC-ND), CUP (APL-SA), Project Hatchet H-60 and BradMick HeliSim (APL-ND), and DCS, which is structure only and never a figure.

7. The work sits under JSP 945 configuration management and Def Stan 05-138 cyber security. The source registry, the digests, the validator, the freshness checks and this record are the configuration record. The corpus holds no secret and no personal data.

## Alternatives rejected

- A `documented` identity for a fictional class. Rejected: no published source names a fictional class, so the grade would be false.
- An invented analogue or an invented figure for the six remaining families. Rejected: the corpus holds no source for them, so they stay `no_source` with a named next source.
- A composite analogue for a family the wiki describes as a composite. Rejected: a composite is not a single real counterpart.
- A new engine config key. Rejected: every new identity is `claimed`, so the build-time predicate that emits a config key stays closed. No `CfgVehicles` key ships.
- A rebind of an already-bound class. Rejected: the 73 existing bindings stay byte-identical.

## Consequences

- The runtime lookup returns a sourced row for the `mi26_halo`, `mq9a_reaper` and `ch5_rainbow` catalogue ids.
- The 26 bound classes read `recorded` in the coverage artefact. The `no_source` class count falls from 66 to 40.
- The corpus holds 226 catalogue entries across 13 capture files, 99 class bindings, 99 recorded classes and 40 `no_source` classes.
- The six remaining families carry a reason that names a concrete next source and its licence, so a later worker has a starting point.
- No engine config key ships and `addons/vehicles/generated/CfgVehicles.hpp` is unchanged.

## References

- `data/aircraft/SCHEMA.md`, section 11, the fictional-class analogue rule.
- `data/aircraft/class_bindings.json`, the concrete binding layer.
- `data/aircraft/catalogue/mq9a_reaper.json` and `data/aircraft/catalogue/ch5_rainbow.json`, the two new entries.
- `data/aircraft/RESEARCH_GAPS.md`, the next-source notes.
- `tools/validation/gen_aircraft_roster.py`, the `NO_SOURCE_FAMILIES` reasons.
- `docs/adr/ADR-018-aircraft-catalogue.md`, the catalogue decision.
- `docs/adr/ADR-033-aircraft-systems.md`, the licence rule.
