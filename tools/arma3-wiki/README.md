# Arma 3 Wiki Reference

## Quick Access

For on-demand wiki page access, use the `webfetch` tool with URLs from the
Bohemia Interactive Community Wiki (BIKI):

- **Base URL**: `https://community.bistudio.com/wiki/`
- **Command pages**: `https://community.bistudio.com/wiki/<CommandName>`
- **Function pages**: `https://community.bistudio.com/wiki/<FunctionName>`

### Fetching Wiki Pages

When you need a specific command or function reference:

```
webfetch(url="https://community.bistudio.com/wiki/setTerrainHeight", format="markdown")
```

### Structured Data (acemod/arma3-wiki)

The ACE3 team maintains machine-readable command data in YAML format:

- **Repository**: `https://github.com/acemod/arma3-wiki`
- **Branch**: `dist`
- **Format**: YAML files in `commands/` directory
- **Rust client**: `arma3-wiki` crate on crates.io

To fetch a specific command definition:

```
webfetch(url="https://raw.githubusercontent.com/acemod/arma3-wiki/dist/commands/<commandname>.yaml", format="text")
```

### Common AEE Commands

#### Terrain
- `setTerrainHeight` - Modify terrain heightmap at runtime
- `getTerrainHeight` - Get terrain altitude at position
- `getTerrainInfo` - Get terrain grid size, cell size, range
- `surfaceType` - Get surface material type at position
- `surfaceTexture` - Get surface texture path at position

#### Environment
- `wind` - Current wind vector
- `windDir` - Wind direction in degrees
- `windStr` - Wind strength
- `gusts` - Gust strength
- `rain` - Rain intensity (0-1)
- `rainbow` - Rainbow intensity
- `fog` - Fog value
- `overcast` - Cloud cover (0-1)
- `waves` - Wave height
- `humidity` - Relative humidity (0-1)
- `temperature` - Air temperature
- `pressure` - Atmospheric pressure

#### Post-Process Effects
- `ppEffectCreate` - Create post-process effect
- `ppEffectAdjust` - Set effect parameters
- `ppEffectCommit` - Apply effect changes
- `ppEffectEnable` - Enable/disable effect
- `ppEffectDestroy` - Remove effect

#### Particles
- `setParticleParams` - Configure particle emitter
- `setParticleRandom` - Set particle randomness
- `setParticleCircle` - Set particle circle emitter
- `setParticleBeam` - Set particle beam emitter

#### Objects & Position
- `createVehicle` - Create object
- `setPos` / `setPosATL` / `setPosASL` - Set position
- `getPos` / `getPosATL` / `getPosASL` - Get position
- `vectorUp` - Get object up vector
- `setVectorUp` - Set object orientation

#### Math & Geometry
- `vectorMultiply` - Scale vector
- `vectorAdd` - Add vectors
- `vectorSubtract` - Subtract vectors
- `vectorDotProduct` - Dot product
- `vectorCrossProduct` - Cross product
- `vectorNormalized` - Normalize vector
- `distance` - Distance between positions
- `distanceSqr` - Squared distance (faster)

#### Scheduling & Timing
- `diag_tickTime` - High-precision timer
- `time` - Mission time
- `sleep` - Pause execution
- `waitUntil` - Wait for condition
- `spawn` - Spawn new VM
- `call` - Call function

#### Config & Settings
- `configName` - Get config class name
- `getNumber` / `getText` / `getArray` - Read config values
- `missionConfigFile` - Mission config
- `configFile` - Game config

#### Multiplayer
- `publicVariable` - Broadcast variable
- `setVariable` / `getVariable` - Object variables
- `remoteExec` / `remoteExecCall` - Remote execution
- `hasInterface` - Check if client has display
- `isServer` - Check if running on server
- `isDedicated` - Check if dedicated server

## Important: Wiki Is Not Complete

The BIKI documents what BI publicly documents. The community regularly finds
workarounds and undocumented capabilities. Examples:

- Depth of field works in-game but is not listed as a PP effect on the wiki.
- Some ppEffect parameters accept values beyond documented ranges.
- Config overrides can enable features BI never officially exposed.

**Do not treat "not on the wiki" as "not possible".** When a feature appears
blocked by engine limits, search community forums, Discord, and mod sources
before concluding it is impossible. The wiki is a floor, not a ceiling.

## Community Resources (beyond wiki)

- BI Forums: `https://forums.bohemia.net/forums/forum/169-arma-3-modding/`
- Arma 3 Discord modding channels
- ACE3 source: `https://github.com/acemod/ACE3` (patterns for advanced engine use)
- GRU3/enfusionbypass communities (engine-level research)

## References

- BIKI: `https://community.bistudio.com/wiki/`
- arma3-wiki: `https://github.com/acemod/arma3-wiki`
- ArmaDoc: `https://github.com/ArmaDoc/ArmaDoc`
- SQF.VSC: `https://github.com/ffredyk/SQF.VSC`
