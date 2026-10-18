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
gives the introduction version. A nested, indented `since` block belongs to one
syntax alternative, never to the command.

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

Every engine weather quantity has one owner. This writer does not repeat a
write another function already makes:

| Quantity | Command | Command locality | Owner |
|---|---|---|---|
| wind | `setWind` | Global | `addons/atmos/functions/state/fnc_updateWind.sqf` |
| gusts | `setGusts` | Local | none. The engine owns the gust signal; `fnc_updateWind` reads it |
| humidity | `setHumidity` | Local (per client) | `addons/atmos/functions/state/fnc_applyEngineWeather.sqf` (this writer) |
| overcast | `setOvercast` | Local; global from the server | `addons/atmos/functions/state/fnc_applyEngineWeather.sqf` (this writer) |
| rain | `setRain` | Global from the server | `addons/atmos/functions/state/fnc_applyEngineWeather.sqf` (this writer) |
| rain particles (phase) | `setRain` | Local (per client) | `addons/atmos/functions/state/fnc_applyPrecipitationPhase.sqf` |
| fog | `setFog` | Global | `addons/atmos/functions/state/fnc_updateFog.sqf` |
| waves | `setWaves` | Local | `addons/maritime/functions/fnc_updateEngineWaves.sqf` |
| rainbow | `setRainbow` | Local | `addons/atmos/functions/state/fnc_updateRainbow.sqf` |
| lightnings | `setLightnings` | Local | `addons/atmos/functions/state/fnc_updateEngineLightnings.sqf` |
| simul cloud cover | `simulSetHumidity` | Local | `addons/atmos/functions/state/fnc_updateSimulWeather.sqf` |
| wind aloft (howl) | `enableEnvironment` | Local | `addons/atmos/functions/state/fnc_updateWindyCoef.sqf` |
| engine surface temperature | `ambientTemperature` | Unspecified (read only) | `addons/thermal/functions/environment/fnc_readEngineAmbientTemperature.sqf` |

Two writers for the one engine wind vector would compound, because
`fnc_updateWind` reads the engine wind every tick (ADR-041). The engine owns
the gust signal, so AEE writes `setGusts` nowhere: `fnc_updateWind` reads the
engine gust and publishes the derived value (see section 8). `setWaves` and
`setLightnings` need *Manual Override* in the Eden intel section to render at
all, and AEE logs one warning per session because a script cannot read that
flag (see section 8).

## 3. Locality

- **Server**: `setOvercast` and `setRain`. A client write is local and
  temporary, so the writer is server-authoritative here.
- **Client**: `setHumidity`. The command has no global form, so each client
  writes its own surface humidity. The writer gates it on `hasInterface`.
- **Client**: the `setRain [rainParams]` phase form, `simulSetHumidity` and
  the `enableEnvironment` wind coefficient. Each is local to the machine, so
  each bridge gates on `hasInterface`.

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
- **Phase**: the engine renders one precipitation form. The phase lever is the
  client-local `setRain [rainParams]` form (Arma 3 2.08): element 15 is the
  `snow` flag, and `setRain []` resets to the config form.
  `fnc_applyPrecipitationPhase` writes it once per phase change.
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

## 8. The levers added after the first writer

Four engine levers were unused. Each is now driven, and each is a separate
bridge with its own gate. The command facts are the local command DB
(acemod/arma3-wiki v2.22).

| Lever | Command and form | Locality | Since | Bridge |
|---|---|---|---|---|
| Precipitation phase | `setRain rainParams` (syntax 2) and `setRain []` | Local | Arma 3 2.08 | `addons/atmos/functions/state/fnc_applyPrecipitationPhase.sqf` |
| Cloud structure | `simulSetHumidity value` | Unspecified (local to the machine) | Arma 3 2.18 (working; 0.50 stub) | `addons/atmos/functions/state/fnc_updateSimulWeather.sqf` |
| In-cloud probe (read) | `simulInClouds pos`, `simulCloudDensity pos` | Local read | Arma 3 1.00 | `addons/atmos/functions/state/fnc_updateSimulWeather.sqf` |
| Wind aloft (howl) | `enableEnvironment [ambientLife, ambientSound, windyCoef]` | Local | `windyCoef` Arma 3 2.12 | `addons/atmos/functions/state/fnc_updateWindyCoef.sqf` |
| Surface temperatures (read) | `ambientTemperature` | Unspecified read | Arma 3 2.06 | `addons/thermal/functions/environment/fnc_readEngineAmbientTemperature.sqf` |

Two levers are deliberately NOT written:

- **`setGusts`** (Local, Arma 3 0.50). The engine owns the gust signal and
  `fnc_updateWind` reads it every tick to publish `aee_core_currentGusts`
  (ADR-041, the single-owner rule for the engine wind). A scripted gust would
  be read back through that per-tick read and compound, so the engine keeps
  the signal. The `gusts` row in the owner table stays `none`.
- **A setter for the engine air temperature.** None exists: the command DB has
  no `setAmbientTemperature` and no command that writes the black or white
  surface temperature. `ambientTemperature` is read only.

The `setWaves` and `setLightnings` writes need the Eden intel *Manual
Override* flag before the engine draws anything, and the command DB has no
command that reads or sets that flag, so a script can neither detect it nor
enable it. Both bridges call `aee_core_fnc_warnManualOverride`, which logs one
warning per session instead of a silent no-op.

## Related records

- [engine-commands-and-features.md](engine-commands-and-features.md) - the
  engine systems behind the weather commands, and the consolidated ceiling
  list.
- `docs/adr/ADR-041-weather-fronts.md` - the single-owner rule for the engine
  wind vector.
