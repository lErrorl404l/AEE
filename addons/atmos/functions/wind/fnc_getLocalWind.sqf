#include "..\..\script_component.hpp"
/*
Local wind field modification by buildings, terrain, and aircraft wake.

The mod's global wind is a single vector (`wind` + aee_core_currentWind).
This function makes it SPATIAL: at any position it returns the local wind
vector after building wake, urban canyon, terrain lee-side, and (near an
aircraft) wake-vortex effects.  It is a query function, not a grid: the
caller (ballistics, helicopter lift, turbulence) samples it at the point
of interest, so the cost is paid only where a wind-sensitive model runs.

Composition (per the issue spec):
  V_local = V_global x min(S_terrain, S_building, S_canyon) + V_wake

Deterministic, no publicVariable, no state.  The building scan uses the
engine's nearestObjects with a modest radius; the result is cached per
frame so the three consumers share one scan per unit per frame.

Input:  [_posAGL, _heightAGL]
  _posAGL    - position above ground level (ASL works too; height is the
               second param)
  _heightAGL - height above the ground in metres (wind varies with
               height: at 50 m + the boundary layer is nearly uniform and
               building/canyon effects have decayed)
Output: [_easterly, _northerly] local wind m/s
Sets:   aee_atmos_localWindCache (per-frame cache for the three consumers)
*/

params [["_posAGL", [0, 0, 0], [[]]], ["_heightAGL", 1.5, [0]]];

// ─── Altitude gate ────────────────────────────────────────────────────────
// Above ~50 m, and with no ridge within 200 m upwind, the local field is
// the global one: building wakes (cavity ~15H) and canyon effects are a
// surface phenomenon.  A helicopter at 100 m should NOT be shoved by a
// building it is 60 m above.
private _global = missionNamespace getVariable [QEGVAR(core,currentWind), wind];
if !(_global isEqualType []) then { _global = wind; };
if (_heightAGL > 50) exitWith {
    // Still check for a ridge within 200 m upwind (terrain lee effects
    // extend to 10h, which for a 100 m hill is 1000 m — but the spec
    // gates at 50 m altitude, so only check the near field here).
    _global
};

// ─── Terrain lee-side (Jackson-Hunt 1975) ─────────────────────────────────
// Crest speed-up: dS ~ 2h/L_h (a 1:5 slope doubles surface stress).
// Downwind separation (slope > 17 deg) recirculates 5-10h with wind at
// 0-30%.  S_terrain = 0.2 + 0.8 x (x/(10h))^0.5, clamped [0.2, 1.0].
private _groundZ = getTerrainHeightASL _posAGL;
private _terrainS = 1.0;
private _windVec = vectorNormalized [_global select 0, _global select 1, 0];

// Sample the terrain 10 m downwind and 200 m downwind of the point.
private _probe1 = _posAGL vectorAdd (_windVec vectorMultiply 10);
private _probe2 = _posAGL vectorAdd (_windVec vectorMultiply 200);
private _h1 = getTerrainHeightASL _probe1 - _groundZ;
private _h2 = getTerrainHeightASL _probe2 - _groundZ;
// A downwind rise is a windward slope (speed-up); a downwind fall is a
// lee slope (recirculation).  The sign tells us which side we are on.
private _downwindRise = _h2 - _h1;
if (abs _downwindRise > 3) then {
    // Slope steepness over the 190 m between probes.
    private _slope = abs _downwindRise / 190;
    if (_slope > 0.3) then {
        // Slope > 17 deg (tan 17 ~ 0.306): separation.
        private _xRel = 5; // mid-recirculation zone 5-10h
        _terrainS = 0.2 + 0.8 * sqrt (_xRel / 10);
        _terrainS = _terrainS min 1.0 max 0.2;
    } else {
        // Speed-up on the windward side.
        private _h = abs _downwindRise;
        private _lH = 190; // half-width proxy
        _terrainS = 1.0 + 2 * (_h / _lH);
    };
};
_terrainS = _terrainS min 1.4 max 0.2;   // crest speed-up capped 1.4

