# Arma 3 Commands Reference for AEE

Quick-reference for commands used by ACE Environment Extended.
For full documentation, fetch from BIKI: `https://community.bistudio.com/wiki/<CommandName>`

## Terrain Deformation

### setTerrainHeight
Modify terrain heightmap at runtime. Server only.
```sqf
setTerrainHeight [positionAndAltitudeArray, adjustObjects]
// positionAndAltitudeArray: [[x, y, newASL], ...]
// adjustObjects: true = move objects to match new terrain
```
- Changes are JIP-synced
- Grid-aligned (precision limited by map cell size)
- Extreme changes cause visual artifacts

### getTerrainHeight
Get terrain altitude at position.
```sqf
getTerrainHeight position  // returns ASL altitude
```

### getTerrainInfo
Get terrain grid parameters.
```sqf
getTerrainInfo position
// Returns: [gridSize, cellSize, rangeX, rangeY]
```

### surfaceType
Get surface material type at position.
```sqf
surfaceType position  // returns config name string
```

## Position & Vectors

### setPos / setPosATL / setPosASL
Set object position in different coordinate systems.
```sqf
object setPos [x, y, z]        //ATL (above terrain level)
object setPosATL [x, y, z]     // explicit ATL
object setPosASL [x, y, z]     // ASL (above sea level)
```

### getPos / getPosATL / getPosASL
Get object position.
```sqf
getPos object       // ATL array [x, y, z]
getPosATL object    // explicit ATL
getPosASL object    // ASL
```

### vectorAdd / vectorSubtract / vectorMultiply
Vector arithmetic.
```sqf
[a, b, c] vectorAdd [d, e, f]       // [a+d, b+e, c+f]
[a, b, c] vectorSubtract [d, e, f]  // [a-d, b-e, c-f]
[a, b, c] vectorMultiply scalar      // [a*s, b*s, c*s]
```

### vectorNormalized
Normalize vector to unit length.
```sqf
vectorNormalized [x, y, z]  // returns unit vector
```

### distance / distanceSqr
Distance between positions or objects.
```sqf
pos1 distance pos2       // meters
pos1 distanceSqr pos2    // squared (faster, no sqrt)
```

## Environment

### wind / windDir / windStr / gusts
Wind state.
```sqf
wind      // [x, y, z] wind vector
windDir   // direction in degrees
windStr   // wind strength 0-1
gusts     // gust strength 0-1
```

### rain / overcast / fog / humidity / temperature / pressure
Weather state.
```sqf
rain       // 0-1 intensity
overcast   // 0-1 cloud cover
fog        // 0-1 fog density
humidity   // 0-1 relative humidity
temperature // degrees C
pressure   // hPa
```

### waves
Wave height from wind.
```sqf
waves  // 0-1 wave intensity
```

## Post-Process Effects

### ppEffectCreate
Create a post-process effect.
```sqf
private _pp = ppEffectCreate ["EffectName", priority];
```
Common effects:
- `"ColorCorrections"` - color grading
- `"DynamicBlur"` - blur
- `"FilmGrain"` - noise
- `"RadialBlur"` - radial blur
- `"ChromAberration"` - chromatic aberration
- `"WetDistortion"` - water distortion

### ppEffectAdjust
Set effect parameters.
```sqf
_pp ppEffectAdjust [params];
```

### ppEffectCommit
Apply changes over time.
```sqf
_pp ppEffectCommit duration;  // 0 = instant
```

### ppEffectEnable / ppEffectDestroy
```sqf
_pp ppEffectEnable true;   // enable
_pp ppEffectEnable false;  // disable
_pp ppEffectDestroy;       // remove
```

## Particles

### setParticleParams
Configure particle emitter.
```sqf
object setParticleParams [
    [shape, ntieth, index, count],
    [animation],
    [type],           // "Billboard" or "Key"
    lifetime,
    speed,
    weight,
    volume,
    rubbing,
    size,
    color,
    [direction],
    [angle, angleVar],
    [event]
];
```

### setParticleRandom
Set particle randomness.
```sqf
object setParticleRandom [
    lifeTimeVar,
    positionVar,
    velocityVar,
    rotationVar,
    sizeVar,
    colorVar,
    randDirAngleVar
];
```

## Scheduling & Timing

### diag_tickTime
High-precision timer (milliseconds).
```sqf
diag_tickTime  // returns float
```

### time
Mission elapsed time (seconds).
```sqf
time
```

### sleep / waitUntil
Script scheduling.
```sqf
sleep seconds;
waitUntil { condition };
```

## Config Reading

### getNumber / getText / getArray
Read config values.
```sqf
getNumber (configFile >> "CfgVehicles" >> "B_Soldier_F" >> "armor")
getText (configFile >> "CfgVehicles" >> "B_Soldier_F" >> "displayName")
getArray (configFile >> "CfgVehicles" >> "B_Soldier_F" >> "hiddenSelections")
```

## Multiplayer

### setVariable / getVariable
Object variable storage.
```sqf
object setVariable ["name", value, true];  // true = public
object getVariable ["name", defaultValue];
```

### remoteExec / remoteExecCall
Remote execution.
```sqf
[code, target] remoteExec ["functionName", owner];
// owner: 0=all, 2=server, -2=all except server
```

### isServer / isDedicated / hasInterface
Environment detection.
```sqf
isServer       // true on server
isDedicated    // true on dedicated server
hasInterface   // true if client has display
```

## Math

### linearConversion
Linear interpolation.
```sqf
linearConversion [minIn, maxIn, minOut, maxOut, value]
```

### selectRandom / selectRandomWeighted
Random selection from array.
```sqf
selectRandom array
selectRandomWeighted [values, weights]
```

### pushBack / pushBackUnique / append
Array modification.
```sqf
array pushBack element
array pushBackUnique element  // no duplicate
array append otherArray
```

## References

- BIKI: `https://community.bistudio.com/wiki/`
- arma3-wiki: `https://github.com/acemod/arma3-wiki`
- ArmaDoc: `https://github.com/ArmaDoc/ArmaDoc`
- SQF.VSC: `https://github.com/ffredyk/SQF.VSC`
