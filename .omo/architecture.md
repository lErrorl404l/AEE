# AEE Architecture (superseded)

> Status: historical design record. The README.md is the authoritative
> description of the current structure. This document predates the modular
> restructure and its naming (aee_aee_core_*, the ACE3 variable bridge)
> no longer applies.

# AEE (Ace Environment Extension) — Architecture Plan

**Status**: Planning phase  
**Date**: 2026-07-24  
**Project root**: `/ext/Development/aee/`

---

## 1. The Problem

ACE3 Weather provides a static climate model: monthly normals + diurnal curve + random Gaussian shifts. It does not model:
- Elevation lapse rate (a player at 2000m gets sea-level temperature)
- Terrain microclimate (north slope vs south slope)
- True air density from temperature + pressure + humidity
- Dynamic weather changes within a mission beyond wind
- Biome differentiation beyond monthly normals (maps without entries get Mediterranean defaults)

**The result**: At 600m on a 2000m mountain, Arma applies drag as if air density is 1.225 kg/m³. Actual density is ~1.007 kg/m³ — an **18% error** in the drag model. That's ~1.2 MOA of phantom bullet drop the game incorrectly applies.

---

## 2. Architecture Overview

```
ACE3 Weather (if present)         AEE (server only)
│                                │
│ ace_weather_currentTemp ───────┤── reads ACE3 data as baseline
│ ace_weather_currentOvercast    │
│                                │
│         ┌──────────────────────────────────────────┐
│         │   aee_core  (main module)                │
│         │                                          │
│         │  fn_init.sqf ── biome detection ──────┐  │
│         │                    ├─ worldName        │  │
│         │                    ├─ CfgWorlds        │  │
│         │                    └─ fallback chain   │  │
│         │                                          │
│         │  fn_getBiome.sqf ─── Köppen class ───────┤── CfgWorlds
│         │                    ├─ map→biome table     │── CBA override
│         │                    └─ climate ref data    │
│         │                                          │
│         │  fn_updateEnvironment.sqf (every 10s)    │
│         │    ├─ fn_updateTemperature.sqf       │   │
│         │    │   biome T_normals →              │   │
│         │    │   diurnal interpolation →        │   │
│         │    │   elevation lapse →              │   │
│         │    │   overcast modifier →            │   │
│         │    │   ace_weather_currentTemperature  │   │
│         │    │                                   │   │
│         │    ├─ fn_updateBarometricPressure.sqf  │   │
│         │    │   sea-level P →                   │   │
│         │    │   elevation correction →          │   │
│         │    │   ace_weather_currentPressure     │   │
│         │    │                                   │   │
│         │    ├─ fn_updateHumidity.sqf            │   │
│         │    │   biome norms →                   │   │
│         │    │   rain/overcast modifier →        │   │
│         │    │   ace_weather_currentHumidity     │   │
│         │    │                                   │   │
│         │    └─ fn_updateWind.sqf                │   │
│         │        (reuse ACE3 wind or replace)    │   │
│         │                                        │   │
│         │  fn_calculateAirDensity.sqf ───────────┤── ballistic extension
│         │    ρ = P / (R_d · T_v)                 │
│         │    T_v = T / (1 - 0.378·e/P)           │
│         │                                        │
│         │  a3db integration (optional):           │
│         │    climate_biomes table                  │
│         │    map_climates table                    │
│         └──────────────────────────────────────────┘
                                │
                                │ publicVariable
                                ▼
                ACE3 downstream consumers
        (advanced_ballistics, medical_vitals,
         kestrel4500, xm157, artillerytables)
```

### Data Flow

```
Every 10 seconds (server only):

  1. Read worldName → CfgWorlds → Köppen class
  2. Look up biome climate normals (temp, humidity, pressure)
  3. Interpolate diurnal curve from day/night normals + time of day
  4. Apply elevation correction using ATLtoASL at player/reference position
  5. Apply overcast modifiers
  6. Compute air density
  7. Set ace_weather_* missionNamespace variables
  8. publicVariable to clients
```

