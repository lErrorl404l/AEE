# ADR-018: Aircraft Catalogue and the Four Flight-Model Inputs

Status: Accepted
Date: 2026-10-06
Decision: AEE gains a second research corpus at `data/aircraft/`. It is a sibling of the vehicle corpus. It holds one sourced entry per real aircraft variant and projects four scalars to the flight model: mass, rated power, drag area and rotor disc area. A generated SQF lookup reads the corpus at build time. The kernel `fnc_calculateAirEngineLoad.sqf` is unchanged.

## Context

AEE's flight model consumes four scalars. `fnc_calculateAirEngineLoad.sqf` takes a mass, a rated power, a drag area and a rotor disc area. Three of the four were declared defaults: 150000 W, 0.7 m2 and 50 m2. No source backed them. The operator principle is full realism and no engine default left standing in for a real value.

The vehicle corpus already solves the same problem for ground vehicles. It has five layers: a class inventory, a source registry, one catalogue capture per held source, a class map and a generated runtime projection. The generator turns the corpus into an SQF table. A validator gates provenance before the build. A coverage guard reports the gaps. The aircraft corpus copies this contract by reference. It does not fork it. The loader gained a `Profile` so one read path serves both corpora.

A jet publishes thrust, a force, not power. The kernel has no thrust branch. A jet's engine is therefore a data problem, not a kernel problem.

The real-world mapping of a fictional Arma airframe to a real aircraft is a claim. No real-world source names the game classes. Every class binding therefore stays at grade `claimed`.

## Decision

1. The corpus is a sibling, not an extension. The aircraft type enum is `fixed_wing` and `rotary_wing`, stored under the loader key `vehicle_type`. The ground enum `wheeled` and `tracked` is not extended. An aircraft and a tank share no runtime field. A shared enum would force the ground couplings onto the airframes.

2. The runtime inputs are four. A `fixed_wing` entry needs `operating_weight_kg` and `rated_power_w`. A `rotary_wing` entry adds `rotor_disc_area_m2`. `drag_area_m2` is optional for a fixed-wing entry. The kernel default of 0.7 m2 stands when the corpus holds no value. Every other datasheet field is reference matter. It is documented and it has no consumer.

3. A jet's rated power is derived, not guessed. The corpus derives `rated_power_w = thrust_kn * 1000 * reference_speed_ms` at grade `derived`, and it states the formula in the value `state`. The derivation selects the jet formula when `thrust_kn` is held, the `net_power_kw * 1000` formula for a prop or rotor, and the `published_power_hp * 745.699872` formula last. The kernel keeps no thrust branch.

4. A figure whose only source is proprietary or unheld is committed at grade `claimed` with `primary_held: false` and a `state` that starts with `UNSOURCED`. It never fills a runtime-required field. Such an entry is a lead with a named next source in `RESEARCH_GAPS.md`.

5. The licence policy is facts only. A single performance figure is not copyrightable, so a derived spec is safe to commit. AEE vendors no proprietary document. Jane's and EUROCONTROL BADA are reference-only leads. OpenAP is a citation, never a vendored dependency or copied code. DTIC and NASA NTRS reports are public domain and may be held.

6. The work sits under JSP 945 configuration management and Def Stan 05-138 cyber security. The source registry, the SHA256 digests, the validator, the freshness checks and the ADR are the configuration record. The corpus holds no secret and no personal data.

7. The generated lookup feeds `fnc_applyExhaustShimmer.sqf`. The declared defaults remain the fallback. Without this wiring the corpus would be inert.

## Alternatives rejected

- A thrust branch in `fnc_calculateAirEngineLoad.sqf`. Rejected: the conversion is a one-line derivation in data, so the kernel stays a pure power model and the change stays data-only and headless-testable.
- A `wheeled | tracked | air` extension of the vehicle corpus. Rejected: the two corpora have different runtime sets, fields, derivations and coverage tokens. A shared enum would force the NRMM ground couplings onto aircraft.
- A separate PBO for the aircraft data. Rejected: no new engine code is needed. The corpus projects into the existing mobility addon, exactly as the vehicle corpus does.

## Consequences

- The three declared defaults lose their monopoly. A bound class reads a sourced mass, power and disc area. The defaults remain only as the empty-row fallback.
- A jet without a held reference speed is a lead, not a fabricated power. The corpus never invents a number.
- The first slice covers the vanilla air classes. A curated modern set and a historical set follow. A class that fails config verification is recorded as a mapping gap and does not block the slice.
- The vehicle corpus, its tests and its CI steps are unchanged.