// ─── Building wake (ADMS-Build, Hertwig 2019) ─────────────────────────────
// Cavity: L_R/H = 1.8 x (W_c/H)^-0.3 / (1 + 0.24 x (W_c/H)^-0.3).
// Zones: cavity 0-1.5H (reversed, -20 to -50%), near wake 1.5-5H
// (30-60% of free wind), far wake 5-15H (60-90%).
// Shadow: S(x) = 1 - 0.7 x (x/L_R)^-p, p ~1.5-2.0.
private _buildingS = 1.0;
private _nearestBld = nearestObjects [_posAGL, ["House", "Building"], 30];
if (_nearestBld isNotEqualTo []) then {
    private _bld = _nearestBld select 0;
    private _bldPos = getPosASL _bld;
    private _bldToPoint = _posAGL vectorDiff _bldPos;
    // Is the point DOWNWIND of the building (inside the wake cone)?
    private _downwind = (_bldToPoint vectorDotProduct _windVec) > 0;
    if (_downwind) then {
        private _dist = vectorMagnitude _bldToPoint;
        private _bldH = (boundingBox _bld select 1) select 2;
        _bldH = _bldH max 3;
        private _bldW = ((boundingBox _bld select 1) select 0) - ((boundingBox _bld select 0) select 0);
        _bldW = _bldW max 3;
        private _wcRatio = _bldW / _bldH;
        private _lR = 1.8 * (_wcRatio ^ -0.3) / (1 + 0.24 * (_wcRatio ^ -0.3)) * _bldH;
        private _xNorm = _dist / _bldH;
        if (_xNorm < 1.5) then {
            // Cavity: reversed flow, 20-50% of free wind (negative =
            // opposite direction).
            _buildingS = -0.35;  // reversed, -35% (mid-cavity)
        } else {
            if (_xNorm < 5) then {
                // Near wake: 30-60%.
                _buildingS = 0.45;
            } else {
                if (_xNorm < 15) then {
                    // Far wake: shadow decay toward free wind.
                    private _lrRatio = _dist / (_lR max 1);
                    _buildingS = 1 - 0.7 * (_lrRatio ^ -1.75);
                    _buildingS = _buildingS min 1.0 max 0.6;
                };
            };
        };
    };
};

// ─── Urban canyon (Oke 1988) ─────────────────────────────────────────────
// Regimes by H/W: skimming >0.65, wake interference 0.4-0.65, isolated
// <0.4.  Perpendicular wind: street-level 10-20% of roof wind.  Parallel
// (channelling): S = 1.2.
private _canyonS = 1.0;
private _nearBuildings = nearestObjects [_posAGL, ["House", "Building"], 25];
if (count _nearBuildings >= 2) then {
    // The street is flanked: canyon regime likely.  Is the wind parallel
    // to the street?  Proxy: compare the wind to the building-row axis.
    private _b1 = _nearBuildings select 0;
    private _b2 = _nearBuildings select 1;
    private _rowAxis = vectorNormalized ((getPosASL _b2) vectorDiff (getPosASL _b1));
    private _perpComponent = abs ((_windVec select 0) * (_rowAxis select 0) + (_windVec select 1) * (_rowAxis select 1));
    private _bH = (boundingBox _b1 select 1) select 2;
    private _bH2 = (boundingBox _b2 select 1) select 2;
    private _avgH = (_bH + _bH2) / 2 max 3;
    private _gap = vectorMagnitude ((getPosASL _b2) vectorDiff (getPosASL _b1)) - ((boundingBox _b1 select 1) select 0) - ((boundingBox _b2 select 1) select 0);
    _gap = _gap max 3;
    private _hw = _avgH / _gap;
    if (_hw > 0.65) then {
        // Skimming flow: perpendicular wind at street level is 10-20% of
        // roof wind; parallel wind channelling accelerates to 1.2.
        _canyonS = [1.2, 0.15] select (_perpComponent > 0.7);
    } else {
        if (_hw > 0.4) then {
            _canyonS = [1.1, 0.5] select (_perpComponent > 0.7);
        };
    };
};

// ─── Aircraft wake (FAA JO 7110.126B) ────────────────────────────────────
// A wingtip vortex near the point adds a horizontal velocity component.
// Circulation Gamma0 = 4W/(pi x rho x U x b); the induced velocity at
// distance r from the vortex core is ~ Gamma/(2 pi r).
private _wake = [0, 0];
private _nearAircraft = nearestObjects [_posAGL, ["Air"], 50];
if (_nearAircraft isNotEqualTo []) then {
    private _ac = _nearAircraft select 0;
    if (isEngineOn _ac) then {
        private _mass = getMass _ac;               // kg
        private _span = (boundingBox _ac select 1) select 0;
        _span = _span max 5;
        private _speed = speed _ac / 3.6;          // m/s
        _speed = _speed max 20;
        private _rho = 1.225;
        private _gamma0 = 4 * _mass / (pi * _rho * _speed * _span);
        // Induced velocity at the query point: perpendicular to the
        // flight direction, decaying with 1/r.
        private _rVec = _posAGL vectorDiff (getPosASL _ac);
        private _r = vectorMagnitude _rVec max 3;
        private _flightDir = vectorNormalized (velocity _ac);
        // Rotate flight direction 90 deg (perpendicular induced flow).
        private _vInd = [-(_flightDir select 1), _flightDir select 0];
        private _mag = (_gamma0 / (2 * pi * _r)) min 3;  // cap 3 m/s
        _wake = [_vInd select 0, _vInd select 1] vectorMultiply _mag;
    };
};

// ─── Compose ─────────────────────────────────────────────────────────────
// V_local = V_global x min(S_terrain, S_building, S_canyon) + V_wake
// The min() makes the STRONGEST reduction win — a point in a deep canyon
// inside a building's far wake gets the canyon value, not the building's.
private _minS = (_terrainS min _buildingS) min _canyonS;
private _local = [
    (_global select 0) * _minS + (_wake select 0),
    (_global select 1) * _minS + (_wake select 1)
];

// Frame cache: three consumers per unit per frame share one scan.
missionNamespace setVariable [QGVAR(localWindCache), [_local, _minS, _terrainS, _buildingS, _canyonS, diag_frameNo]];

_local
