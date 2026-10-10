# Software Requirements Specification

This specification states what AEE must do. It is the requirements baseline
for the software CIs named in `docs/cmp.md` section 2.

Every requirement traces to a source. A source is an ADR under `docs/adr/`,
an issue, a standard, or a published reference. A requirement with no source
is marked UNKNOWN. The specification invents no requirement.

## 1. Scope

AEE is an Arma 3 mod. It extends the environment simulation of ACE3. It
simulates atmosphere, weather, thermal state, optics, acoustics, mobility,
physiology, and the map. It runs on the Arma 3 engine. The engine keeps the
solver, the renderer, and the physics step (ADR-017, ADR-034).

The mod is a set of addons. Each addon is one Configuration Item. The addon
set is in `docs/architecture/addon-map.json`.

## 2. Applicable documents

| Document | Holds |
|---|---|
| `docs/adr/` | The settled design decisions. ADR-001 to ADR-037. |
| `docs/engine/` | What the engine does, and what a mod can override. |
| `docs/architecture/addon-dependencies.md` | The addon graph, generated from the source. |
| `docs/icd/` | The variable contract at each addon boundary. |
| `data/vehicle/SCHEMA.md`, `data/aircraft/SCHEMA.md` | The vehicle data contracts. |
| JSP 939 | Defence Policy for Modelling and Simulation. The VV&A practice. |
| JSP 945 | MOD Policy for Configuration Management. |

## 3. Definitions

- A producer is the addon that owns a variable. It writes the variable.
- A consumer is the addon that reads the variable.
- A published variable is a variable a consumer may read across an addon
  boundary.
- Verification checks the code against a published formula. Validation
  checks the output against an independent oracle. `docs/vv-a.md` states
  the difference.

## 4. Requirements

### 4.1 Atmosphere and weather

| Requirement | Source |
|---|---|
| The mod computes air temperature with a height lapse rate. | ADR-016, ADR-019 |
| The mod classifies each map into a Koppen biome from first principles. It uses no per-map name table. | ADR-002, issue #123 |
| The mod derives the seasonal solar curve from the absolute world latitude. | ADR-002, issue #178 |
| The mod computes barometric pressure, humidity, and air density at the player position. | ADR-016 |
| The mod models orographic precipitation, haze, cloud, and turbulence. | `docs/wiki/chapters/modules.qmd` (atmos) |
| The mod models hail, lightning, and microbursts. | `docs/wiki/chapters/modules.qmd` (atmos) |

### 4.2 Thermal state

| Requirement | Source |
|---|---|
| The mod computes surface, air, and water temperature, and the wet bulb globe temperature. | ADR-019 |
| The mod computes wind chill, frostbite time, and manual dexterity. | ADR-019 |
| The mod models thermal crossover and the thermal contrast a sensor sees. | ADR-019, ADR-006 |
| The mod computes the Stefan coefficient from the soil property, in `material`. | ADR-019, issue #203 |

### 4.3 Optics, vision, and night vision

| Requirement | Source |
|---|---|
| The mod couples the thermal sensor to the optics. | ADR-006 |
| The mod owns eye adaptation, and publishes the adapted luminance. | ADR-007, ADR-014 |
| The mod models NVG imperfection, not a clean gain. | ADR-009 |
| The mod grades the image realism against a base grade. | ADR-010 |
| The mod computes the view distance from the sensor and the weather. | ADR-020 |

### 4.4 Ballistics and weapons

| Requirement | Source |
|---|---|
| The mod uses verified ballistics data. Each value carries a source. | ADR-003 |
| The mod models recoil and item mass. | ADR-004 |
| The mod models carried load and item mass. | ADR-005 |
| The mod models barrel temperature and propellant temperature. | `docs/wiki/chapters/modules.qmd` (ballistics) |

### 4.5 Mobility and vehicles

| Requirement | Source |
|---|---|
| The mod models ground friction, soil strength, and terrain drag. | ADR-037 |
| The mod uses the PhysX mass surface and a build-time grade gate. | ADR-037 |
| The mod computes land and aircraft systems from one shared pipeline. | ADR-033, `docs/architecture/vehicle-systems-pipeline.md` |
| The mod derives vehicle mass from the class binding. | ADR-037, issue #203 |

### 4.6 Physiology and survival

| Requirement | Source |
|---|---|
| The mod models altitude hypoxia, dive state, and strain. | `docs/wiki/chapters/modules.qmd` (physiology) |
| The mod models cold-weather exposure and clothing insulation. | ADR-019 |

### 4.7 Acoustics and radio

| Requirement | Source |
|---|---|
| The mod computes atmospheric sound absorption. | issue #80, `validate_oracles.py` |
| The mod computes radio refraction from the atmospheric gradient. | issue #12 |

### 4.8 AI and wildlife

| Requirement | Source |
|---|---|
| The wildlife addon consumes the AI addon. The reverse never holds. | ADR-021, issue #203 |
| The mod models wildlife ecology and ambience. | ADR-013, ADR-021 |
| The mod feeds AI perception from the published environment state. | ADR-020 |

### 4.9 Map and symbology

| Requirement | Source |
|---|---|
| The mod publishes MGRS position from one source. | ADR-022 |
| The mod derives map markers from the engine config. | ADR-029 |
| The mod uses the NATO and APP-6 symbology taxonomy. | ADR-023, ADR-024 |
| The mod tracks live markers. | ADR-025 |

### 4.10 Framework and settings

| Requirement | Source |
|---|---|
| Every addon publishes its settings under one taxonomy. | ADR-012 |
| The mod declares each cross-addon call in `requiredAddons[]`. | ADR-032 |
| The mod runs a conformance layer that detects and repairs a drift. | ADR-031 |
| The mod runs a native kernel with an SQF fallback. | ADR-036 |
| The mod exposes an observability console that reports evidence. | ADR-020, ADR-035 |
| Every nightly build runs the headless regression. | ADR-011 |

## 5. External interfaces

The interface between two addons is a variable contract. The contracts are
in `docs/icd/`. Each contract names the producer, the consumer, the
variables, and the direction.

The mod interface to the engine is in `docs/engine/`. A config change reads
the engine source first (ADR-001).

## 6. Traceability

A requirement traces forward to a test. The test suites are in
`tools/tests/`. The verification and validation scripts are in
`tools/validation/`. The Software Test Plan names the levels. The
Verification, Validation and Accreditation record names the evidence.

A requirement with no test is a gap. The gap is recorded, not hidden.
