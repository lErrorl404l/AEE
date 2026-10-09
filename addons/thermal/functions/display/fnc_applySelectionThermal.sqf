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
  - the display is continuous: the band radiance is normalised by the
    scene AGC or the manual window, then interpolated through control
    points (fnc_thermalPalette).  The control points are the engine's
    own decoded TI colours, so a painted object matches an unpainted
    one.  Material never selects a hue; emissivity is already in the
    radiance.

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
        _x params ["_o", "_oldTexs", "_oldMats"];
        if (!isNull _o) then {
            // Restore by the SAVED array's own index.  getObjectTextures and
            // getObjectMaterials are indexed by the hiddenSelections texture
            // slot, the same index the paint writes.  The old restore walked
            // the default-LOD selectionNames list and used ITS position as the
            // texture index; that index space differs in order and length from
            // the saved arrays, so it restored the wrong slots.
            private _n = (count _oldTexs) max (count _oldMats);
            for "_i" from 0 to (_n - 1) do {
                if ((_i < count _oldTexs) && {(_oldTexs select _i) isEqualType ""}) then {
                    _o setObjectTexture [_i, _oldTexs select _i];
                };
                if ((_i < count _oldMats) && {(_oldMats select _i) isEqualType ""}) then {
                    _o setObjectMaterial [_i, _oldMats select _i];
                };
            };
        };
    } forEach _saved;
    missionNamespace setVariable [QGVAR(selThermalSaved), []];
    // The repaint gate is per object and per selection, so a stale entry would
    // suppress the first repaint after a re-entry and leave the restored day
    // texture on screen.
    missionNamespace setVariable [QGVAR(paintGate), createHashMap];
    missionNamespace setVariable [QGVAR(paintBands), createHashMap];
    // The visibility hysteresis cache is display state, like the paint gate:
    // clear it so a re-entry recomputes from the current scene.
    missionNamespace setVariable [QGVAR(selVis), createHashMap];
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

    // The module trace switch, resolved ONCE for the pass.  AEE_TRACE_ON
    // expands to three namespace lookups, and this function walks the
    // object's whole selection set, so the flag is read here and then passed
    // to the per-selection band-radiance calls.
    private _traceOn = AEE_TRACE_ON;

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
    if (!isNull _viewer && {[_viewer] call FUNC(isThermalHostActive)}) then { _thermalOn = true };

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

    // ─── A number plate keeps its own texture and material ─────────────────
    // A plate is an identification marking, not a thermal-radiating surface.
    // The flat heat paint replaces the plate's texture with one solid colour
    // and the FPN rvmat (Stage1 white, no digit glyphs) replaces its material,
    // so the engine-rendered plate text reads BLACK against the paint - the
    // operator's "numberplates still show black text in thermals".  Drop every
    // number_* selection from the paint set and from the material swap below;
    // the model's own plate texture then renders its digits legibly.  The
    // engine names the plate selections number_01/02/03 (confirmed at runtime:
    // RPT sel=number_01/02/03 on B_Plane_Fighter_01_F), and this is the same
    // engine-provided declaration the discovery walk already reads.
    _selNames = _selNames select { !(["number", _x, false] call BIS_fnc_inString) };

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
        // Save what the paint writes: the FULL texture and material arrays.
        // Both are indexed by the hiddenSelections texture slot, which is the
        // index the paint resolves, so EXIT restores them by their own index.
        _saved pushBack [_obj, _oldTexs, _oldMats];
        missionNamespace setVariable [QGVAR(selThermalSaved), _saved];
        // FPN material swap (client-local, once per object per pass):
        // the perlinNoise Stage2 multiplies over the painted heat colour.
        // Skipped when the object has no material slots (ground/terrain
        // cannot take a material swap - the proxy-plane overlay is the
        // terrain path).  Only slots with a string material are swapped
        // (matches the EXIT restore guard below).
        if (_fpnEnabled && _oldMats isNotEqualTo []) then {
            private _fpnMat = "\z\aee\addons\thermal\data\ti_fpn.rvmat";
            // The FPN rvmat is Stage1 white with no digit glyphs, so swapping
            // it onto a number plate erases the plate text.  Skip the plate
            // material slots; they keep the model's own material.
            private _matSels = selectionNames _obj;
            {
                private _slotSel = _matSels param [_forEachIndex, ""];
                if ((_x isEqualType "") && {!(["number", _slotSel, false] call BIS_fnc_inString)}) then {
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
    // The detector band (T16): default lwir, replaced by the mounted device's
    // band below.  A device that cannot be read keeps the LWIR default, so the
    // no-device path reproduces the old LWIR result bit for bit.
    private _band = "lwir";
    // Sun elevation in degrees, published by the environmental solar model.
    // The reflected-solar term is zero for LWIR and at night.
    private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), -90];
    if !(_sunElev isEqualType 0) then { _sunElev = -90; };

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
            private _uniformClo = [_obj] call EFUNC(clothing,getUniformProperties);
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
    // The largest bounding-box extent is the target's critical dimension for
    // the Johnson angular-size test.  Read from the box already in hand, so no
    // extra engine call.
    private _sizeObj = abs (((_bbRealObj select 1) select 0) - ((_bbRealObj select 0) select 0));
    _sizeObj = _sizeObj max (abs (((_bbRealObj select 1) select 1) - ((_bbRealObj select 0) select 1)));
    _sizeObj = _sizeObj max (abs (((_bbRealObj select 1) select 2) - ((_bbRealObj select 0) select 2)));
    if (_sizeObj <= 0) then { _sizeObj = (sizeOf _obj) max 0.1; };
    private _vSpeedObj = abs speed _obj;
    private _oxObj = [];

    private _uploaded = 0;

    // Per-selection solar exposure for the whole object.  One shared resolver
    // call, cached per class, so the model geometry is read once and not on
    // this hot path.
    private _exposureArr = [_obj, _selNames] call FUNC(getSelectionSunExposure);

    // ─── Sensor-resolution layer (issue #215): the three kernels' caller ──
    // Order is the one the headers intend: derive the threshold from the
    // mounted device, decide the local-contrast edge against the object's
    // OTHER selections, then apply the Johnson spatial test.  The result is a
    // resolved fraction the paint blends the band position by.
    //
    // The device is the viewer's, resolved once per object pass and cached by
    // optic class.  The sensor belongs to the optic, so the cache key is the
    // optic and not the object.
    private _netdC = 0.05;
    private _resX = 640;
    // The day-optic magnification the spatial kernel's 24/mag FOV fallback
    // consumes (fnc_getOpticProperties, issue #215).  Unity when the slot
    // holds no recognised optic, which is the kernel's own declared fallback.
    private _mag = 1;
    if (_thermalOn && {!isNull _viewer}) then {
        private _wp = vehicle _viewer;
        private _optic = "";
        if (!isNull _wp) then { _optic = primaryWeaponItems _wp param [2, ""]; };
        if (_optic == "") then { _optic = hmd _viewer; };
        // The researched sight physics.  The optic slot the device block reads
        // is the same slot the day-optic classifier keys on, so the resolved
        // magnification is the mounted sight's own.  Cached by optic class,
        // like the thermal device above, so the corpus scan runs once per
        // optic rather than once per object per tick.
        private _opCache = missionNamespace getVariable [QGVAR(opticPropsCache), -1];
        if (_opCache isEqualType 0) then {
            _opCache = createHashMap;
            missionNamespace setVariable [QGVAR(opticPropsCache), _opCache];
        };
        private _op = _opCache getOrDefault [_optic, []];
        if ((count _op) < 6) then {
            _op = [_viewer, _wp] call EFUNC(optics,getOpticProperties);
            if ((_op isEqualType []) && {(count _op) >= 6}) then {
                _opCache set [_optic, _op];
            };
        };
        if ((_op isEqualType []) && {(count _op) >= 6}) then {
            private _opMag = _op select 0;
            if ((_opMag isEqualType 0) && (_opMag >= 1) && {finite _opMag}) then { _mag = _opMag; };
        };
        private _devCache = missionNamespace getVariable [QGVAR(devicePropsCache), -1];
        if (_devCache isEqualType 0) then {
            _devCache = createHashMap;
            missionNamespace setVariable [QGVAR(devicePropsCache), _devCache];
        };
        private _device = _devCache getOrDefault [_optic, []];
        if ((count _device) < 6) then {
            _device = [_viewer, _wp] call EFUNC(thermal,getThermalDeviceProperties);
            if ((_device isEqualType []) && {(count _device) >= 6}) then {
                _devCache set [_optic, _device];
            };
        };
        if ((_device isEqualType []) && {(count _device) >= 6}) then {
            private _devNetd = _device select 0;
            private _devRes = _device select 1;
            if ((_devNetd isEqualType 0) && (_devNetd > 0) && {finite _devNetd}) then { _netdC = _devNetd; };
            if ((_devRes isEqualType 0) && (_devRes > 0) && {finite _devRes}) then { _resX = _devRes; };
            // Index 6 is the detector band (T1).  A device row without it
            // leaves the LWIR default in place.
            private _devBand = _device param [6, "lwir"];
            if (_devBand isEqualType "") then { _band = _devBand; };
        };
    };

    // The band edges and the band-resolved path transmission, resolved once
    // per object.  The band defaults to lwir, so a device that cannot be read
    // reproduces the old LWIR result bit for bit.
    private _bandEdges = [_band] call FUNC(resolveThermalBand);
    private _lambda1M = _bandEdges select 0;
    private _lambda2M = _bandEdges select 1;
    private _tau = [_rangeM, _humidity, _tAir, _fog, rain, _airDensity, _band] call FUNC(calculateAtmosphericTransmission);
    if (_tau < 0) then { _tau = 1; };   // unusable input: transmissive fallback

    // The threshold.  A device the matcher cannot identify is the documented
    // uncooled 0.05 C microbolometer fallback, NOT a disabled model.  If the
    // background temperature is unusable as well, the edge kernel's declared
    // reference value is used (0.004349, the network default at 15 C).
    private _tBgC = _tAir;
    if !((_tBgC isEqualType 0) && {finite _tBgC}) then { _tBgC = 15; };
    private _threshold = [_netdC, 5, _tBgC] call FUNC(calculateSensorThreshold);
    if !((_threshold isEqualType 0) && (_threshold > 0) && {finite _threshold}) then {
        _threshold = 0.004349;
    };

    // The object's local background: the mean band radiance of its OTHER
    // selections, from the previous pass.  The paint is driven one selection
    // per call, so the object's selection NAMES are accumulated in a map and
    // the mean is recomputed at most once per repaint interval per object.
    // That bounds the scan to O(n) per object per interval, where n is the
    // painted selection count (bounded by the per-class selection cache).
    // Every other call in the interval is O(1), and the per-selection
    // leave-one-out is O(1) from the cached sum.
    private _radMap = missionNamespace getVariable [QGVAR(selBandRad), -1];
    if (_radMap isEqualType 0) then {
        _radMap = createHashMap;
        missionNamespace setVariable [QGVAR(selBandRad), _radMap];
    };
    private _nameMap = missionNamespace getVariable [QGVAR(selBandRadNames), -1];
    if (_nameMap isEqualType 0) then {
        _nameMap = createHashMap;
        missionNamespace setVariable [QGVAR(selBandRadNames), _nameMap];
    };
    private _objNames = _nameMap getOrDefault [_objKey, []];
    {
        _objNames pushBackUnique _x;
    } forEach _selNames;
    _nameMap set [_objKey, _objNames];

    private _bgSum = 0;
    private _bgCount = 0;
    private _bgCache = missionNamespace getVariable [QGVAR(selBandRadBg), -1];
    if (_bgCache isEqualType 0) then {
        _bgCache = createHashMap;
        missionNamespace setVariable [QGVAR(selBandRadBg), _bgCache];
    };
    // ─── Background refresh period (the added per-object scan) ─────────────
    // The scan averages the object's OTHER selections.  Those radiances move
    // on the surface time constants (600 s and longer), so recomputing the
    // mean at the paint cadence was the repeated cost the sensor layer added.
    // Hold it for a full second (four paint intervals at the default 4 Hz);
    // the size check recomputes early when a newly discovered selection joins
    // the set.  That bounds the scan to O(n) once per second per object.
    private _bgInterval = _interval * 4;
    private _bgEntry = _bgCache getOrDefault [_objKey, []];
    private _bgFresh = false;
    if ((_bgEntry isEqualType []) && {(count _bgEntry) == 4}) then {
        private _bgAge = diag_tickTime - (_bgEntry select 2);
        if ((_bgAge < _bgInterval) && {(_bgEntry select 3) == (count _objNames)}) then { _bgFresh = true; };
    };
    if (_bgFresh) then {
        _bgSum = _bgEntry select 0;
        _bgCount = _bgEntry select 1;
    } else {
        {
            private _r = _radMap getOrDefault [format ["%1|%2", str _obj, _x], -1];
            if ((_r isEqualType 0) && (_r > 0) && {finite _r}) then {
                _bgSum = _bgSum + _r;
                _bgCount = _bgCount + 1;
            };
        } forEach _objNames;
        _bgCache set [_objKey, [_bgSum, _bgCount, diag_tickTime, count _objNames]];
    };

    {
        private _sel = _x;
        private _idx = [_obj, _sel] call FUNC(resolveSelectionPaintIndex);
        if (_idx < 0) then { continue; };

        // Solar exposure from the selection's surface orientation
        // (fnc_getSelectionSunExposure): a part facing the sun gets more than
        // a part in shade, and a roof gets more than a side.  The wheel and
        // undercarriage floor is applied inside that resolver.
        private _exposure = _exposureArr param [_forEachIndex, 1];

        // Current per-selection temperature from the object solver state.
        private _stateKey = format ["%1|%2", str _obj, _sel];
        // Eager-default allocation removed; the writer path already uses the
        // lazy -1 form.
        private _tempMap = missionNamespace getVariable [QGVAR(selTemperature), -1];
        if (_tempMap isEqualType 0) then { _tempMap = createHashMap; };
        // First sight: the state map holds no entry for this selection.  The
        // two-node solve below must then start at its OWN equilibrium, not
        // at the _tAir seed: an object that has been sitting in the scene
        // is already at steady state, and starting it cold makes the band
        // march for the first ~15 s (the operator's per-pass flicker).  A
        // huge step lands the exact exponential transient on the
        // equilibrium (exp(-dt/tau) -> 0).  The physics is untouched: every
        // later pass uses the real 5 s step and the node still heats and
        // cools for real when the conditions change.
        private _storedTemp = _tempMap get _stateKey;
        private _firstSight = isNil "_storedTemp";
        private _tCurrent = _tempMap getOrDefault [_stateKey, _tAir];
        private _solveDt = [5, 1000000] select _firstSight;

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
            // through aee_altitude_fnc_calculateOxygenDelivery.  CO carries
            // the acute loss, [Hb] relaxes over hours.  The metabolic
            // fraction scales oxidative heat, the perfusion index scales
            // skin blood flow.
            // Solve once per object, not once per selection.  This is
            // physics-neutral: calculateOxygenDelivery advances [Hb] on ELAPSED
            // TIME and stamps the new tick time back into its state entry, so
            // the second and later calls in a tick saw _elapsed == 0 and
            // returned without touching [Hb] anyway.
            if (count _oxObj == 0) then {
                _oxObj = [_obj, _qMet, 1.8258] call EFUNC(altitude,calculateOxygenDelivery);
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
                "vertical", 0.5, _mrt, true, 0.05, true, _solveDt,
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
                "vertical", 0.5, _mrt, false, _lCond, false, _solveDt
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
            private _logMsg = format [
                "NaN tNew: obj=%1 sel=%2 tAir=%3 tCurrent=%4 qInternal=%5 mode=%6",
                _obj, _sel, _tAir, _tCurrent, _qInternal, _mode
            ];
            AEE_LOG_ERROR(_logMsg);
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
        private _selMatClass = [_obj, _sel] call FUNC(getSelectionMaterials);
        private _mat = _selMatClass call FUNC(getMaterialThermal);
        private _eps = _mat select 0;
        // A rain-wetted surface emits toward the liquid-water value.  The
        // selection is an exposed exterior surface; the wet blend never
        // exceeds 1 (fnc_getEffectiveEmissivity clamps).
        private _surfaceWetness = missionNamespace getVariable [QEGVAR(core,surfaceWetness), 0];
        if !(_surfaceWetness isEqualType 0) then { _surfaceWetness = 0; };
        _eps = [_eps, _surfaceWetness] call FUNC(getEffectiveEmissivity);
        // Reflected-solar band radiance (T4): zero for LWIR and at night, so
        // every LWIR caller stays bit-identical.
        private _wSolar = [_band, _eps, _sunElev] call FUNC(calculateReflectedSolarBand);
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
        private _rad = [_tNew, _eps, _tAir, _fGround, _tCurrent, _tau, _tAir, _traceOn, _lambda1M, _lambda2M, _humidity, _band, _wSolar] call FUNC(calculateBandRadiance);
        private _agcMin = missionNamespace getVariable [QGVAR(agcRadMin), -1];
        private _agcMax = missionNamespace getVariable [QGVAR(agcRadMax), -1];
        // Manual window and the no-AGC fallback.  The manual span is a
        // setting: the device library carries NETD, resolution and refresh
        // rate, but publishes no span.  The fallback uses this same window,
        // so a cold start never maps through a hard-coded span that no
        // device exposes.
        private _manMinC = missionNamespace getVariable [QGVAR(thermalManualMinC), -40];
        private _manMaxC = missionNamespace getVariable [QGVAR(thermalManualMaxC), 120];
        if !(_manMinC isEqualType 0) then { _manMinC = -40; };
        if !(_manMaxC isEqualType 0) then { _manMaxC = 120; };
        if (_manMaxC <= _manMinC) then { _manMaxC = _manMinC + 1; };
        private _displayMode = missionNamespace getVariable [QGVAR(thermalDisplayMode), 0];
        if !(_displayMode isEqualType 0) then { _displayMode = 0; };
        private _agcValid = false;
        if ((_agcMin isEqualType 0) && (_agcMax isEqualType 0) && (_agcMin < _agcMax)) then {
            _agcValid = true;
        };
        if ((_displayMode == 1) || !_agcValid) then {
            _agcMin = [_manMinC, _eps, _tAir, _fGround, _tCurrent, _tau, _tAir, _traceOn, _lambda1M, _lambda2M, _humidity, _band, _wSolar] call FUNC(calculateBandRadiance);
            _agcMax = [_manMaxC, _eps, _tAir, _fGround, _tCurrent, _tau, _tAir, _traceOn, _lambda1M, _lambda2M, _humidity, _band, _wSolar] call FUNC(calculateBandRadiance);
        };
        // Local display mode (2): replace the scene/manual window with this
        // object's own selection window from fnc_updateThermalAGC.  It widens
        // one object's internal contrast but breaks absolute ordering between
        // objects, so it is opt-in and never the default.  The window already
        // carries the 8x max-gain floor, so a flat object is not given
        // invented contrast.  An absent window (cold start, or no solved
        // selections yet) keeps the window resolved above.
        if (_displayMode == 2) then {
            private _objWindows = missionNamespace getVariable [QGVAR(objAgcRad), -1];
            if !(_objWindows isEqualType 0) then {
                private _oWin = _objWindows getOrDefault [_objKey, []];
                if ((_oWin isEqualType []) && {(count _oWin) == 2}) then {
                    private _oMin = _oWin select 0;
                    private _oMax = _oWin select 1;
                    if ((_oMin isEqualType 0) && (_oMax isEqualType 0) && (_oMin < _oMax)) then {
                        _agcMin = _oMin;
                        _agcMax = _oMax;
                    };
                };
            };
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
            private _logMsg = format [
                "obj=%1 sel=%2 mat=%3 eps=%4 tNew=%5 rad=%6 agc=%7..%8 b=%9 qInt=%10 finite_b=%11",
                _obj, _sel, _mat, _eps, _tNew, _rad, _agcMin, _agcMax, _b, _qInternal, finite _b
            ];
            AEE_LOG_TRACE(_logMsg);
        };
        // NaN guard: SQF NaN comparisons are false (NaN != NaN is also
        // false in SQF), so max/min AND a self-compare CANNOT clamp a
        // NaN - it would emit "#(rgb,8,8,3)color(scalar NaN,..)" and
        // the engine rejects the texture.  The `finite` command is the
        // only reliable check.  A NaN here means a state read returned
        // nil upstream (the #189 class); fall back to ambient.
        if !(finite _b) then {
            private _logMsg = format [
                "NaN brightness: obj=%1 sel=%2 tNew=%3 eps=%4 rad=%5",
                _obj, _sel, _tNew, _eps, _rad
            ];
            AEE_LOG_ERROR(_logMsg);
            _b = 0;
        };

        // ─── Sensor resolution: is this selection a resolvable target? ────
        // Threshold from the device, edge against the local background of the
        // object's OTHER selections, then the Johnson spatial test.  The three
        // kernels are pure; this block is their caller.
        //
        // The background is the object mean WITHOUT this selection (its own
        // radiance from the previous pass), so one selection does not bias the
        // background it is compared against.  An object with no sibling
        // selection has no local background, so the test is skipped and the
        // selection keeps full contrast.
        private _ownPrev = _radMap getOrDefault [_stateKey, -1];
        private _bgRad = -1;
        if (_bgCount >= 2) then {
            if ((_ownPrev isEqualType 0) && (_ownPrev > 0)) then {
                _bgRad = (_bgSum - _ownPrev) / (_bgCount - 1);
            } else {
                _bgRad = _bgSum / _bgCount;
            };
        };
        // Keep the radiance fresh every pass so thermal vision opens on a
        // measured background.  One hashmap write per selection.
        _radMap set [_stateKey, _rad];

        private _vis = 1;
        // The sensor noise floor.  The range is the REAL sensor-to-selection
        // distance; a display-only tick or a dedicated server has no target,
        // so the declared default 1000 m is used.  That default is UNSOURCED:
        // the device corpus holds no detection range.  The noise raises the
        // contrast a selection must show to resolve (fnc_calculateThermalNoise).
        private _noiseRange = [1000, _rangeM] select (_rangeM > 0.001);
        private _noiseFloor = [_netdC, _noiseRange, _resX, _humidity] call FUNC(calculateThermalNoise);
        if !((_noiseFloor isEqualType 0) && {finite _noiseFloor}) then { _noiseFloor = 0; };
        if (_thermalOn && (_bgRad > 0) && (_rangeM > 0.001)) then {
            private _edge = [_rad, _bgRad, _threshold, _noiseFloor] call FUNC(evaluateThermalEdge);
            if ((_edge isEqualType []) && {(count _edge) >= 2}) then {
                private _contrast = _edge select 1;
                // Angular size: the object's largest bounding-box extent at
                // this range.  The repository holds no per-selection extent
                // and no per-lens thermal FOV, so the kernel's declared
                // 24/mag day-optic fallback is used at unity magnification.
                private _angle = _sizeObj / _rangeM;
                private _spatial = [_angle, _resX, _mag, 0, _netdC, _contrast, _tBgC] call FUNC(resolveThermalTarget);
                if ((_spatial isEqualType []) && {(count _spatial) >= 3}) then {
                    _vis = [_contrast, _threshold, _spatial select 0, _spatial select 2] call FUNC(resolveThermalVisibility);
                };
            };
        };
        // A refusal from any kernel must not blank the scene: keep full
        // contrast when the resolved fraction is unusable.
        if !((_vis isEqualType 0) && (_vis >= 0) && {finite _vis}) then { _vis = 1; };

        // ─── Visibility hysteresis (the in/out flicker) ────────────────────
        // The three kernels run every due pass and their verdict is continuous
        // in the inputs, but two joins are STEPS: the sub-pixel SNR detection
        // at 2.8 and the one-line-pair Johnson boundary in
        // fnc_resolveThermalTarget.  At a fixed range those sit on a knife
        // edge, so range and scene noise flip _vis every pass and the
        // selection repaints between full contrast and its local background -
        // the operator's "flickering in and out".  Keep the previous fraction
        // until the new one differs by more than the dead-band: the step joins
        // become a Schmitt trigger, and a steady scene holds the cached
        // fraction and never repaints.  A full-contrast (1.0) verdict always
        // snaps to 1 so a resolved target is never held below it.
        private _visMap = missionNamespace getVariable [QGVAR(selVis), -1];
        if (_visMap isEqualType 0) then {
            _visMap = createHashMap;
            missionNamespace setVariable [QGVAR(selVis), _visMap];
        };
        private _visPrev = _visMap getOrDefault [_stateKey, -1];
        private _visBand = 0.1;
        if ((_vis < 1) && {(_visPrev isEqualType 0) && (_visPrev >= 0) && {abs (_vis - _visPrev) <= _visBand}}) then {
            _vis = _visPrev;
        };
        _visMap set [_stateKey, _vis];
        missionNamespace setVariable [QGVAR(selVis), _visMap];

        // Pull a target the sensor cannot resolve toward the local background
        // colour, in the same band-position domain the palette consumes.  The
        // blend is the area-weighted mean of target and background: a pixel the
        // target only partly fills shows that fraction of the target.  A
        // selection that passes keeps its full-contrast colour.
        if (_vis < 1) then {
            private _bBg = ((_bgRad - _agcMin) / ((_agcMax - _agcMin) max 1e-6)) max 0 min 1;
            _b = ((_bBg + ((_b - _bBg) * _vis)) max 0 min 1);
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
        // Quantise the POSITION, not a hue.  The engine re-uploads the
        // procedural texture whenever the value changes, so a 255-step
        // ladder bounds the uploads.  255 is the 8-bit display depth and
        // keeps the ramp continuous; 32 was a visible band.
        private _levels = 255;
        private _qb = (round ((_b max 0 min 1) * (_levels - 1))) / (_levels - 1);
        // ─── Continuous display palette (issue #204 rework) ──────────────
        // The display carries ONE scalar per pixel.  The selection's
        // material enters the image only through emissivity, which the
        // band radiance above already holds, so the colour is a pure
        // function of the normalised band position.  The old three-entry
        // material hue table is gone: it painted glass permanently black
        // and made a whole vehicle read as one flat colour.
        private _palette = missionNamespace getVariable [QGVAR(thermalPalette), 0];
        if (!(_palette isEqualType 0)) then { _palette = 0; };
        private _polarity = missionNamespace getVariable [QGVAR(thermalPolarity), 0];
        if (!(_polarity isEqualType 0)) then { _polarity = 0; };
        // Polarity is baked into the palette here AND applied by the
        // ColorInversion ppEffect in fnc_applyThermalVision.  The native
        // TI renderer (vision mode 2) does not apply ppEffects, so the
        // baked ramp is the polarity the operator sees there.
        private _heatCol = [_qb, _palette, _polarity] call FUNC(thermalPalette);
        private _colour = format [
            "#(rgb,8,8,3)color(%1,%2,%3,1)",
            _heatCol select 0,
            _heatCol select 1,
            _heatCol select 2
        ];

        // ─── Change gate on the PAINTED level (the residual AGC flicker) ───
        // The AGC window is a low-passed scene statistic, so the raw band
        // position still moves by a fraction of a display step every pass.
        // The gate used to compare the RAW `_b` against the last upload with a
        // half-step dead-band, but the thing painted is the quantised level
        // `_qb`.  Two raw positions inside ONE level can sit up to a full step
        // apart, which is MORE than the half-step dead-band, so the raw gate
        // re-uploaded the SAME colour while the painted level never changed.
        // That is the residual flicker.  The gate now compares the integer
        // level that feeds the colour string: a repaint needs a change of at
        // least one level, and a sub-level wobble produces NO repaint.  The
        // palette and polarity are stored with the level, so a display-mode
        // change repaints even though the level is unchanged.
        private _qLevel = round ((_b max 0 min 1) * (_levels - 1));
        private _bandKey = "";
        private _last = -1;
        if (_due) then {
            _bandKey = _objKey + "|" + _sel;
            _last = _bands getOrDefault [_bandKey, -1];
        };
        private _lastLevel = -1;
        private _lastPal = -1;
        private _lastPol = -1;
        if (_last isEqualType [] && {(count _last) == 3}) then {
            _lastLevel = _last select 0;
            _lastPal = _last select 1;
            _lastPol = _last select 2;
        };
        private _moved = (_qLevel != _lastLevel);
        private _restyled = (_palette != _lastPal) || (_polarity != _lastPol);
        // The paint and its _thermalOn gate share one line on purpose.  That is
        // the shape TestThermalPaintVisionGate.test_heat_texture_paint_is_gated
        // reads, and the gate must stay visible there: in normal vision this
        // selection can be the operator's own uniform, and nothing puts the
        // real texture back.
        if (_thermalOn && {_due && {_forced || _moved || _restyled}}) then { _obj setObjectTexture [_idx, _colour]; _bands set [_bandKey, [_qLevel, _palette, _polarity]]; _uploaded = _uploaded + 1; };
        // The material stays the object's own (or the ti_fpn rvmat when the
        // thermalFPN setting is on - see the save block).  setObjectTexture
        // replaces the Stage1 texture of whatever material is current, so the
        // heat colour renders over Stage1.  ti_fpn.rvmat is Stage1 only: it
        // carries no Stage2 and no perlinNoise, so nothing multiplies over
        // the paint.
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
    if (_traceOn) then {
        private _objUs = round ((diag_tickTime - _perfT0) * 1000);
        private _gateMsg = format ["paint %1 | sels %2 | due %3 | uploads %4 | solve %5 ms",
            _objKey, count _selNames, _due, _uploaded, _objUs];
        AEE_LOG_DEBUG(_gateMsg);
    };
};

0
