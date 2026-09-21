#include "..\..\script_component.hpp"
/*
Per-selection physics-driven thermal apply (issue #124).

Replaces the rvmat TI-stage swap (ti_cloth_cold/hot, the #123 bug
class) with a procedural per-selection thermal image.

Mechanism (verified against A3TI's fn_setObjects.sqf): each model
selection's texture channel is flattened to a procedural colour
string `#(rgb,8,8,3)color(b,b,b,1)` via setObjectTexture.  The engine
composites it exactly like a painted texture, but the colour comes
from physics, not a .paa/.rvmat.

FLIR mapping (real sensor physics):
  - the sensor reads RADIANCE, not temperature: radiance = eps*sigma*T^4.
    A low-emissivity surface (polished metal ~0.1) at 100 C radiates
    like a black body at ~56 C, so the sensor reports
      T_apparent = T * eps^(1/4)        [Stefan-Boltzmann, emissivity
                                          correction - the "cold shiny
                                          metal" effect FLIR manuals warn
                                          about]
  - white-hot palette: brightness b = clamp((T_apparent - T_lo) /
    (T_hi - T_lo), 0, 1), with the sensor gain window T_lo=-40 C,
    T_hi=+150 C (typical ground-target auto-gain span).  Black = cold,
    white = hot - the real white-hot mode.
  - the colour is greyscale (b,b,b) because white-hot carries no hue;
    colour variants (ironbow/rainbow) are a post-process tint, handled
    by the sensor pipeline, not per-object.

Multiplayer: setObjectTexture is LOCAL, correct here - each client
renders its own thermal pass from identical physics (the existing
object-temperature solver runs everywhere), so every client applies the
same texture and every player sees the same thermal image.

Cost: one setObjectTexture per thermal selection per throttle tick
(0.05 s in the existing thermal contrast pass), NOT per frame.  The
original textures are saved on first apply and restored on EXIT, same
pattern as fnc_applyClothingThermal.

Arguments:
  0: object (OBJECT)
  1: selection name (STRING) - "" for whole-object fallback
  2: mode (STRING, optional) - "EXIT" restores saved textures
  3: internal heat (NUMBER, optional, W/m2) - engine/exhaust/friction
     per selection, default 0 (solar + ambient only)
  4: ground view factor (NUMBER, optional, 0..1) - the MRT ground
     weight for the radiation term; a tyre sees ~0.7 ground, a roof
     ~0.3, a standing soldier 0.5
*/
params ["_obj", "_selection", ["_mode", ""], ["_qInternal", 0, [0]], ["_fGround", 0.5, [0]], ["_massScale", 1, [0]]];

