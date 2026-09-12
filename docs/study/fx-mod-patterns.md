# AEE FX Study — Workshop Mod Patterns

## Mods Studied (12 total)

| ID | Name | PBOS | Category | Value |
|---|---|---|---|---|
| 2586787720 | TPW MODS | 7 | Fog/rain/dust/fire | **Highest** — direct overlap with AEE fx |
| 2735613231 | Weather+ | 2 | Event modules | Tornado, thunderstorm, snowfall, volcano |
| 879970502 | Real World Weather | 1 | API weather | Weather Underground API integration |
| 2275409948 | STRM Random Weather | 1 | Randomizer | Simple overcast/fog/wind cycling |
| 2555651608 | Alias Night FX | 1 | Cinematic | Satellites, meteors, aurora |
| 3672288512 | Vehicle Destruction FX | 2 | Destruction | Fire, smoke, spark particles |
| 1105511475 | ArmaFXP | 25 | Vehicle FX | Per-vehicle explosion effects |
| 1537745369 | Helicopter Dust | 1 | Dust | Rotor wash dust particles |
| 1465275935 | ANZACSAS Weather Clouds | 1 | Clouds | Cloud rendering |
| 2809399991 | Real Lighting and Weather | 3 | Post-FX | Film grain, night/rain effects |
| 1342869619 | Dust Wind Effect | 1 | Dust | Projectile impact dust |
| 767380317 | Blastcore Edited | 1 | Particles | Wall/wood debris |

---

## Key Patterns We Can Adopt

### 1. TPW FOG — Climate Zones (HIGHEST PRIORITY)

**What they do:** Map Arma map names to real-world climate zones with temperature/dewpoint ranges. Use latitude + map name to select zone.

**Pattern:**
```sqf
// Climate zone = [highDayMax, lowDayMax, highDayMin, lowDayMin, 
//                  highDewpoint, lowDewpoint, highMinDewpoint, lowMinDewpoint,
//                  coldestMonth, snowChance, zoneName]
_arctic = [20,-10,5,-25,9,-10,2,-18,1,20,"Arctic"];
_europe = [24,2,13,-4,16,0,11,-5,12,34,"Europe"];
_tropical = [33,28,25,22,26,23,23,15,2,0,"Tropical"];
```

**AEE adoption:** We already have Koppen classification. We can ADD a map-name-to-climate lookup as a fallback when the player hasn't set a custom location. The zone data gives us realistic temperature ranges, dewpoint limits, and snow probability per region. This is EXACTLY what our `getTemperatureAtPosition` needs for maps without custom weather data.

**Files:** `2586787720/TPW_MODS/tpw_fog.sqf` lines 60-180

---

### 2. TPW DUST STORM — Particle + Fog Overlay

**What they do:** Combine `#particlesource` particles with `60 setfog` for visibility reduction. Particles are spawned in a volume around the player.

**Pattern:**
```sqf
_dust = "#particlesource" createvehiclelocal getposasl vehicle player;
_dust attachto [vehicle player,[0,0,0]];
_dust setparticleparams [
    ["a3\data_f\particleeffects\universal\universal.p3d", 16, 12, 8, 0],
    "", "billboard", 1, _lifetime,
    [0, 0, 0],        // position
    _rotvel,           // rotation velocity
    1,                 // weight (1.275 = sinks slowly)
    _vol,              // volume
    _rub,              // rubbing (wind interaction)
    [_size],           // size
    _colourprog,       // colour progression [[r,g,b,0],[r,g,b,a],[r,g,b,0]]
    [1000],            // animSpeed
    1, 1, "", "", vehicle player
];
_dust setparticlerandom [1, [_diameter, _diameter, _height], [0, 0, 0], 0, 0, [0, 0, 0, 0.1], 0, 0];
_dust setdropinterval 0.05; // smaller = more dust
```

**AEE adoption:** Our `atmos` addon can drive dust particle density from AEE wind speed and surface moisture. When `aee_core_windSpeed > threshold` and `surfaceType is "dust"`, spawn particles with density proportional to wind. The fog overlay is already handled by AEE's fog system.

**Files:** `2586787720/TPW_MODS/tpw_fog.sqf` lines 775-850

---

### 3. TPW RAIN FX — Surface + Goggle Drops

