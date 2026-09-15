# ACE Environment Extended

AEE is a physically accurate environment simulation for Arma 3. It models elevation lapse rates, terrain microclimate, true air density, Koppen biome classification, thermal and physiological effects, optics, vehicle mobility, maritime state, radio propagation, and atmospheric events — all grounded in published physics rather than game-style approximations.

The mod is standalone and requires only [CBA A3](https://github.com/CBATeam/CBA_A3/releases).

---

## What AEE Does

- **Atmosphere** — Elevation lapse rates, diurnal temperature cycles, true air density from temperature/pressure/humidity, Koppen biome classification with seasonal variation, orographic precipitation, and WMO 3-hour pressure tendency.
- **Thermal and physiology** — Wet-bulb globe temperature (ISO 7243 heat-stress categories), NWS heat index, wind chill (JAG/TTI), altitude acclimatisation with time-of-useful-consciousness hypoxia, ISO 17166 UV index with ozone absorption, hypothermia and dehydration risk.
- **Optics** — Thermal crossover, mirage, solar glare, Cn2-based atmospheric seeing, physical smoke dispersal, rain visibility (Atlas extinction), dew and frost on optics, snow blindness.
- **Mobility** — SAE J1349 engine derating by air density, slip-curve traction, mud accretion, Nash-cascade river water level, NRMM cone-index route degradation, momentum-theory helicopter lift.
- **Environmental** — CBRN persistence (Arrhenius Q10), Rothermel fire spread, avalanche risk, Stefan freeze/thaw, flash-flood prediction, surface wetness, scent dispersion.
- **Maritime** — Harmonic tidal prediction (M2/S2/K1/O1 constituents), WMO Beaufort sea state, Pierson-Moskowitz wave height, magnetic compass deviation.
- **Radio** — Friis free-space path loss with atmospheric ducting and ITU-R P.531 ionospheric absorption for VHF/UHF/HF.
- **Atmospheric events** — Lightning (ice-phase gated), sandstorms, dust devils, microbursts (NWS tiers), ICAO eddy-dissipation-rate turbulence, airframe icing.

---

## Optional Integrations

- **ACE3** — Weather state feeds the Kestrel; heat index and WBGT published; WBGT and dehydration drive ACE3 medical vitals (heart rate, blood flow, pain).
- **KAT** — Dehydration and hypoxia state feed KAT's circulation model.
- **ACM** — CBRN persistence drives ACM's contamination state.
- **ACRE2 / TFAR** — Radio propagation index scales transmission range.
- **Real Weather** — Reads a `weather.json` written by `tools/weather_fetch.py` (Open-Meteo, no API key) and overrides the simulation.

---

## Requirements

- [CBA A3](https://github.com/CBATeam/CBA_A3/releases) (latest version)
- Arma 3

Compat addons load only when their host mod is present. AEE itself has no ACE3 dependency.

## Installation

1. Subscribe to this item, or download the latest release from GitHub and unpack `@aee` into your Arma 3 directory.
2. Launch with: `-mod=@cba_a3;@aee`
3. Configure via CBA Settings, AEE Core and AEE Mobility categories.

## Mission Authors

The EDEN module **AEE Environment Config** overrides biome, temperature offset, precipitation bias, wind multiplier, and the update interval.

Shared simulation state lives in `aee_core_*` mission variables. Any mission script can read the temperature, pressure, humidity, wind, WBGT, sea state, radio propagation index, and the rest of the state surface. See the documentation for the full reference.

## Compatibility and Support

- [GitHub Repository](https://github.com/lErrorl404l/AEE)
- [Documentation](https://lerrorl404l.github.io/AEE/)
- [Issue Tracker](https://github.com/lErrorl404l/AEE/issues)

## License

GPL-2.0-or-later with a PBO-distribution exception.