---

## 3. Project Structure (Mirrors ABE Conventions)

```
/ext/Development/aee/
├── mod.cpp
├── meta.cpp
├── .hemtt/
│   ├── project.toml
│   └── lints.toml
├── addons/
│   ├── main/                          # Bootstrapper
│   │   ├── $PBOPREFIX$                # "z\aee\addons\main"
│   │   ├── config.cpp                 # CfgPatches for aee_main
│   │   ├── script_mod.hpp             # PREFIX=aee, MAINPREFIX=z
│   │   ├── script_version.hpp         # MAJOR=0 MINOR=1 PATCHLVL=0
│   │   ├── script_macros.hpp          # QUOTE, DOUBLES, FUNC, GVAR
│   │   └── CBA_settings.sqf           # Legacy settings file
│   │
│   ├── aee_core/                      # Main environment module
│   │   ├── $PBOPREFIX$                # "z\aee\addons\aee_core"
│   │   ├── config.cpp                 # CfgPatches + CfgFunctions + base classes
│   │   ├── script_component.hpp       # COMPONENT=aee_core
│   │   ├── fn_init.sqf                # Server init, PFH registration
│   │   ├── fn_getBiome.sqf            # CfgWorlds → Köppen class
│   │   ├── fn_getClimateNormals.sqf   # Köppen → temp/pressure/humidity tables
│   │   ├── fn_updateTemperature.sqf   # Diurnal + elevation + overcast
│   │   ├── fn_updatePressure.sqf      # Sea-level → elevation correction
│   │   ├── fn_updateHumidity.sqf      # Biome + rain modifier
│   │   ├── fn_updateWind.sqf          # (optional) Wind replacement
│   │   ├── fn_updateEnvironment.sqf   # Orchestrator: runs all updates
│   │   ├── fn_calculateAirDensity.sqf # ρ = P/(R·T_v) with humidity
│   │   └── fn_diagnostic.sqf          # /dev/console reporting
│   │
│   └── aee_ace3_compat/               # ACE3 integration (optional component)
│       ├── $PBOPREFIX$
│       ├── config.cpp
│       └── script_component.hpp
```

---

## 4. Biome System

### Köppen Classification — AEE's Biome Taxonomy

AEE maps every Arma worldName to a Köppen class. Climate normals are defined per class, not per map. This means any map works — even custom ones — as long as the biome is identifiable.

**Direct approaches (tried in order):**

| Approach | Method | Works for |
|----------|--------|-----------|
| **CfgWorlds >> world >> description** | String match: "tropical", "desert", "temperate" | Maps with descriptive class entries |
| **CfgWorlds >> world >> ACE_TempDay** | Already has ACE3 data → infer biome | ACE3-compatible maps |
| **worldName hardcode** | Known maps → known biome | All major Arma maps |
| **CBA setting override** | `aee_biome = "Csa"` | Custom maps, mission maker preference |
| **Latitude heuristic** | `worldName` lookup table | Fallback for unknown maps |

### Map → Biome Mapping

| Map | Real analog | Köppen | Key characteristics |
|-----|-------------|--------|---------------------|
| **Altis** | Greek Aegean | **Csa** | Hot dry summers, mild wet winters |
| **Stratis** | Greek Aegean | **Csa** | Same as Altis, more exposed |
| **Tanoa** | South Pacific | **Af** | Uniform 26-28°C year-round, high humidity |
| **Livonia / Enoch** | E. Poland/Belarus | **Dfb** | Cold winters, mild summers, precip year-round |
| **Chernarus** | Czech Rep. | **Dfb** | Temperate continental, cold winters |
| **Takistan** | Afghanistan | **BSk/BWk** | Hot dry summers, cold winters, large DTR |
| **Malden** | S. France | **Csa** | Mediterranean |
| **Sahrani** | Caribbean | **Aw** | Tropical savannah, wet/dry seasons |
| **Kujari** | Sahel | **BSh** | Hot semi-arid |
| **Weferlingen** | Germany | **Cfb** | Oceanic, mild winters, cool summers |
| **Cam Lao Nam** | Vietnam | **Am** | Monsoon tropical |
| **Unknown** | — | **Cfa** (default) | Humid subtropical — safe mid-latitude default |