if (_mode == "EXIT") then {
    // ─── EXIT: restore every saved texture AND material ─────────────────────
    // Runs BEFORE the object guard: the EXIT path is global (restores every
    // saved object), so callers may invoke it with a dummy object, e.g.
    // fnc_applyBuildingThermal's mode-off handler calls ["", "", "EXIT"].
    //
    // The material restore is mandatory: the TI band rvmat (StageTI = the
    // physics colour) replaces the object's real material while TI is
    // active.  Restoring it returns the day view, damage states and any
    // modded multi-stage material to the player who had TI enabled - the
    // swap is CLIENT-LOCAL, so other players' views were never changed.
    private _saved = missionNamespace getVariable [QGVAR(selThermalSaved), []];
    {
        _x params ["_o", "_oldTexs", "_oldMats", "_selNames"];
        if (!isNull _o) then {
            private _selIdx = 0;
            {
                if (_selIdx < count _oldTexs && {(_oldTexs select _selIdx) isEqualType ""}) then {
                    _o setObjectTexture [_selIdx, _oldTexs select _selIdx];
                };
                if (_selIdx < count _oldMats && {(_oldMats select _selIdx) isEqualType ""}) then {
                    _o setObjectMaterial [_selIdx, _oldMats select _selIdx];
                };
                _selIdx = _selIdx + 1;
            } forEach _selNames;
        };
    } forEach _saved;
    missionNamespace setVariable [QGVAR(selThermalSaved), []];
} else {
    if (isNull _obj || {!hasInterface}) exitWith { 0 };

    // ─── Solve and apply ──────────────────────────────────────────────────
    // The selection arg is a NAME (string), an INDEX (number from the
    // callers' hiddenSelections loop), or "" (all selections).  A
    // number-vs-string comparison throws in SQF, so resolve the type
    // before the empty check.
    private _selNames = [];
    if (_selection isEqualType 0) then {
        private _allSels = selectionNames _obj;
        if (_selection >= 0 && {_selection < count _allSels}) then {
            _selNames = [_allSels select _selection];
        };
    } else {
        _selNames = if (_selection == "") then { [] } else { [_selection] };
    };
    if (_selNames isEqualTo []) then {
        _selNames = selectionNames _obj;
    };

    // Save originals once per object per pass (first apply).  Materials
    // are captured too: the FPN rvmat replaces them while thermal is
    // active (issue #204 - perlinNoise Stage2 FPN over the painted heat
    // colour), and EXIT restores them.  Texture-only when FPN is off.
    private _saved = missionNamespace getVariable [QGVAR(selThermalSaved), []];
    private _alreadySaved = _saved findIf { (_x select 0) == _obj };
    private _fpnEnabled = missionNamespace getVariable [QGVAR(thermalFPN), true];
    if (_alreadySaved < 0) then {
        private _oldTexs = getObjectTextures _obj;
        private _oldMats = getObjectMaterials _obj;
        _saved pushBack [_obj, _oldTexs, _oldMats, _selNames];
        missionNamespace setVariable [QGVAR(selThermalSaved), _saved];
        // FPN material swap (client-local, once per object per pass):
        // the perlinNoise Stage2 multiplies over the painted heat colour.
        // Skipped when the object has no material slots (ground/terrain
        // cannot take a material swap - the proxy-plane overlay is the
        // terrain path).  Only slots with a string material are swapped
        // (matches the EXIT restore guard below).
        if (_fpnEnabled && _oldMats isNotEqualTo []) then {
            private _fpnMat = "\z\aee\addons\thermal\data\ti_fpn.rvmat";
            {
                if (_x isEqualType "") then {
                    _obj setObjectMaterial [_forEachIndex, _fpnMat];
                };
            } forEach _oldMats;
        };
    };

    // Ambient + wind + solar from the core environment state.
    private _tAir = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
    private _wind = vectorMagnitude (missionNamespace getVariable [QEGVAR(core,currentWind), [0,0,0]]);
    private _solar = missionNamespace getVariable [QEGVAR(core,currentSolarFlux), 0];

    {
        private _sel = _x;
        private _idx = (selectionNames _obj) find _sel;
        if (_idx < 0) then { continue; };

        // Shade exposure: roof/upper selections get full sun, lower panels
        // less (self-shadow).  Refined by the object's existing shade ray.
        private _exposure = 1;
        if (_sel find "wheel" >= 0 || {_sel find "undercarriage" >= 0}) then {
            _exposure = 0.15;   // tyres/undercarriage: mostly self-shadowed
        };

        // Current per-selection temperature from the object solver state.
        private _stateKey = format ["%1|%2", str _obj, _sel];
        private _tCurrent = missionNamespace getVariable [QGVAR(selTemperature), createHashMap] getOrDefault [_stateKey, _tAir];

        // ─── Two-node path (issue #191) ─────────────────────────────────────
        // Core-bearing selections solve core+skin coupled (Gagge
        // two-node), NOT the single-node surface-only balance.  The
        // human path is wired now - the Gagge model is fully validated
        // against its published set points.  Engine and building-mass
        // two-node stay on the surface path until their fitted models
        // land: the engine needs a per-engine coolant-loop fit
        // (Bohac 1996 / Jarrier 2000 lumped-RC, no canonical constants),
        // and building mass needs the ISO 52016 envelope+mass topology.
        private _tNew = _tAir;
        if (_obj isKindOf "CAManBase") then {
            private _mrt = [getPosASL _obj, _fGround] call FUNC(calculateMRT);
            // 1 met = 58.2 W/m2 over DuBois 1.8258 m2 = 106.3 W TOTAL
            // (Gagge, native vanilla resting metabolism - no ACM
            // dependency).  qGen is TOTAL W, matching the W/K coupling
            // in the core balance.
            private _qMet = 58.2 * 1.8258;

            // ─── Blood-volume physiology (issue #196) ────────────────────────
            // VO2 - and so metabolic heat - is FLAT until DO2crit, the
            // oxygen-delivery limit, then collapses.  DO2crit is reached
            // at ~50% blood volume loss (Guyton & Hall; ATLS class III
            // starts at 30% loss, class IV at 40%): above the limit the
            // circulation delivers oxygen and heat production holds at
            // basal; below it the body falls back to anaerobic ATP
            // (Seekamp 1999) and heat production falls toward zero.  A
            // corpse makes none at all.  The old surface path scaled
            // metabolism linearly from the first drop of blood - the
            // physiology says it holds until DO2crit.  (ACE
            // ace_medical_bloodVolume, 6.0 L full; vanilla fallback.)
            private _bloodVol = _obj getVariable ["ace_medical_bloodVolume", 6.0];
            if !(_bloodVol isEqualType 0) then { _bloodVol = 6.0; };
            private _bloodFrac = (_bloodVol max 0 min 6) / 6.0;
            private _metabFrac = if (_bloodFrac >= 0.5) then { 1 } else { _bloodFrac / 0.5 };
            if (!alive _obj) then { _metabFrac = 0; };
            _qMet = _qMet * _metabFrac;

            // ─── Water immersion state (issue #193) ──────────────────────────
            // Immersion = below the water surface at a water position.
            // getPosASL z negative = submerged; surfaceIsWater confirms
            // the position is a water body.  Water temperature from the
            // core state (fnc_calculateWaterTemperature, leaky
            // integrator toward air).  Water speed: no native current
            // state exists - still water (speed 0) is the honest
            // default, giving the Boutelier still-water coefficient.
            private _waterSpeed = 0;
            private _tWater = -1;
            private _posASL = getPosASL _obj;
            if ((_posASL select 2) < 0) then {
                if (surfaceIsWater _posASL) then {
                    _tWater = missionNamespace getVariable [QEGVAR(core,currentWaterTemperature), _tAir];
                };
            };
            // Rain rate (0..1) from the engine's built-in rain command - the
            // native weather state, external wettedness driver for the
            // evaporative path.
            private _rain = rain;

            // The loadout flux scales the skin mass: a carried item with
            // more thermal inertia (a full backpack) warms and cools
            // slower - the skin-mass time constant grows with the
            // carried mass (issue #204).
            private _skinMass = (0.1 * 70) * (_massScale max 0.2 min 3);

            private _two = [
                _obj, _sel,
                "human", "human",       // core class, skin class
                _tAir, _wind, _solar, _exposure,
                0.9 * 70, _skinMass,    // core/skin mass (loadout-scaled)
                1.8258,                 // DuBois area (m2)
                0.15,                   // convection plate dim (m)
                _tCurrent, _tCurrent,   // core/skin current temps
                _qMet,                  // qGen: resting metabolism (W)
                "vertical", 0.5, _mrt, true, 0.05, true, 5,
                _waterSpeed, _tWater, _rain, _bloodFrac
            ] call FUNC(solveTwoNodeSelection);
            _tNew = _two select 1;      // skin temp - what FLIR sees
        } else {
            // ─── Inert objects (vehicles, buildings): two-node path ────────
            // The single-node surface solve is OBSOLETE - the two-node
            // solver subsumes it with isHuman=false.  The physics is
            // BETTER: _qInternal (engine 770 / wheels 280 W/m2) enters
            // the CORE node and conducts through the panel wall to the
            // skin - a vehicle panel does not generate heat, it
            // conducts engine heat from inside.  This is the correct
            // model and it removes the NaN-prone single-node Newton.
            private _matClass = [_obj, _sel] call FUNC(getSelectionMaterials);
            private _area = 6;                    // default panel area (m2)
            private _lCond = 0.008;               // 8mm panel/block wall (m)
            private _qGenCore = _qInternal * _area;
            private _two = [
                _obj, _sel,
                _matClass, _matClass,
                _tAir, _wind, _solar, _exposure,
                50, 20,                          // core/skin mass (kg, lumped panel)
                _area, _lCond * 10,              // area, convection plate dim
                _tCurrent, _tCurrent,
                _qGenCore,                       // engine heat into the CORE (W)
                "vertical", 0.5, _tCurrent, false, _lCond, false, 5
            ] call FUNC(solveTwoNodeSelection);
            _tNew = _two select 1;               // skin temp - what FLIR sees
        };

        // Persist for the next tick's inertia term.  NaN-guard the
        // stored value too: a NaN persisted here would poison the state
        // forever (every later tick reads it back as _tCurrent).  The
        // `finite` command is the only reliable SQF NaN check - NaN
        // comparisons are all false.  A NaN here means a state read
        // returned nil upstream (the #189 class).  Log the inputs so a
        // recurrence is diagnosable, then fall back to ambient.
        if !(finite _tNew) then {
            diag_log format [
                "[AEE] NaN tNew: obj=%1 sel=%2 tAir=%3 tCurrent=%4 qInternal=%5 mode=%6",
                _obj, _sel, _tAir, _tCurrent, _qInternal, _mode
            ];
            _tNew = _tAir;
        };
        private _selMap = missionNamespace getVariable [QGVAR(selTemperature), createHashMap];
        _selMap set [_stateKey, _tNew];
        missionNamespace setVariable [QGVAR(selTemperature), _selMap];

        // ─── FLIR display mapping (issue #196) ─────────────────────────────
        // Real FLIR reads BAND RADIANCE, not temperature: the sensor
        // signal is the Planck integral over 8-14 um with an emissivity
        // and reflection term (FLIR T810442), and the display maps the
        // SCENE's actual radiance window onto the full grey range via
        // scene-adaptive AGC (linear with 1% tail rejection, IIR-smoothed
        // - FLIR Camera Adjustments app note).  The old `T * eps^0.25`
        // with a fixed -40..150 C window was the wrong physics twice: the
        // eps^0.25 form is total-power Stefan-Boltzmann, not band-limited
        // radiance, and the fixed window rendered every night scene white
        // (a few-kelvin spread across 190 C of range).
        //
        // The AGC window is computed per frame by fnc_updateThermalAGC
        // (called from the sensor tick before this pass) from the same
        // per-selection temperature state this loop writes.  The window
        // is in RADIANCE units, so the selection's radiance maps through
        // it directly.
        private _mat = ([_obj, _sel] call FUNC(getSelectionMaterials)) call FUNC(getMaterialThermal);
        private _eps = _mat select 0;
        private _rad = [_tNew, _eps, _tAir, _fGround, _tCurrent] call FUNC(calculateBandRadiance);
        private _agcMin = missionNamespace getVariable [QGVAR(agcRadMin), -1];
        private _agcMax = missionNamespace getVariable [QGVAR(agcRadMax), -1];
        // Fallback window (first frames / no AGC yet): the radiance of
        // the old -40..150 C span - identical behaviour to the previous
        // fixed window until the AGC warms up.
        if (!(_agcMin isEqualType 0) || !(_agcMax isEqualType 0) || _agcMin >= _agcMax) then {
            _agcMin = [-40, _eps, _tAir, _fGround, _tCurrent] call FUNC(calculateBandRadiance);
            _agcMax = [150, _eps, _tAir, _fGround, _tCurrent] call FUNC(calculateBandRadiance);
        };
        private _b = ((_rad - _agcMin) / ((_agcMax - _agcMin) max 1e-6)) max 0 min 1;
        // Polarity (WHOT/BHOT) is applied by a ColorInversion ppEffect in
        // fnc_applyThermalVision (the proven A3TI/MKK mechanism) - NOT a
        // brightness flip here.  A `_b = 1-_b` flip of the band index
        // never reached the rendered image for StageTI-baked objects (the
        // 'WHOT/BHOT no visual difference' report, issue #204).
        // TRACE: log the full pipeline every call so a bad value is
        // visible even if `finite` does not flag it.  Throttled to the
        // first 20 calls per object to keep the RPT readable.
        private _traceKey = format ["%1_%2", _obj, _sel];
        private _traceN = missionNamespace getVariable [QGVAR(traceCount), createHashMap];
        private _n = _traceN getOrDefault [_traceKey, 0];
        if (_n < 20) then {
            _traceN set [_traceKey, _n + 1];
            missionNamespace setVariable [QGVAR(traceCount), _traceN];
            diag_log format [
                "[AEE][TRACE] obj=%1 sel=%2 mat=%3 eps=%4 tNew=%5 rad=%6 agc=%7..%8 b=%9 qInt=%10 finite_b=%11",
                _obj, _sel, _mat, _eps, _tNew, _rad, _agcMin, _agcMax, _b, _qInternal, finite _b
            ];
        };
        // NaN guard: SQF NaN comparisons are false (NaN != NaN is also
        // false in SQF), so max/min AND a self-compare CANNOT clamp a
        // NaN - it would emit "#(rgb,8,8,3)color(scalar NaN,..)" and
        // the engine rejects the texture.  The `finite` command is the
        // only reliable check.  A NaN here means a state read returned
        // nil upstream (the #189 class); fall back to ambient.
        if !(finite _b) then {
            diag_log format [
                "[AEE] NaN brightness: obj=%1 sel=%2 tNew=%3 eps=%4 rad=%5",
                _obj, _sel, _tNew, _eps, _rad
            ];
            _b = 0;
        };

        // ─── Heat-colour texture paint (issue #204, MKK mechanism) ────────
        // The vanilla TI mode renders the material's Stage1 TEXTURE.  The
        // proven thermal mods (MKK 3753145363 fnc_setThermalMaterials,
        // A3TI 2041057379 fn_setObjects) paint the heat as a procedural
        // colour via setObjectTexture - a WHOT-red base [1,0.10,0.20]
        // scaled by the heat state, quantised to N levels to stop the
        // engine re-creating the texture every refresh.  The original
        // material is KEPT (MKK THERMAL_RED default: texture only, no
        // material swap) so damage states and modded multi-stage materials
        // survive.
        //
        // The old approach swapped the material to grey-band rvmats with a
        // grey Stage1: the grey composited over the vanilla TI rendered
        // flat and never carried the heat colour into the image (the
        // 'WHOT/BHOT no visual difference' report).  The heat colour
        // replaces it - the same quantisation, now with the correct colour
        // in the texture the TI pass actually reads.
        //
        // WHOT (brightness): hot = red.  The base colour scales with the
        // AGC-normalised radiance; polarity (BHOT) is applied by a
        // ColorInversion ppEffect in fnc_applyThermalVision, NOT a
        // brightness flip here - a flip of the band index never reached
        // the rendered image for StageTI-baked objects.
        // Quantise to 32 levels (MKK TI_VEHICLE_HEAT_TEXTURE_LEVELS) so a
        // 0.066 heat step is invisible but the texture is not recreated
        // on every tick (the engine re-paints the procedural texture
        // each time the value changes).
        private _levels = 32;
        private _qb = (round ((_b max 0 min 1) * (_levels - 1))) / (_levels - 1);
        private _heatCol = [
            1.0 * _qb,
            0.10 * _qb,
            0.20 * _qb
        ];
        private _colour = format [
            "#(rgb,8,8,3)color(%1,%2,%3,1)",
            _heatCol select 0,
            _heatCol select 1,
            _heatCol select 2
        ];

        _obj setObjectTexture [_idx, _colour];
        // The material stays the object's own (or the FPN rvmat when the
        // thermalFPN setting is on - see the save block).  setObjectTexture
        // replaces the Stage1 texture of whatever material is current, so
        // the heat colour renders over Stage1 and (with FPN) the perlinNoise
        // Stage2 multiplies over it.
    } forEach _selNames;
};

0