**What they do:** Check `rain` engine variable, spawn particle sources for surface drops and goggle drops. Check for overhead cover using `lineIntersects`.

**Pattern:**
```sqf
// Check if under cover
private _pos = eyepos player vectoradd [0,0,0];
private _highpos = _pos vectoradd [0,0,50];
if (!(lineIntersects [_pos,_highpos]) && {vehicle player == player}) then {
    // Not under cover — spawn rain drops
};
```

**AEE adoption:** Our `fx` addon can use this `lineIntersects` pattern to determine if the player is sheltered. Rain particle density scales with AEE's `aee_core_precipitation` variable instead of the engine `rain` variable.

**Files:** `2586787720/TPW_MODS/tpw_rainfx.sqf` lines 30-60

---

### 4. REAL WEATHER — API Integration Pattern

**What they do:** Use `url_fetch` extension (DLL) to call Weather Underground API. Map Arma map names to real-world cities. Handle timeouts and retries.

**Pattern:**
```sqf
// Map Arma world to real city
case "ALTIS": {
    Weather_worldVar = "Greece";
    Weather_cityVar = "Limnos";
    WorldLat = "39.5329";
    WorldLong = "25.0122";
};

// Fetch with timeout
_status = "url_fetch" callExtension format ["%1", _this];
if (diag_tickTime > (_ticks + 15)) then { HZ_TIMEOUT = true; };
```

**AEE adoption:** We already have `weather_fetch.py` for OpenMeteo. This confirms the pattern: extension or Python callout for API, map-name-to-coordinates lookup, timeout handling. Our approach (Python script → diag_log JSON → SQF parse) is equivalent. The city mapping table is useful for the getting-started guide.

**Files:** `879970502/HZ_RealWorldWeather/functions/fn_GrabUrlData.sqf`, `fn_SetRealtimeWeather.sqf`

---

### 5. STRM RANDOM WEATHER — Simple Cycling

**What they do:** Every 50-60 minutes, randomize overcast, fog, wind. Use `setFog`, `setOvercast`, `setGusts`, `setWindStr`. Fog only at sunrise/sunset.

**Pattern:**
```sqf
_overcastChange = random [3000, 3300, 3600]; // 50-60 min
_overcastChangeTo = (_overcast selectRandomWeighted [1,4,3,2,1]);
(_overcastChange / timeMultiplier) setOvercast _overcastChangeTo;
(_overcastChange / timeMultiplier) setGusts _overcastChangeTo;
(_overcastChange / timeMultiplier) setWindStr _overcastChangeTo;
(_overcastChange / timeMultiplier) setWindForce (1 / (_overcastChangeTo + 0.01));
```

**AEE adoption:** AEE already does deterministic weather from position + time. This confirms the engine API pattern: `setFog`, `setOvercast`, `setGusts`, `setWindStr`, `setWindForce` with time dividers. The sunrise/sunset fog check is useful for our fog density calculations.

**Files:** `2275409948/St3_RandomWeather/functions/fn_RandomWeather.sqf`

---

### 6. WEATHER+ EVENT MODULES — Remote Execution

**What they do:** Each event (tornado, thunderstorm, snowfall) uses `remoteExec` to broadcast to all clients. Toggle pattern: check if already running → disable, else → enable.

**Pattern:**
```sqf
// Toggle pattern
if (!isNil "tornadosino" && { tornadosino == "goon" }) exitWith {
    [] remoteExec ["PHEN_fnc_Reset_Tornado", 0];
};
[_pos] remoteExec ["PHEN_fnc_Tornado", 0];
```

**AEE adoption:** Our CBRN and atmospheric events can use this pattern for multiplayer sync. The `publicVariable` toggle pattern is clean for enable/disable state.

**Files:** `2735613231/WeatherPLUS/Functions/Modules/fn_WP_Module_Tornado.sqf`

---

### 7. REAL LIGHTING — Post-Process Effects

**What they do:** Use `ppEffectCreate ["FilmGrain", ...]` with `linearConversion` to scale grain intensity based on rain and time-of-day.

**Pattern:**
```sqf
// Night + rain = heavy grain
if (sunOrMoon < 0.5) then {
    if (_rain > 0.4) then {
        effect_screen ppEffectAdjust [0.01, 0.7, 3.5, 1, 1, 1];
    } else {
        effect_screen ppEffectAdjust [0.01, 0.5, 0.5, 0.1, 0.1, true];
    };
};
```