---

## 5. Climate Reference Data (Per-Biome)

Each biome stores 12 monthly entries. Minimal but sufficient for the alpha:

```
climate_biomes:
  id:           Köppen code (e.g., "Csa")
  name:         Human-readable name
  t_day[12]:    Monthly mean daytime temperature (°C)
  t_night[12]:  Monthly mean nighttime temperature (°C)
  humidity[12]: Monthly mean relative humidity (0-100%)
  pressure_msl: Mean sea-level pressure (hPa)
  dtr:          Typical diurnal range (°C) — for fine-tuning
```

Full monthly tables for the 5 primary biomes (Af, Csa, Dfb, BSk, Cfb) are in [biome_tables appendix below].

---

## 6. Environment Model — Formulae

### 6.1 Temperature

```
T_base = diurnal_interp(T_day[month], T_night[month], dayTime)
T_elevation = T_base - 0.0065 × elevation_ASL
T_overcast = T_elevation - 4 × overcast
T_final = round(T × 10) / 10
```

Where:
- `diurnal_interp`: cosine interpolation peaking at 13:00, minimum at 05:00
- `elevation_ASL`: `getTerrainHeightASL player` or map center reference
- `overcast`: `overcast` engine value (0-1)
- `4`: empirical cooling constant (ACE3 uses ~2-6 range, 4 is center)

### 6.2 Barometric Pressure

```
P_sea = 1013.25  // hPa, standard sea level
P_station = P_sea × (T_std / (T_std - 0.0065 × elevation))^5.2559
```

Where `T_std` = 288.15 K (standard sea-level temperature).

For more accuracy with real temperature:
```
P_corrected = P_station × e^( -g × elevation / (R_d × T_v) )
```

### 6.3 Humidity

```
RH = humidity[month]  // biome baseline
if (rain > 0 || overcast > 0.7) then {
    RH = 100  // saturated during rain
}
```

Humidity has minimal effect on ballistics (~1.5% density change at extremes) but is included for ACE3 downstream consumers that expect it.

### 6.4 Air Density (Complete Pipeline)

```sqf
// INPUTS:
//   T_C   : temperature (°C)
//   P_hPa : station pressure (hPa)
//   RH    : relative humidity (0-100)

// Step 1 — Saturation vapor pressure (Buck 1996, ±0.05% accuracy)
e_s = 6.1121 * exp( (18.678 - T_C/234.5) * T_C / (257.14 + T_C) );

// Step 2 — Actual vapor pressure
e = e_s * RH / 100;

// Step 3 — Virtual temperature (moist air correction)
T_K = T_C + 273.15;
P_Pa = P_hPa * 100;
T_v = T_K / (1 - 0.37802 * e / P_hPa * 100 / P_Pa);
// simplified: T_v = T_K / (1 - 0.37802 * e / P_hPa)
// since P_hPa * 100 / P_Pa = 1

// Step 4 — Density
R_d = 287.05287;  // J/(kg·K)
ρ = P_Pa / (R_d * T_v);  // kg/m³
```

### 6.5 Magnitude Reference (Why This Matters)

| Condition | ρ change | POI shift at 600m (5.56) |
|-----------|----------|--------------------------|
| Sea level, 15°C | baseline | — |
| Sea level, 35°C | -6.5% | +0.6 MOA (10 cm) |
| Sea level, -10°C | +9.5% | -0.7 MOA (12 cm) |
| 2000m ASL, 2°C | **-17.8%** | **+1.2 MOA (21 cm)** |
| 3000m ASL, -4.5°C | **-25.8%** | **+1.9 MOA (33 cm)** |

---

## 7. ACE3 Integration Strategy

**Approach: Replace entirely, own the output variables.**

### The Three Integration Points

