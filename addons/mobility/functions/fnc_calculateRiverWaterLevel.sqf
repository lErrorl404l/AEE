#include "..\script_component.hpp"

/*
Cumulative water level change from precipitation, modelled as a Nash
cascade of three serial linear reservoirs with biome-dependent inflow.

  • r1 accumulates rainfall, r2 and r3 pass it downstream
  • Outflow from r3 drives the water level (lagged, peaked response)
  • Tropical biomes amplify, arid biomes dampen
  • Flood risk thresholds for mission logic (river crossings, flooding)

Stored in GVAR(currentWaterLevel) — float 0+ (0 = dry baseline)
Stored in GVAR(riverReservoirs)   — [r1, r2, r3] cascade state
Stored in GVAR(currentFloodRisk)  — string "None"|"Elevated"|"Flood"|"Severe"
*/

private _biome = missionNamespace getVariable [QEGVAR(core,biome), "Cfb"];
if (isNil "_biome" || _biome == "") then { _biome = "Cfb"; };

// ─── Curve number from the surface and the biome ──────────────────────────
// The biome factor once multiplied the rainfall directly, which is a proxy
// for infiltration. The Curve Number expresses the same thing from the
// soil group and the land cover (issue #24): an arid biome drains its
// sparse cover, a tropical one sheds far more. The values are the TR-55
// table's hydrologic soil groups B and C, which most temperate ground is.
private _curveNumber = switch (true) do {
    case (_biome in ["Af","Am","Aw"]):                { 88 };  // dense cover, wet
    case (_biome in ["Cfa","Cfb","Cwa","Csa","Csb"]): { 75 };  // mixed cover
    case (_biome in ["Dfa","Dfb","Dfc"]):             { 72 };  // forest, frozen season
    case (_biome in ["BWh","BWk"]):                   { 91 };  // sparse desert crust
    case (_biome in ["BSh","BSk"]):                   { 85 };  // scrub, thin soil
    default                                           { 75 };
};
// The position falls back to the map origin when no unit exists, the same
// fallback updatePressure and calculateQNH use, so the curve number is
// deterministic on a headless server.
private _unit = call CBA_fnc_currentUnit;
private _pos = [0, 0];
if (!isNil "_unit" && {!isNull _unit}) then {
    _pos = getPos _unit;
};
private _surfaceClass = (surfaceType _pos) call EFUNC(material,classifyBySurfaceType);
// An impervious cover sheds almost everything, which is why a road floods
// and the field beside it does not.
_curveNumber = switch (true) do {
    case (_surfaceClass in ["concrete", "asphalt", "metal"]): { 98 };
    case (_surfaceClass == "water"):                          { 100 };
    case (_surfaceClass == "vegetation"):                     { _curveNumber - 5 };
    default                                                   { _curveNumber };
};
_curveNumber = _curveNumber min 100;

// ─── Rainfall to runoff (SCS Curve Number) ────────────────────────────────
// The Curve Number method is defined on a STORM TOTAL, not on a tick. A
// 5-second increment is far below the initial abstraction on its own, so
// applying it per tick yields exactly zero and the river never rises.
//
// aee_core_rainAccum is a decayed RATE proxy, not a depth: it tends to the
// engine rain value and saturates there. The storm depth is integrated
// here instead, and reset once the rain has stopped for a while, which is
// what makes one storm one event.
//
// rain 1.0 is the engine's heaviest fall. The mod treats that as 30 mm/h,
// the upper bound of the WMO "heavy rain" band, so the depth the interval
// delivered is rain * (30 / 3600) * interval mm.
private _rainIntensity = rain;
if !(_rainIntensity isEqualType 0) then { _rainIntensity = 0; };
private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
if !(_interval isEqualType 0) then { _interval = 5; };
private _mmPerTick = _rainIntensity * (30 / 3600) * _interval;

private _stormDepth = missionNamespace getVariable [QGVAR(stormDepth_mm), 0];
if !(_stormDepth isEqualType 0) then { _stormDepth = 0; };
private _dryTicks = missionNamespace getVariable [QGVAR(stormDryTicks), 0];
if !(_dryTicks isEqualType 0) then { _dryTicks = 0; };