**AEE adoption:** Our `optics` addon can use `ppEffectCreate ["FilmGrain", ...]` for night vision grain that scales with AEE's visibility state. The `linearConversion` pattern for scaling effects based on weather is exactly what we need.

**Files:** `2809399991/RW_Effects/functions/fn_nightTime.sqf`

---

### 8. HELICOPTER DUST — CfgSurfaces + CfgCloudlets

**What they do:** Override `CfgSurfaces` dust values per terrain type. Define custom `CfgCloudlets` for rotor wash dust.

**Pattern:**
```cpp
class CfgSurfaces {
    class GdtGrassShort : Default {
        dust = 0.02;  // Low dust from grass
    };
    class GdtConcrete : Default {
        dust = 0.03;  // More dust from concrete
    };
};

class CfgCloudlets {
    class HDust1 : Default {
        interval = "0.01 - 0.01 * ((density*1.7) interpolate [0,0.6,0,0.6])";
        weight = 1.8;   // Heavier than TPW (1.275)
        volume = 1.3;
        color[] = {{1,1,0.8,0.12},{1,1,0.8,0.1},{1,1,0.8,0.05},{1,1,0.8,0}};
        colorCoef[] = {1,1,1,"0.5*((density*3.8) interpolate [0,0.6,0,0.6])"};
    };
};
```

**AEE adoption:** Our `environmental` addon can override `CfgSurfaces` dust values per biome. Koppen classification tells us which biome → which dust level. Desert biomes get high dust, forest gets low. The `colorCoef` pattern scales particle color with density.

**Files:** `1537745369/ANZ_HeliDustEfxMod/config.cpp`

---

### 9. VEHICLE DESTRUCTION FX — CfgCloudlets + Event Handlers

**What they do:** Define CfgCloudlets for fire, smoke, sparks. Attach to vehicles via EventHandlers.

**Pattern:**
```cpp
class CfgCloudlets {
    class fxp_VEESmok1 : Default {
        interval = 0.03;
        particleShape = "\A3\data_f\ParticleEffects\Universal\Universal";
        particleFSNtieth = 16;
        particleFSIndex = 7;
        lifeTime = 3;
        size[] = {3, 7, 10};
        color[] = {{0.3,0.3,0.3,0.5},{0.4,0.4,0.4,0.4},{0.6,0.5,0.5,0.3},{0.7,0.7,0.7,0.2},{0.8,0.8,0.8,0.1},{1,1,1,0}};
    };
};
```

**AEE adoption:** Our `fx` addon can define custom cloudlets for AEE-driven effects (dust devils, heat haze, fire spread). The `CfgCloudlets` parameters are the standard reference for particle tuning.

**Files:** `3672288512/vdf_particles/config.cpp`, `1105511475/fxp_VehExpEffect/config.cpp`

---

## Summary: What to Build Next

| Priority | Pattern | Source | AEE Addon | Implementation |
|---|---|---|---|---|
| 1 | Climate zone fallback | TPW fog | core/atmos | Map name → zone lookup table |
| 2 | Dust particle density | TPW dust + HeliDust | environmental | Wind speed → particle density |
| 3 | Rain shelter check | TPW rainfx | fx | lineIntersects for overhead cover |
| 4 | Night grain scaling | Real Lighting | optics | ppEffectCreate + linearConversion |
| 5 | CfgSurfaces dust override | HeliDust | environmental | Koppen biome → dust value |
| 6 | Weather API pattern | Real World Weather | already done | OpenMeteo via weather_fetch.py |
| 7 | Event toggle pattern | Weather+ | atmospheric | publicVariable toggle for events |
| 8 | CfgCloudlets reference | ArmaFXP + VDF | fx | Particle parameter reference library |

---

## Key Takeaway

Every mod we studied uses the SAME engine APIs we already use:
- `#particlesource` for particle spawning
- `setFog`, `setOvercast`, `setWind` for weather state
- `ppEffectCreate` for post-processing
- `CfgCloudlets` for particle definitions
- `CfgSurfaces` for terrain properties

AEE doesn't need to invent anything. We need to WIRE our superior state variables (Koppen, air density, WBGT, CBRN persistence) to these same engine APIs. The mods show us HOW to wire them. AEE shows us WHAT to feed them.