| Variable | How AEE Sets It | Downstream consumers |
|----------|-----------------|---------------------|
| `ace_weather_currentTemperature` | `missionNamespace setVariable [..., true]` (broadcast) | advanced_ballistics, medical_vitals, kestrel4500, xm157 |
| `ace_weather_currentHumidity` | `publicVariable` | advanced_ballistics, artillerytables, mk6mortar |
| `ace_weather_currentOvercast` | Read from engine `overcast`, set with broadcast | advanced_ballistics |

### Strategy

**No ACE3 dependency.** AEE is standalone. When ACE3 is absent:
- AEE writes to its own `aee_*` variables
- The ballistic extension reads AEE variables directly

When ACE3 is present:
- AEE writes to `ace_weather_current*` variables
- ACE3 is disabled (`ace_weather_enabled = false` via CBA setting)
- AEE's update takes over all three variables
- Downstream ACE3 systems transparently use AEE-corrected data

**ACE3 compat layer** (fn_ace3_compat.sqf):
1. Detect ACE3: `isClass(configFile >> "CfgPatches" >> "ace_weather")`
2. If present: set `ace_weather_enabled = false` to stop ACE3's PFH
3. Set all three ace_weather_* variables on AEE's update cycle
4. Wind: set `ace_weather_disableWindSimulation = true` if AEE provides wind

### Key alignment point: CfgWorlds data

ACE3's `fnc_getMapData.sqf` reads `ACE_TempDay[]`, `ACE_Humidity[]`, etc. from CfgWorlds. AEE can also read these — but AEE doesn't need to. AEE carries its own biome climate tables, which are more granular and cover all maps regardless of ACE3 config entries.

---

## 8. CBA Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `aee_enabled` | BOOL | true | Master switch |
| `aee_biome` | STRING | "AUTO" | Override biome: AUTO, Af, Csa, Dfb, BSk, Cfb, ... |
| `aee_updateInterval` | NUMBER | 10 | Environment update interval (seconds) |
| `aee_elevationCorrection` | BOOL | true | Apply elevation lapse rate |
| `aee_biomeCorrection` | BOOL | true | Apply biome climate normals |
| `aee_diagnostic` | BOOL | false | Log environment state to diag_log |

---

## 9. Phasing & Milestones

### Phase 0 — Project Scaffold (1 session)
- Mod.cpp, meta.cpp, HEMTT project.toml
- Addon trio structure (main + aee_core)
- Script_mod, script_version, script_macros
- Config.cpp with CfgPatches + CfgFunctions
- CI/CD setup

### Phase 1 — Core Environment (days)
- `fn_init.sqf`: Server-only, register PFH
- `fn_getBiome.sqf`: CfgWorlds → Köppen, with fallback chain
- `fn_getClimateNormals.sqf`: Hardcoded monthly tables for 5 biomes
- `fn_updateTemperature.sqf`: Diurnal + elevation + overcast
- `fn_updatePressure.sqf`: Elevation-corrected pressure
- `fn_updateHumidity.sqf`: Biome + rain saturation
- `fn_updateEnvironment.sqf`: Orchestrator
- `fn_calculateAirDensity.sqf`: Complete formula
- Set `ace_weather_current*` variables for ACE3 compat
- **Milestone**: At 2000m on Altis, air density is ~1.01 kg/m³ instead of 1.225

### Phase 2 — ACE3 Integration (hours)
- `fn_ace3_compat.sqf`: Disable ACE3 weather, own the outputs
- Test with ACE3 advanced_ballistics downstream

### Phase 3 — Wind Model (optional)
- Replace ACE3 wind simulation
- Terrain-aware wind (ridge acceleration, valley channelling)
- CfgWorlds wind data integration

### Phase 4 — a3db Integration (optional)
- Ship biome climate tables as a3db binary
- Fall back to hardcoded tables when a3db absent

---

## 10. Biome Climate Tables — Reference Data

Abbreviated monthly data for the 5 primary biomes. Full source: IRL station normals (NOAA NCEI 1991-2020, WMO).