if (_rainIntensity > 0.01) then {
    _stormDepth = _stormDepth + _mmPerTick;
    _dryTicks = 0;
} else {
    _dryTicks = _dryTicks + 1;
    // Six dry ticks is half a minute. The event closes and the counter
    // resets, so the next storm starts from its own abstraction.
    if (_dryTicks >= 6) then {
        _stormDepth = 0;
        _dryTicks = 0;
    };
};
missionNamespace setVariable [QGVAR(stormDepth_mm), _stormDepth];
missionNamespace setVariable [QGVAR(stormDryTicks), _dryTicks];

private _soilMoist = missionNamespace getVariable [QEGVAR(core,soilMoisture), 0.2];
if !(_soilMoist isEqualType 0) then { _soilMoist = 0.2; };
private _runoffTotalMm = [_stormDepth, _curveNumber, _soilMoist] call FUNC(calculateRunoffSCS);

// The cascade takes the INCREMENT of cumulative runoff, so a long storm
// delivers its water as it falls rather than all at the end.
private _runoffPrev = missionNamespace getVariable [QGVAR(runoffCumulative_mm), 0];
if !(_runoffPrev isEqualType 0) then { _runoffPrev = 0; };
if (_runoffTotalMm < _runoffPrev) then { _runoffPrev = 0; };
private _runoffMm = (_runoffTotalMm - _runoffPrev) max 0;
missionNamespace setVariable [QGVAR(runoffCumulative_mm), _runoffTotalMm];

// ─── Depression storage (bucket fill-spill) ───────────────────────────────
// Hollows fill before anything spills downstream. The capacity is the
// NRCS class value for the cover: a paved surface holds almost nothing.
private _dsCapacity = switch (true) do {
    case (_surfaceClass in ["concrete", "asphalt", "metal"]): { 1.5 };
    case (_surfaceClass == "rock"):                           { 3 };
    case (_surfaceClass == "vegetation"):                     { 7 };
    default                                                   { 5 };
};
private _stored = missionNamespace getVariable [QGVAR(depressionStore_mm), 0];
if !(_stored isEqualType 0) then { _stored = 0; };
private _storage = [_stored, _runoffMm, _dsCapacity] call FUNC(calculateDepressionStorage);
_storage params ["_newStored", "_spillMm"];
missionNamespace setVariable [QGVAR(depressionStore_mm), _newStored];

// ─── Nash cascade — three serial linear reservoirs ─────────────────────────
private _k = missionNamespace getVariable [QGVAR(riverResponseRate), 0.1];   // storage coefficient; 1/k = reservoir time constant
_k = _k * (_interval / 5);
private _reservoirs = missionNamespace getVariable [QGVAR(riverReservoirs), [0, 0, 0]];
private _r1 = _reservoirs select 0;
private _r2 = _reservoirs select 1;
private _r3 = _reservoirs select 2;

private _inflow = _spillMm;

_r1 = _r1 + _inflow - (_r1 * _k);
_r2 = _r2 + (_r1 * _k) - (_r2 * _k);
_r3 = _r3 + (_r2 * _k) - (_r3 * _k);
private _outflow = _r3 * _k;

missionNamespace setVariable [QGVAR(riverReservoirs), [_r1, _r2, _r3]];

// ─── Runoff depth to river STAGE (Manning rating) ─────────────────────────
// The cascade now carries MILLIMETRES of runoff, where it once carried a
// 0..1 rain intensity. The water level is STAGE, and stage relates to
// DISCHARGE through Manning's equation for a wide channel:

//   Q = (1/n) * b * h^(5/3) * sqrt(S)      discharge, m3/s
//   h = (Q * n / (b * sqrt(S)))^(3/5)      stage, m

// Source: Chow 1959, Open-Channel Hydraulics. n is the Manning roughness
// (0.035 for a natural channel), b the section width and S the bed slope.
// A river that rose linearly with rainfall would be wrong: stage goes as
// the three-fifths power of discharge, so the first rain lifts the level
// visibly and later rain lifts it less.
private _manningN = missionNamespace getVariable [QGVAR(manningN), 0.035];
if !(_manningN isEqualType 0) then { _manningN = 0.035; };
private _bedSlope = missionNamespace getVariable [QGVAR(bedSlope), 0.001];
if !(_bedSlope isEqualType 0) then { _bedSlope = 0.001; };
_manningN = _manningN max 0.005;
_bedSlope = _bedSlope max 0.00001;
private _riverWidthM = missionNamespace getVariable [QGVAR(riverSectionWidth_m), 4];
if !(_riverWidthM isEqualType 0) then { _riverWidthM = 4; };
_riverWidthM = _riverWidthM max 0.5;

