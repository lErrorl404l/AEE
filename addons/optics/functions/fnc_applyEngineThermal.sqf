#include "..\script_component.hpp"
/*
 * Drives the ENGINE's thermal display from AEE's physics model.
 *
 * The engine renders thermal natively from per-object heat state, then maps
 * the result through a display window:  OutputRangeStart + thermalValue *
 * OutputRangeWidth (default 0.1 + t * 0.8 -> range 0.1..0.9).  The default
 * window is compressed, so the engine's per-object thermal differences all
 * clip to the same brightness — the "everything is white" report.
 *
 * Two levers, both scriptable since 2.10 (SPOTREP #00106):
 *
 *  1. setTIParameter  - the DISPLAY GAIN.  Widening OutputRangeWidth and
 *     lowering OutputRangeStart spreads the engine's thermal values across
 *     the full screen range, exactly like a real FLIR's AGC/level controls
 *     (or dark-adapted eyes: the window defines what is visible).  Driven
 *     from our contrast model: clear scene -> full width, crossover/rain
 *     -> narrowed (the scene's meaningful spread is smaller).
 *
 *  2. setVehicleTIPars - the per-vehicle INPUT heat state 0..1, read from
 *     our object-temperature model (engineRunTime -> engine heat, speed ->
 *     wheel heat).  The engine then renders running vs parked vehicles
 *     differently, which its baked static heatmaps cannot.
 *
 * The engine still owns the render pass and the palette.  We only supply
 * the input heat state and the display window.  A custom renderer is not
 * possible (the thermal pass is not interceptable), so this is the maximum
 * physical control the engine exposes.
 *
 * Reapplied every tick while thermal is active; the settings are not saved
 * in savegames and must be reapplied after loading (BIKI).
 */
params [""];

if (!hasInterface) exitWith { 0 };

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith { 0 };

// ─── 1. Display baseline (FIXED, not adaptive) ────────────────────────────
// A thermal display's gain/level must be STABLE or the operator cannot
// compare hot vs cold across a scene: an auto-exposure layer that re-maps
// as the view changes reads as a "flashlight" / "something is leaching in"
// and makes every 1:1 comparison impossible (the user's exact report).
// Real military thermals offer a fixed gain+level; AGC exists but is a
// deliberate mode, not the default.
//
// The engine's own output mapping is already the physics pass: thermalValue
// (0..1) -> brightness.  The window (OutputRangeStart/Width) is only a
// display baseline.  We lock it to start=0 (cold = dark), width=1 (full
// range) ONCE on ENTER, so the image is deterministic and all separation
// comes from per-object thermalValue (vehicles via setVehicleTIPars,
// people/buildings via material swaps).  The physics below does the work;
// the window must not fight it.
private _outStart = 0.0;
private _outWidth = 1.0;

// Apply once (guard: only call when not already applied this session).
private _tiBaseSet = missionNamespace getVariable [QGVAR(tiBaseSet), false];
if !(_tiBaseSet isEqualType true) then { _tiBaseSet = false; };
if (!_tiBaseSet) then {
    setTIParameter ["OutputRangeStart", _outStart];
    setTIParameter ["OutputRangeWidth", _outWidth];
    missionNamespace setVariable [QGVAR(tiBaseSet), true];
    AEE_LOG_INFO("thermal display baseline locked: start=0 width=1");
};

// ─── 2. Per-vehicle heat state from our physics model ─────────────────────
// setVehicleTIPars is a LOCAL command (no _Global variant exists; it is
// registered client-side in the engine).  That is correct for our design:
// the thermal image is rendered per-client, each client runs this PFH, and
// each client's own thermal view reads the heat state it set locally.
// The physics inputs (weather, engine state) are identical across clients,
// so every client computes the same heat values for the same vehicles.
//
// DESIGN: drive the heat state from our PHYSICS TEMPERATURE for ALL
// vehicles, engine on or off.  The vanilla engine's own model (afMax/
// htMax static timers) is unrealistic — that is the exact thing mods
// exist to replace.  Our fnc_calculateObjectTemperature already computes
// the equilibrium surface temperature from EVERYTHING:
//   air temp + solar absorption (0.7 x 15 C) + engine heat (40 C, tau
//   300 s) + exhaust share (200 C, tau 60 s) + wind convective cooling
//   + thermal inertia (tau 120 s) + emissivity
// That IS the heat fraction, mapped to the engine's 0..1 scale:
//   0 = ambient, 1 = ambient + 50 C (a hard-running engine on a hot
//   day).  The engine renders THIS, so sun, ambient, wind, and engine
//   state all move the image — no static timers.
//
// Read QGVAR(thermalState): key str object, value [temp, engineRunTime,
// now, acclimatisation, obj].  temp is the equilibrium surface temp C.
private _thermalState = missionNamespace getVariable [QGVAR(thermalState), createHashMap];
private _vehicles = _player nearEntities [["Car", "Tank", "Motorcycle", "Helicopter", "Plane", "Ship"], 150];
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };

{
    if (isNull _x || !alive _x) then { continue; };
    private _objKey = str _x;
    private _state = _thermalState getOrDefault [_objKey, []];

    // Physics surface temperature (C).  Falls back to ambient + solar on
    // a fresh spawn (no state yet) so the vehicle is not instantly cold.
    private _surfaceTemp = _airTemp;
    if (count _state >= 1) then {
        private _t = _state select 0;
        if (_t isEqualType 0) then { _surfaceTemp = _t; };
    };
    // Heat fraction on the engine's 0..1 scale: ambient = 0, +50 C = 1.
    // A parked vehicle at ambient reads 0 (dark); a running engine at
    // +40 C reads 0.8 (bright).  Clamped to the engine's range.
    private _engineHeat = ((_surfaceTemp - _airTemp) / 50) min 1 max 0;

    // ─── Damage-state thermal ──────────────────────────────────────────
    // A damaged engine runs HOTTER: coolant loss and increased friction
    // raise the operating temperature well above a healthy engine.  A
    // destroyed or burning vehicle is at combustion temperature (~600 C)
    // and saturates the signature.  Damage is read per hit point so a
    // shot engine reads hot while an undamaged body stays normal —
    // real vehicle thermal after combat.
    //
    // getHitPointDamage is per hit point; scan the vehicle's hit points
    // once per damage check.  Engine damage boosts heat up to +0.5 (the
    // engine is ~50 C hotter at 100% damage); fuel damage adds fire risk
    // (hotter); body damage over 0.9 or destroyed = burning/saturated.
    private _damageEngine = 0;
    private _damageFuel = 0;
    private _damageBody = 0;
    // getAllHitPointsDamage returns [names[], selections[], damages[]] —
    // three parallel arrays, NOT [name, selection, damage] triples.  Each
    // element of the names array is a STRING; the matching damage is at
    // the same index in the damages array.  Destructuring the flat array
    // as triples read a String where a Number was expected (tolower error).
    private _hpData = getAllHitPointsDamage _x;
    if (count _hpData >= 3 && {count (_hpData select 0) > 0}) then {
        private _hpNames = _hpData select 0;
        private _hpDamages = _hpData select 2;
        for "_i" from 0 to (count _hpNames - 1) do {
            private _hn = toLower (_hpNames select _i);
            private _hpDamage = _hpDamages select _i;
            if (_hn find "engine" >= 0) then { _damageEngine = _damageEngine max _hpDamage; };
            if (_hn find "fuel" >= 0 || _hn find "tank" >= 0) then { _damageFuel = _damageFuel max _hpDamage; };
            if (_hn find "body" >= 0 || _hn find "hull" >= 0) then { _damageBody = _damageBody max _hpDamage; };
        };
    };

    // Destroyed or burning: the whole vehicle is at combustion temperature.
    if (!alive _x || _damageBody >= 0.95 || _damageFuel >= 0.95) then {
        _engineHeat = 1;
    } else {
        // Damaged engine: +0.5 heat at full engine damage (runs ~50 C hot).
        _engineHeat = (_engineHeat + _damageEngine * 0.5) min 1;
        // Fuel damage: fire risk, hotter even if engine is fine.
        _engineHeat = (_engineHeat + _damageFuel * 0.2) min 1;
    };
    // A damaged engine on a destroyed vehicle is already saturated above.

    // Wheel heat: friction from motion.  Real tyres warm with speed and
    // driving time; simple model: speed fraction of a threshold.
    private _speed = abs speed _x;
    private _wheelHeat = (_speed / 30) min 1;

    // ─── Exhaust heat (weapon TI slot) ────────────────────────────────
    // The engine's setVehicleTIPars slots are engine/wheels/weapon.  We
    // drive the WEAPON slot from exhaust temperature — at idle the
    // exhaust is the hottest visible signature on a running vehicle
    // (200 C exhaust gas above ambient, tau 60 s warm-up), hotter than
    // the engine block (40 C).  The user reported "can't see exhaust
    // when idling"; this fixes it.
    //
    // Exhaust temp computed from the SAME physics as the object temp
    // model: exhaustTemp = air + 200*(1-exp(-runTime/60)).  Mapped to
    // the 0..1 heat scale (ambient = 0, +50 C = 1) and clamped.  The
    // engineRunTime is state element 1 (0 = off/cold).
    private _engineRunTime = 0;
    if (count _state >= 2) then {
        private _ert = _state select 1;
        if (_ert isEqualType 0) then { _engineRunTime = _ert; };
    };
    private _exhaustHeat = 0;
    if (_engineRunTime > 0) then {
        private _exhaustTemp = _airTemp + 200 * (1 - exp (-_engineRunTime / 60));
        _exhaustHeat = ((_exhaustTemp - _airTemp) / 50) min 1 max 0;
    };
    // Engine on but run time not yet accumulated (fresh state): the
    // exhaust warms within a minute, so give it the engine-block heat as
    // a floor — a running vehicle always has a warm exhaust.
    if (_exhaustHeat <= 0 && isEngineOn _x) then {
        _exhaustHeat = _engineHeat max 0.3;
    };
    // Destroyed: exhaust saturates with the rest.
    if (!alive _x || _damageBody >= 0.95) then { _exhaustHeat = 1; };

    // Weapon heat: skip (barrel heat is a weapon-state system we do not
    // model per-shot yet; keep the engine's own handling).
    //
    // Change guard: setVehicleTIPars is a real engine call (network +
    // heat-state update).  Only invoke it when a value moved materially;
    // otherwise a convoy of parked vehicles would spam the call every
    // 0.1 s tick.  Store the last-applied triple per vehicle in
    // missionNamespace so it survives tick-to-tick.
    private _lastTriple = missionNamespace getVariable [format [QGVAR(tiVeh_%1), _objKey], [-1, -1, -1]];
    if (_lastTriple isEqualType []) then {
        if (count _lastTriple < 3) then { _lastTriple = [-1, -1, -1]; };
    } else {
        _lastTriple = [-1, -1, -1];
    };
    private _changed = false;
    if (abs ((_lastTriple select 0) - _engineHeat) > 0.02) then { _changed = true; };
    if (abs ((_lastTriple select 1) - _wheelHeat) > 0.02) then { _changed = true; };
    if (abs ((_lastTriple select 2) - _exhaustHeat) > 0.02) then { _changed = true; };
    if (_changed) then {
        _x setVehicleTIPars [_engineHeat, _wheelHeat, _exhaustHeat];
        missionNamespace setVariable [format [QGVAR(tiVeh_%1), _objKey], [_engineHeat, _wheelHeat, _exhaustHeat]];
    };

    // Debug: one line per vehicle, throttled — confirms the engine is
    // being driven from physics.
    if (missionNamespace getVariable [QGVAR(nvgDebug), false]) then {
        diag_log text format ["[AEE] TI drive: %1 T=%2 air=%3 heat=%4 wheels=%5 speed=%6 dmgEng=%7 dmgFuel=%8",
            typeOf _x, round (_surfaceTemp * 10) / 10, round (_airTemp * 10) / 10,
            _engineHeat, _wheelHeat, round _speed, round (_damageEngine * 100) / 100,
            round (_damageFuel * 100) / 100];
    };

    // Track the scene's hottest heat fraction for the AGC window (section
    // 1 reads it next tick).  This makes the display gain follow the
    // environment: a scene with a running engine brightens against cold
    // ambient; an empty cold scene stays dark.
    if (_engineHeat > (missionNamespace getVariable [QGVAR(tiSceneMaxHeat), 0.5])) then {
        missionNamespace setVariable [QGVAR(tiSceneMaxHeat), _engineHeat];
    };
} forEach _vehicles;

// Decay the scene max toward ambient over ~30 s so the gain relaxes when
// the hot source leaves view (a FLIR does not hold max gain forever).
private _sceneMax = missionNamespace getVariable [QGVAR(tiSceneMaxHeat), 0.5];
if !(_sceneMax isEqualType 0) then { _sceneMax = 0.5; };
_sceneMax = _sceneMax - 0.2 * (diag_deltaTime / 30);
missionNamespace setVariable [QGVAR(tiSceneMaxHeat), _sceneMax max 0.05];

count _vehicles