### Af — Tropical Rainforest (Tanoa)

| Month | T_day (°C) | T_night (°C) | Humidity (%) |
|-------|-----------|-------------|-------------|
| Jan | 30.6 | 24.3 | 81 |
| Feb | 31.5 | 24.6 | 78 |
| Mar | 32.2 | 24.9 | 77 |
| Apr | 32.4 | 25.3 | 79 |
| May | 32.3 | 25.7 | 79 |
| Jun | 31.9 | 25.7 | 78 |
| Jul | 31.4 | 25.4 | 77 |
| Aug | 31.4 | 25.3 | 78 |
| Sep | 31.6 | 25.2 | 79 |
| Oct | 31.8 | 25.0 | 80 |
| Nov | 31.2 | 24.6 | 82 |
| Dec | 30.5 | 24.3 | 82 |

Pressure: ~1009 hPa. Diurnal range: ~6-7°C.

### Csa — Hot Mediterranean (Altis)

| Month | T_day (°C) | T_night (°C) | Humidity (%) |
|-------|-----------|-------------|-------------|
| Jan | 13.6 | 7.2 | 78 |
| Feb | 14.6 | 7.6 | 75 |
| Mar | 16.9 | 9.3 | 70 |
| Apr | 20.8 | 12.5 | 63 |
| May | 25.9 | 17.0 | 55 |
| Jun | 31.2 | 21.7 | 48 |
| Jul | 34.0 | 24.3 | 46 |
| Aug | 34.0 | 24.5 | 48 |
| Sep | 29.4 | 20.7 | 58 |
| Oct | 24.2 | 16.5 | 67 |
| Nov | 19.1 | 12.4 | 75 |
| Dec | 14.8 | 8.9 | 78 |

Pressure: ~1015 hPa. Diurnal range: 6-10°C.

### Dfb — Humid Continental (Livonia, Chernarus)

| Month | T_day (°C) | T_night (°C) | Humidity (%) |
|-------|-----------|-------------|-------------|
| Jan | -3.9 | -8.7 | 95 |
| Feb | -3.0 | -8.8 | 95 |
| Mar | 3.0 | -4.2 | 90 |
| Apr | 11.7 | 2.3 | 76 |
| May | 19.0 | 8.1 | 70 |
| Jun | 22.4 | 12.2 | 69 |
| Jul | 24.7 | 14.8 | 70 |
| Aug | 22.7 | 13.0 | 69 |
| Sep | 16.4 | 8.0 | 76 |
| Oct | 8.9 | 3.0 | 81 |
| Nov | 1.6 | -2.4 | 86 |
| Dec | -2.3 | -6.5 | 93 |

Pressure: ~1016 hPa. Diurnal range: 8-12°C summer, 4-6°C winter.

### BSk — Cold Semi-Arid (Takistan)

| Month | T_day (°C) | T_night (°C) | Humidity (%) |
|-------|-----------|-------------|-------------|
| Jan | 9.0 | -3.1 | 67 |
| Feb | 10.7 | -1.1 | 64 |
| Mar | 15.9 | 4.1 | 56 |
| Apr | 21.7 | 9.4 | 47 |
| May | 27.2 | 13.8 | 35 |
| Jun | 32.7 | 18.4 | 26 |
| Jul | 34.8 | 20.7 | 26 |
| Aug | 33.9 | 19.4 | 27 |
| Sep | 29.5 | 14.9 | 29 |
| Oct | 23.7 | 9.4 | 38 |
| Nov | 16.8 | 3.6 | 50 |
| Dec | 11.3 | -0.4 | 60 |

Pressure: ~1020 hPa. Diurnal range: 12-16°C (largest of all biomes).

### Cfb — Oceanic (Western Europe, Weferlingen)

