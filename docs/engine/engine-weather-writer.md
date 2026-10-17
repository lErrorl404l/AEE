# The engine weather writer: commands, ranges and the AEE mapping

Purpose: record the engine weather surface that AEE writes, so a modelled
storm is visible in the engine as cloud, rain and a wet surface. This page
states each command, its range, its locality, its interpolation form, and the
AEE mapping. It names the inland-water ceiling last.

The writer is `addons/atmos/functions/state/fnc_applyEngineWeather.sqf`. It
runs once per environment tick from
`addons/core/functions/fnc_updateEnvironment.sqf`.

## 1. Source and method

The contract is the local Arma 3 command DB, acemod/arma3-wiki dist **v2.22**,
one page per command at `commands/<name>.yml`. The column-0 `since` block
gives the introduction version. A nested, indented `since` block belongs to
one syntax alternative, never to the command.

Two engine facts decide the design and are read from the same pages:

- `setOvercast` and `setRain` propagate globally only from the **server**. A
  client call is local, temporary, and reverts to the server value.
- Rain does not fall below overcast **0.5** in Arma 3.

## 2. The commands the writer uses

| Command | Form | Range | Effect locality | Since |
|---|---|---|---|---|
| `setOvercast` | `time setOvercast value` | overcast 0..1 | Local; global from the server | Arma 3 0.50 |
| `setRain` | `time setRain value` | rain 0..1; needs overcast >= 0.5 | Global from the server | Arma 3 0.50 |
| `setHumidity` | `setHumidity value` | surface humidity 0..1 | Local | Arma 3 2.8 |
| `forceWeatherChange` | `forceWeatherChange` | nular | Unspecified | Arma 3 1.16 |

`setFog`, `setWind`, `setWaves`, `setRainbow` and `setLightnings` are engine
weather commands that AEE already writes. Each has one owner and this writer
does not repeat the write:

| Command | Owner |
|---|---|
| `time setFog [value, decay, base]` | `addons/atmos/functions/state/fnc_updateFog.sqf` |
| `setWind [x, y, forced]` | `addons/atmos/functions/state/fnc_updateWind.sqf` |
| `time setWaves value` | `addons/maritime/functions/fnc_updateEngineWaves.sqf` |
| `time setRainbow value` | `addons/atmos/functions/state/fnc_updateRainbow.sqf` |
| `time setLightnings value` | `addons/atmos/functions/state/fnc_updateEngineLightnings.sqf` |

Two writers for the one engine wind vector would compound, because
`fnc_updateWind` reads the engine wind every tick (ADR-041). `setWaves` and
`setLightnings` need *Manual Override* in the Eden intel section to render at
all.

## 3. Locality

- **Server**: `setOvercast` and `setRain`. A client write is local and
  temporary, so the writer is server-authoritative here.
- **Client**: `setHumidity`. The command has no global form, so each client
  writes its own surface humidity. The writer gates it on `hasInterface`.

## 4. Interpolation

Every value uses the engine's timed form, `<time> setOvercast value` and
`<time> setRain value`. The time is one AEE tick
(`aee_core_updateInterval`), so the engine ramps to the new value instead of
snapping.

`forceWeatherChange` applies the pending values at once and skips the
transition. It can cause lag (command DB). The writer therefore never calls
it on the per-tick path. It is reserved for an explicit transition: a caller
that passes `true` to `aee_atmos_fnc_applyEngineWeather` applies the values
with a zero transition and then calls `forceWeatherChange` once.

## 5. The AEE mapping

AEE holds its own absolute cloud fraction in `aee_atmos_targetOvercast`. It is
seeded once from the engine overcast, so an authored mission sky is the
floor, and then driven by AEE's models. Holding the value in AEE state stops
the writer reading back its own engine write and compounding.

- **Overcast fraction**: `clamp(max(baseline, cloudFromHumidity) +
  frontCloudTerm, 0, 1)`. The baseline is the seeded engine overcast.
  `cloudFromHumidity` rises from 0 at 55 % relative humidity to 1 at 90 %.
  `frontCloudTerm` is the signed front forcing from
  `fnc_updateWeatherFront`. The two humidity end points are AEE modelling
  choices and are marked UNSOURCED against the engine.
- **Precipitation intensity**: the modelled rate is
  `aee_atmos_frontPrecipRate * aee_core_orographicFactor`, in millimetres per
  hour. The engine value is that rate divided by `ENGINE_RAIN_FULL_MMH`
  (`addons/lib/constants.hpp`, 25 mm/h). This division is the only place the
  modelled millimetres-per-hour and the engine 0..1 meet.
- **Engine coupling**: rain needs overcast >= 0.5. A modelled rate above zero
  raises the overcast target to 0.5. An overcast below 0.5 forces the engine
  rain to zero.
- **Humidity**: the modelled relative humidity in percent divided by 100, to
  the engine's surface-humidity 0..1.
- **Phase**: the engine renders one precipitation form, so phase does not
  change the engine intensity. The only phase lever is the client-local
  `setRain []` rain-params form (Arma 3 2.8), which is out of scope here.
- **Wind**: owned by `fnc_updateWind`. The engine raises wind with overcast,
  so the overcast write below is the writer's only wind lever.

## 6. Precedence

`fnc_engineWeatherBlockedReason` returns the reason AEE must not write, or
`""` when it may. First match wins:

1. `"setting"`: `aee_atmos_engineWeatherEnabled` is off.
2. `"manual"`: `aee_atmos_manualWeather` is true. An operator or a mission has
   taken manual control and AEE must not fight it.

AEE alone owns the engine weather. There is no compat layer between AEE and
the engine weather, so the writer is the single producer of overcast and rain.

A mission that scripts its own weather sets `aee_atmos_manualWeather = true`.

## 7. Ceiling: inland water

The engine draws one flat sea plane at the world sea level. It has no second
water body and no scripted water body at run time. AEE models river level,
surface wetness and flood as **state**
(`fnc_calculateRiverWaterLevel`, `fnc_calculateSurfaceWetness`,
`fnc_calculateFlashFloodRisk`), and this writer cannot draw inland water from
that state.

The only engine-visible levers AEE holds near inland water are:

- `setHumidity value` (surface wetness, the wet footstep sound),
- `time setRain value` (falling rain and the wet ground it leaves),
- `time setFog [value, decay, base]` (the fog that follows the water cycle).

A river, a flood or a wet track stays a plotted state until the engine exposes
a water body, which it does not. This is the recorded ceiling.

## Related records

- [engine-commands-and-features.md](engine-commands-and-features.md) - the
  engine systems behind the weather commands, and the consolidated ceiling
  list.
- `docs/adr/ADR-041-weather-fronts.md` - the single-owner rule for the engine
  wind vector.