// Discharge: the runoff depth over the contributing area, delivered over
// the interval, with the cascade's outflow as the fraction that arrives.
//
// The catchment is the area draining to this point. Issue #24 specifies
// D8 routing on the terrain heightmap at a 30-100 m step, and that step
// is the ROUTING cell, not the contributing area: a river's stage
// responds to everything upstream. A single 100 m cell gives 0.10 m of
// stage for 90 mm of rain, which is a ditch. The setting defaults to
// 0.25 km2, a small stream catchment, so the level sits in the range the
// flood thresholds describe.
private _catchmentM2 = missionNamespace getVariable [QGVAR(catchmentArea_m2), 250000];
if !(_catchmentM2 isEqualType 0) then { _catchmentM2 = 250000; };
_catchmentM2 = _catchmentM2 max 10000;
private _dischargeM3s = ((_outflow / 1000) * _catchmentM2) / (_interval max 1);

private _tideOffset = missionNamespace getVariable [QEGVAR(core,currentTideOffset_m), 0];
if (isNil "_tideOffset") then { _tideOffset = 0; };

// Tidal reach: full amplitude at the coast, falling to zero inland. The
// original code applied the offset uniformly and only described the reach
// in a comment, so a river 5 km inland rose with the tide.
//
// The coast distance is CACHED per 100 m cell (fnc_getCoastDistance). A
// per-tick terrain probe would cost up to 200 surfaceIsWater calls on
// every machine, which is the wrong cost model: this tick runs on every
// client in a large session. One walk per cell, then a lookup.
//
// The position falls back to the map origin when no unit exists, the same
// fallback updatePressure and calculateQNH use. The tide must NOT depend
// on a unit: core state is deterministic across machines by design, and a
// headless server would otherwise never feel it.
private _reachM = missionNamespace getVariable [QGVAR(tidalReach_m), 5000];
if !(_reachM isEqualType 0) then { _reachM = 5000; };
private _tideFactor = 0;
if (_tideOffset != 0 && _reachM > 0) then {
    private _coastDist = [_pos, _reachM] call EFUNC(environmental,getCoastDistance);
    _tideFactor = (1 - (_coastDist / _reachM)) max 0 min 1;
};

// The baseflow keeps a river running after the rain stops, which is why
// a stream carries water in a dry week. It adds to the discharge, so it
// is rated through the same curve rather than added to the stage.
private _gwStore = missionNamespace getVariable [QGVAR(groundwaterStore_mm), 0];
if !(_gwStore isEqualType 0) then { _gwStore = 0; };
private _gwRate = missionNamespace getVariable [QGVAR(baseflowRate_perDay), 0.2];
if !(_gwRate isEqualType 0) then { _gwRate = 0.2; };
private _recharge = _spillMm * 0.3;   // the share that enters the slow store
private _baseflow = [_gwStore, _recharge, _gwRate, _interval] call FUNC(calculateBaseflow);
_baseflow params ["_newGwStore", "_baseflowOut_mm"];
missionNamespace setVariable [QGVAR(groundwaterStore_mm), _newGwStore];
private _baseflowM3s = ((_baseflowOut_mm / 1000) * _catchmentM2) / (_interval max 1);

private _totalDischarge = _dischargeM3s + _baseflowM3s;
private _waterLevel = ((_totalDischarge * _manningN / (_riverWidthM * sqrt _bedSlope)) ^ 0.6) + (_tideOffset * _tideFactor);
_waterLevel = _waterLevel max 0;

private _floodRisk = switch (true) do {
    case (_waterLevel > 0.5): { "Severe" };
    case (_waterLevel > 0.3): { "Flood" };
    case (_waterLevel > 0.15): { "Elevated" };
    default                    { "None" };
};

missionNamespace setVariable [QEGVAR(core,currentWaterLevel), _waterLevel];
missionNamespace setVariable [QEGVAR(core,currentFloodRisk), _floodRisk];