| Month | T_day (°C) | T_night (°C) | Humidity (%) |
|-------|-----------|-------------|-------------|
| Jan | 5.0 | 0.5 | 85 |
| Feb | 6.2 | 0.5 | 82 |
| Mar | 10.0 | 2.9 | 76 |
| Apr | 14.1 | 5.3 | 70 |
| May | 19.0 | 9.4 | 68 |
| Jun | 22.0 | 12.3 | 67 |
| Jul | 23.6 | 14.1 | 68 |
| Aug | 23.4 | 13.8 | 70 |
| Sep | 19.3 | 10.7 | 76 |
| Oct | 14.2 | 7.5 | 81 |
| Nov | 8.7 | 3.8 | 86 |
| Dec | 5.4 | 1.3 | 88 |

Pressure: ~1018 hPa. Diurnal range: 8-12°C.

---

## 11. Diurnal Interpolation Function

```sqf
// Returns current temperature from day/night normals + time
// T_day: monthly mean daytime temp
// T_night: monthly mean nighttime temp
// Input: dayTime (0-24)

private _fnc_diurnal = {
    params ["_tDay", "_tNight", "_dayTime"];
    
    // Daytime peak at 13:00, minimum at 05:00
    private _phase = ((_dayTime + 7) % 24) / 24;  // 0 at 05:00 (min), 0.333 at 13:00 (max)
    private _cos = cos(_phase * 360);
    
    // Amplitude is half the diurnal range
    private _mean = (_tDay + _tNight) / 2;
    private _amp = (_tDay - _tNight) / 2;
    
    _mean - _amp * _cos  // cos(0)=1 gives minimum at 05:00
};
```

---

## 12. Edge Cases & Design Decisions

| Case | Handling |
|------|----------|
| **Custom map** | Falls to Cfa default (humid subtropical). Mission maker can override via `aee_biome` CBA setting. |
| **Arctic map** | If no entry, falls to Dfc (subarctic) via the default fallback. |
| **Underwater** | No special handling — water temp not modeled in v1. |
| **Vehicle interior** | No vehicle interior microclimate in v1. Heat soak not modeled. |
| **Night vision / thermal** | Not AEE concern. Thermal imaging reads engine temp via ACE3's existing hook. |
| **Sea-level zero** | `getTerrainHeightASL` gives correct 0 at sea. |
| **a3db absent** | Hardcoded climate tables in `fn_getClimateNormals.sqf`. a3db is optional. |
| **ACE3 absent entirely** | AEE writes `aee_*` variables. Ballistic extension reads them. No dependency. |
| **Multiplayer** | All computation on server. Temperature/pressure/humidity publicVariable'd. Wind via setWind (engine-synced). |

---

## 13. Output Contract

AEE writes these missionNamespace variables (all server-side, broadcast to clients):

| Variable | Type | Unit | Example |
|----------|------|------|---------|
| `ace_weather_currentTemperature` | NUMBER | °C | 22.5 |
| `ace_weather_currentHumidity` | NUMBER | 0-100 | 65 |
| `ace_weather_currentPressure` | NUMBER | hPa | 1013.25 |
| `ace_weather_currentOvercast` | NUMBER | 0-1 | 0.3 |
| `aee_currentAirDensity` | NUMBER | kg/m³ | 1.225 |
| `aee_biome` | STRING | — | "Csa" |
| `aee_biomeName` | STRING | — | "Hot Mediterranean" |

The ballistic extension reads `aee_currentAirDensity` (with fallback to internal calculation if absent).

---

## 14. Rejected Approaches

| Approach | Rejected because |
|----------|-----------------|
| **Rust extension for environment** | SQF can handle 10-second interval math trivially. No performance reason to extend. |
| **Real-time METAR pulls** | Requires internet. Breaks in single-player offline. Not reliable for Arma. |
| **Per-player microclimate** | Computationally wasteful. Deferred to v2 if terrain shading is added. |
| **Full atmospheric model (MIL-STD-210C)** | Overkill. ICAO standard atmosphere + Buck humidity is 95% of the correction. |
| **a3db dependency for V1** | a3db not required. Tables hardcoded. a3db becomes an optional enhancement for moddability. |
