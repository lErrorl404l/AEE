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
private _perfT0 = diag_tickTime;
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
    // The repaint gate is per object and per selection, so a stale entry would
    // suppress the first repaint after a re-entry and leave the restored day
    // texture on screen.
    missionNamespace setVariable [QGVAR(paintGate), createHashMap];
    missionNamespace setVariable [QGVAR(paintBands), createHashMap];
} else {
    if (isNull _obj || {!hasInterface}) exitWith { 0 };

    // ─── Repaint gate, resolved before the per-selection setup ──────────────
    // The gate needs only the object and the mode, so it is computed here,
    // ahead of everything below.  The setup (selectionNames, getObjectTextures,
    // getObjectMaterials, boundingBoxReal, the atmospheric-transmission kernel
    // and the loadout walk) used to run on EVERY 10 Hz call even when the solve
    // was not due: the gate sat after it, so only the solve and the paint were
    // skipped.  The counter dump put applyBuildingThermal at 4 ms/call
    // (40 ms/s) while the vehicle-heat model read 0 ms and the per-call solve
    // measured sub-millisecond, which places the cost in that repeated setup.
    // A not-due call now returns before it.  No physics moves: the solve path,
    // the gate keys and the stamp cadence are unchanged, and the first due call
    // still saves the originals before it paints.
    //
    // The gate is two things, and neither changes the image:
    //   Cadence.  Surface temperatures run on time constants of 600 s and
    //   longer, so the 10 Hz per-frame repaint is wasted.  The solve is an
    //   elapsed-time relaxation, so evaluating it at the repaint cadence
    //   instead of 10 Hz is physics-neutral.
    //   Change detection.  The colour is quantised to 32 levels, so a
    //   selection whose band has not moved cannot look different.
    //
    // Impulse callers pass mode "FORCE" (muzzle flash, detonation) so an
    // event is never held for the cadence.
    //
    // THE GATE IS PER OBJECT AND PER SELECTION, matching the per-selection
    // band map below.  The building and clothing callers walk their selection
    // list and call this function once per entry, so an object-keyed gate let
    // only the first entry of each pass through and every later part kept the
    // FPN material with no heat colour - the flat vehicle and flat clothing
    // report.  The selection argument is part of the key: a named or indexed
    // call keys on that selection, and the "" all-selection form keeps one key
    // for the whole object.  A FORCE call still bypasses the cadence.
    private _objKey = str _obj;
    private _gateSel = if (_selection isEqualType 0) then { str _selection } else { _selection };
    private _gateKey = _objKey + "|" + _gateSel;
    private _gate = missionNamespace getVariable [QGVAR(paintGate), -1];
    if (_gate isEqualType 0) then {
        _gate = createHashMap;
        missionNamespace setVariable [QGVAR(paintGate), _gate];
    };
    private _bands = missionNamespace getVariable [QGVAR(paintBands), -1];
    if (_bands isEqualType 0) then {
        _bands = createHashMap;
        missionNamespace setVariable [QGVAR(paintBands), _bands];
    };
    private _lastPaint = _gate getOrDefault [_gateKey, 0];
    private _interval = 1 / (missionNamespace getVariable [QGVAR(repaintHz), 4]);
    private _forced = (_mode == "FORCE");
    private _due = _forced || {(diag_tickTime - _lastPaint) >= _interval};
    if (!_due) exitWith { 0 };

    // The heat paint is a FLIR look, so it belongs to thermal vision alone.
    // This function is the single choke point for the paint and it had no
    // vision gate at all.  Two callers reach it in every vision mode: the
    // fired handler runs applyWeaponBarrelHeat unconditionally, twelve lines
    // before its own NVG gate, and that function paints the PLAYER, whose
    // weapon selections are the operator's own uniform.  The hitPart handler
    // stamps impacts with no gate either.  So firing a round in daylight
    // repainted the shooter red, and no teardown ever ran to undo it because
    // no sensor session had started.  Gate the VISUAL writes on the live
    // mode and keep the solve below them unconditional: barrel heat still
    // accumulates, so thermal vision opens on an already-hot weapon and the
    // AGC still reads a real radiance window.
    private _thermalOn = false;
    private _viewer = call CBA_fnc_currentUnit;
    if (!isNull _viewer && {currentVisionMode _viewer == 2}) then { _thermalOn = true };

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
    // Saving and the FPN material swap are both visual state, so they are
    // gated with the paint.  Saving in normal vision would also poison the
    // swap: the swap sits below and is skipped once a save exists, so an
    // ungated save here would leave the FPN rvmat unapplied when thermal
    // vision finally came on.
    if (_thermalOn && _alreadySaved < 0) then {
        private _oldTexs = getObjectTextures _obj;
        private _oldMats = getObjectMaterials _obj;
        // Store the model's FULL selection list, not this call's slice: the
        // per-selection gate lets each selection paint in its own call, so
        // EXIT must restore every slot the paint can write.  Positions in
        // selectionNames are the indices the paint writes (it resolves _idx
        // with `selectionNames _obj find _sel`), so a sequential restore over
        // the full list is symmetric.
        _saved pushBack [_obj, _oldTexs, _oldMats, selectionNames _obj];
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

    // Atmospheric path state, resolved ONCE per object: range and the
    // humidity/fog/air-density trio set the 8-14 um transmission every
    // selection on this object shares.  Same core-state lookups the other
    // thermal consumers read; no second environment model.
    private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
    private _fog = missionNamespace getVariable [QEGVAR(core,currentFogDensity), 0];
    private _airDensity = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
    private _rangeM = if (isNull _viewer) then { 0 } else { _obj distance _viewer };
    private _tau = [_rangeM, _humidity, _tAir, _fog, rain, _airDensity] call FUNC(calculateAtmosphericTransmission);
    if (_tau < 0) then { _tau = 1; };   // unusable input: transmissive fallback

    // Original textures: while thermal paint is active getObjectTextures
    // returns a procedural colour, so the saved original is the solar
    // absorptance fallback.
    private _savedTexs = [];
    {
        if ((_x select 0) == _obj) then { _savedTexs = _x select 1; };
    } forEach (missionNamespace getVariable [QGVAR(selThermalSaved), []]);

    // Worn clothing insulation (clo) from the real per-unit registry
    // (fnc_getEquipmentProperties combined slot).  Cached per uniform so the
    // inventory walk runs once per garment, not every tick.
    private _cloWorn = 0;
    if (_obj isKindOf "CAManBase") then {
        private _cloCache = missionNamespace getVariable [QGVAR(clothingCloCache), -1];
        if (_cloCache isEqualType 0) then {
            _cloCache = createHashMap;
            missionNamespace setVariable [QGVAR(clothingCloCache), _cloCache];
        };
        private _cloKey = str _obj;
        private _cloEntry = _cloCache getOrDefault [_cloKey, []];
        private _cloUni = uniform _obj;
        if ((count _cloEntry) == 2 && {(_cloEntry select 0) == _cloUni}) then {
            _cloWorn = _cloEntry select 1;
        } else {
            private _uniformClo = [_obj] call EFUNC(physiology,getUniformProperties);
            _cloWorn = if (_uniformClo isEqualType [] && {(count _uniformClo) > 3}) then { _uniformClo select 3 } else { 0 };
            if !(_cloWorn isEqualType 0) then { _cloWorn = 0; };
            _cloCache set [_cloKey, [_cloUni, _cloWorn]];
            missionNamespace setVariable [QGVAR(clothingCloCache), _cloCache];
        };
    };

    // Per-object constants, resolved once instead of once per selection.  The
    // model geometry and the blood model are identical for every selection of
    // an object, so the per-selection calls were pure repeated cost.
    //
    // Convection characteristic length: the natural-convection correlation
    // integrates over the plate's real vertical extent, not wall thickness.
    // Rayleigh scales as L^3 and laminar h as L^(-1/4), so a fixed 0.08 m
    // over-predicted h by about 2x on a 1.5 m panel.
    private _bbRealObj = boundingBoxReal _obj;
    private _lCharObj = abs (((_bbRealObj select 1) select 2) - ((_bbRealObj select 0) select 2));
    if (_lCharObj < 0.1) then {
        // Degenerate bbox: fall back to the visual bounding box.
        private _bbVisObj = boundingBox _obj;
        _lCharObj = abs (((_bbVisObj select 1) select 2) - ((_bbVisObj select 0) select 2));
    };
    // Last resort for a model reporting no extent: the engine's own size hint,
    // floored so the solver never divides by zero.
    if (_lCharObj < 0.1) then { _lCharObj = (sizeOf _obj) max 0.1; };
    private _vSpeedObj = abs speed _obj;
    private _oxObj = [];

    private _uploaded = 0;

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
        // Eager-default allocation removed; the writer path already uses the
        // lazy -1 form.
        private _tempMap = missionNamespace getVariable [QGVAR(selTemperature), -1];
        if (_tempMap isEqualType 0) then { _tempMap = createHashMap; };
        private _tCurrent = _tempMap getOrDefault [_stateKey, _tAir];

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
        private _tCoreNew = _tAir;
        // One radiative field for this selection, from its own ground view
        // factor.  The solver consumes it directly and must not re-derive MRT.
        private _mrt = [getPosASL _obj, _fGround] call FUNC(calculateMRT);
        if (_obj isKindOf "CAManBase") then {
            // Metabolic rate: resting 1 met = 58.2 W/m2 (Gagge 1986) over
            // DuBois 1.8258 m2, plus movement heat.  qGen is TOTAL W,
            // matching the W/K coupling in the core balance.  The movement
            // terms mirror fnc_calculateObjectTemperature so both thermal
            // paths agree (the movement model itself is an open item: no
            // published speed-to-metabolism relation is in the repo).
            private _vSpeed = _vSpeedObj;
            private _metabMove = switch (true) do {
                case (_vSpeed > 6):   { 120 };
                case (_vSpeed > 3):   {  60 };
                case (_vSpeed > 0.5): {  20 };
                default               {   0 };
            };
            private _qMet = 58.2 * 1.8258 + _metabMove;

            // ─── Oxygen delivery (issue #196) ────────────────────────────────
            // One blood model, shared with fnc_calculateObjectTemperature
            // through aee_physiology_fnc_calculateOxygenDelivery.  CO carries
            // the acute loss, [Hb] relaxes over hours.  The metabolic
            // fraction scales oxidative heat, the perfusion index scales
            // skin blood flow.
            // Solve once per object, not once per selection.  This is
            // physics-neutral: calculateOxygenDelivery advances [Hb] on ELAPSED
            // TIME and stamps the new tick time back into its state entry, so
            // the second and later calls in a tick saw _elapsed == 0 and
            // returned without touching [Hb] anyway.
            if (count _oxObj == 0) then {
                _oxObj = [_obj, _qMet, 1.8258] call EFUNC(physiology,calculateOxygenDelivery);
            };
            private _ox = _oxObj;
            private _metabFrac = _ox select 6;
            if (!alive _obj) then { _metabFrac = 0; };
            _qMet = _qMet * _metabFrac;

            // ─── Water immersion state (issue #193) ──────────────────────────
            // Immersion = below the water surface at a water position.
            // The water temperature IS the immersion signal (dry sentinel
            // -273); water speed has no native current state, so still water
            // (0) is the honest default.  Water temperature from the core
            // state (fnc_calculateWaterTemperature).
            private _waterSpeed = 0;
            private _tWater = -273;
            private _posASL = getPosASL _obj;
            if ((_posASL select 2) < 0 && {surfaceIsWater _posASL}) then {
                _tWater = missionNamespace getVariable [QEGVAR(core,currentWaterTemperature), _tAir];
                if !(_tWater isEqualType 0) then { _tWater = _tAir; };
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

            // Core state persists separately from the skin: the two nodes
            // have different capacities and must not be seeded equal each
            // tick (issue #191).
            private _coreMap = missionNamespace getVariable [QGVAR(selCoreTemperature), -1];
            if (_coreMap isEqualType 0) then {
                _coreMap = createHashMap;
                missionNamespace setVariable [QGVAR(selCoreTemperature), _coreMap];
            };
            private _tCoreNow = _coreMap getOrDefault [_stateKey, 36.8];
            if !(_tCoreNow isEqualType 0) then { _tCoreNow = 36.8; };

            // Per-selection solar absorptance from the worn garment's own
            // texture (fnc_getSolarAbsorptance), so a black and a light
            // uniform differ in sun.  Thermal paint overwrites the texture
            // during a session, so the saved original is the fallback.
            private _solarAlpha = [_obj, _idx, (_savedTexs param [_idx, ""])] call FUNC(getSolarAbsorptance);

            private _two = [
                _obj, _sel,
                "human", "human",       // core class, skin class
                _tAir, _wind, _solar, _exposure,
                0.9 * 70, _skinMass,    // core/skin mass (loadout-scaled)
                1.8258,                 // DuBois area (m2)
                0.15,                   // convection plate dim (m)
                _tCoreNow, _tCurrent,   // persistent core, current skin
                _qMet,                  // qGen: metabolism (W)
                "vertical", 0.5, _mrt, true, 0.05, true, 5,
                _waterSpeed, _tWater, _rain, (_ox select 10), _cloWorn, _solarAlpha
            ] call FUNC(solveTwoNodeSelection);
            _tNew = _two select 1;      // skin temp - what FLIR sees
            _tCoreNew = _two select 0;
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
            private _lChar = _lCharObj;
            private _qGenCore = _qInternal * _area;
            private _two = [
                _obj, _sel,
                _matClass, _matClass,
                _tAir, _wind, _solar, _exposure,
                50, 20,                          // core/skin mass (kg, lumped panel)
                _area, _lChar,                   // area, convection plate dim (m)
                _tCurrent, _tCurrent,
                _qGenCore,                       // engine heat into the CORE (W)
                "vertical", 0.5, _mrt, false, _lCond, false, 5
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
        if !(finite _tCoreNew) then { _tCoreNew = _tAir; };
        private _selMap = missionNamespace getVariable [QGVAR(selTemperature), -1];
        if (_selMap isEqualType 0) then {
            _selMap = createHashMap;
            missionNamespace setVariable [QGVAR(selTemperature), _selMap];
        };
        _selMap set [_stateKey, _tNew];
        missionNamespace setVariable [QGVAR(selTemperature), _selMap];
        // The core persists separately from the skin: the displayed node is
        // the skin, the defended core is the solver's other state.
        private _coreMap = missionNamespace getVariable [QGVAR(selCoreTemperature), -1];
        if (_coreMap isEqualType 0) then {
            _coreMap = createHashMap;
            missionNamespace setVariable [QGVAR(selCoreTemperature), _coreMap];
        };
        _coreMap set [_stateKey, _tCoreNew];
        missionNamespace setVariable [QGVAR(selCoreTemperature), _coreMap];

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
        // Publish the selection's OWN emissivity for the AGC.  selTemperature
        // keeps its "object|selection" keys; this parallel map lets the AGC
        // window be built from the real materials, not one painted-surface
        // value that normalises bare metal as if it were painted.
        private _epsMap = missionNamespace getVariable [QGVAR(selEmissivity), -1];
        if (_epsMap isEqualType 0) then {
            _epsMap = createHashMap;
            missionNamespace setVariable [QGVAR(selEmissivity), _epsMap];
        };
        _epsMap set [_stateKey, _eps];
        missionNamespace setVariable [QGVAR(selEmissivity), _epsMap];
        private _rad = [_tNew, _eps, _tAir, _fGround, _tCurrent, _tau, _tAir] call FUNC(calculateBandRadiance);
        private _agcMin = missionNamespace getVariable [QGVAR(agcRadMin), -1];
        private _agcMax = missionNamespace getVariable [QGVAR(agcRadMax), -1];
        // Fallback window (first frames / no AGC yet): the radiance of
        // the old -40..150 C span - identical behaviour to the previous
        // fixed window until the AGC warms up.
        if (!(_agcMin isEqualType 0) || !(_agcMax isEqualType 0) || _agcMin >= _agcMax) then {
            _agcMin = [-40, _eps, _tAir, _fGround, _tCurrent, _tau, _tAir] call FUNC(calculateBandRadiance);
            _agcMax = [150, _eps, _tAir, _fGround, _tCurrent, _tau, _tAir] call FUNC(calculateBandRadiance);
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
        // Gated on aee_thermal_thermalDebug, like the sibling diagnostics in
        // fnc_applyThermalVision and fnc_applyBuildingThermal.  This log was
        // raw and ungated inside a 10 Hz path, so it wrote to the RPT from the
        // render thread on every new object the sweep reached.
        private _traceKey = format ["%1_%2", _obj, _sel];
        private _traceN = missionNamespace getVariable [QGVAR(traceCount), -1];
        if (_traceN isEqualType 0) then {
            _traceN = createHashMap;
            missionNamespace setVariable [QGVAR(traceCount), _traceN];
        };
        private _n = _traceN getOrDefault [_traceKey, 0];
        if (_n < 20 && {missionNamespace getVariable [QGVAR(thermalDebug), false]}) then {
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

        // Gated for the same reason as the save block above: in normal vision
        // this selection can be the operator's own uniform, and no teardown
        // runs to put the real texture back.
        private _bandKey = "";
        private _was = "";
        if (_due) then {
            _bandKey = _objKey + "|" + _sel;
            _was = _bands getOrDefault [_bandKey, ""];
        };
        // The paint and its _thermalOn gate share one line on purpose.  That is
        // the shape TestThermalPaintVisionGate.test_heat_texture_paint_is_gated
        // reads, and the gate must stay visible there: in normal vision this
        // selection can be the operator's own uniform, and nothing puts the
        // real texture back.
        if (_thermalOn && {_due && {_forced || _was != _colour}}) then { _obj setObjectTexture [_idx, _colour]; _bands set [_bandKey, _colour]; _uploaded = _uploaded + 1; };
        // The material stays the object's own (or the FPN rvmat when the
        // thermalFPN setting is on - see the save block).  setObjectTexture
        // replaces the Stage1 texture of whatever material is current, so
        // the heat colour renders over Stage1 and (with FPN) the perlinNoise
        // Stage2 multiplies over it.
    } forEach _selNames;

    // Stamped on EVERY due pass, not only on a real upload.  The old condition
    // (_uploaded > 0) meant a STATIC scene never advanced the stamp, so _due
    // stayed true forever and the entire per-selection solve ran on every
    // 10 Hz tick.  A standing-still observer is exactly that case, and it is
    // when the lag is worst.  A due pass happens only once per _interval now,
    // which is what throttles the solve to the repaint cadence (4 Hz default)
    // instead of 10 Hz.  The solve is an elapsed-time relaxation, so the
    // larger step is physics-neutral.
    _gate set [_gateKey, diag_tickTime];
    missionNamespace setVariable [QGVAR(paintGate), _gate];
    missionNamespace setVariable [QGVAR(paintBands), _bands];
    if (AEE_TRACE_ON) then {
        private _objUs = round ((diag_tickTime - _perfT0) * 1000);
        private _gateMsg = format ["paint %1 | sels %2 | due %3 | uploads %4 | solve %5 us",
            _objKey, count _selNames, _due, _uploaded, _objUs];
        AEE_LOG_DEBUG(_gateMsg);
    };
};

0
