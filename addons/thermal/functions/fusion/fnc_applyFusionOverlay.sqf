#include "..\..\script_component.hpp"
/*
 * Fusion overlay (issue #204, Track B ENVG-B).
 *
 * Renders the physics-driven thermal state as an emissive overlay on
 * top of the NVG base view.  Real fusion goggles (L3Harris ENVG-B,
 * AN/PSQ-20) blend an image-intensified I2 tube image with a thermal
 * microbolometer image; the thermal channel is a separate composited
 * source, not the native TI mode.
 *
 * Mechanism (proven by the workshop audit - A3TI EmissiveWhite.rvmat,
 * workshop 2041057379): swap each object's thermal selections to an
 * rvmat whose EMISSIVE carries the heat.  A3TI uses a binary
 * full-white (emmisive 500, AlwaysInShadow, ambient 20) so everything
 * glows white over the NVG.  We grade it by the SAME physics + AGC
 * state as the thermal display: hotter selections glow brighter,
 * cooler selections stay dark.  The 16 pre-baked fusion_emissive_XX
 * rvmats carry emissive = band_grey * 500 (band_100 = full A3TI
 * white), so band_50 glows half as bright.
 *
 * The overlay reads QGVAR(selTemperature) (the same per-selection
 * physics state the thermal display writes) and the AGC window
 * (QGVAR(agcRadMin/Max)), so fusion and thermal agree on what is hot.
 * This function is called from the sensor tick while in NVG mode 1
 * with a fusion-capable headset.
 *
 * EDGE STATE AND THE BRIGHTNESS LADDER COMBINE, THEY DO NOT OVERWRITE.
 * Each selection gets one of the 16 emissive materials as its brightness
 * ladder.  A detected edge is a SEPARATE piece of state written to
 * QGVAR(selThermalEdge), keyed like the selection temperature, and it does
 * NOT touch the material slot.  The two are combined by keeping the ladder
 * on the material and carrying the edge alongside it: if the edge wrote to
 * the material slot, a detected edge would LOSE its correct thermal shading
 * to gain a marker.  The edge decision is LOCAL: the selection's band
 * radiance against the mean band radiance of the object's OTHER selections.
 * Any edge marker built from this state is a device CUE and not sensor
 * output.  No fielded dismounted thermal sight draws an automatic marker,
 * and detection on those devices is a human task, so no automatic cue is
 * drawn here.
 *
 * Params:
 *   0: _player (OBJECT, default player)
 *
 * Returns: nothing.
 */
params [["_player", player, [objNull]], ["_mode", ""]];

// Restore the emissive materials.  This function swaps a material onto every
// thermal selection of every object within 300 m, and the selection set
// includes Man, so without a restore an operator who uses fusion and never
// enters thermal mode leaves fusion_emissive materials on world objects and
// on uniforms after returning to normal vision.  The sensor teardown calls
// this with EXIT.
if (_mode == "EXIT") exitWith {
    private _restore = missionNamespace getVariable [QGVAR(fusionOverlaySaved), []];
    {
        _x params ["_o", "_oldMats"];
        if (!isNull _o) then {
            private _i = 0;
            {
                if (_i < count _oldMats && {(_oldMats select _i) isEqualType ""}) then {
                    _o setObjectMaterial [_i, _oldMats select _i];
                };
                _i = _i + 1;
            } forEach _oldMats;
        };
    } forEach _restore;
    missionNamespace setVariable [QGVAR(fusionOverlaySaved), []];
};

if (isNull _player) exitWith {};

// Reuse the exact band quantisation from the thermal display: the AGC
// window and selection state are per-frame.
private _selMap = missionNamespace getVariable [QGVAR(selTemperature), createHashMap];
private _agcMin = missionNamespace getVariable [QGVAR(agcRadMin), -1];
private _agcMax = missionNamespace getVariable [QGVAR(agcRadMax), -1];
// The edge state is SEPARATE from the brightness ladder.  The 16 emissive
// materials are the brightness ladder and the material slot is theirs; an
// edge must not write to that slot, or the selection loses its thermal
// shading to gain a marker.  The ladder stays on the material and the edge is
// carried alongside it, keyed like the selection temperature.
private _edgeMap = missionNamespace getVariable [QGVAR(selThermalEdge), createHashMap];

private _objects = _player nearObjects 300;
{
    private _obj = _x;
    // Shared dynamic discovery (issue #204): Man = all texture slots,
    // vehicle = config override > textureSources > all-but-MFD.  The
    // single source of truth so fusion and thermal agree on every part.
    private _selIdxs = [_obj] call FUNC(getThermalSelections);
    private _hs = getArray (configOf _obj >> "hiddenSelections");

    // Save the object's own materials ONCE per session, before the first
    // swap.  Saving every tick would capture the already-swapped emissive
    // material, and the EXIT restore would then put the emissive material
    // back instead of the object's own.
    if (_selIdxs isNotEqualTo []) then {
        private _restore = missionNamespace getVariable [QGVAR(fusionOverlaySaved), []];
        if ((_restore findIf { (_x select 0) == _obj }) < 0) then {
            _restore pushBack [_obj, getObjectMaterials _obj];
            missionNamespace setVariable [QGVAR(fusionOverlaySaved), _restore];
        };
    };

    // Pass 1: solve every selection's band radiance once, so pass 2 can use
    // the object's OTHER selections as its local background.
    private _solved = [];
    {
        private _idx = _x;
        private _selName = if (_obj isKindOf "Man") then {
            private _names = selectionNames _obj;
            if (_idx < count _names) then { _names select _idx } else { "" }
        } else {
            if (_idx < count _hs) then { _hs select _idx } else { "" }
        };
        if (_selName == "") then { continue; };
        private _stateKey = format ["%1|%2", _obj, _selName];
        private _tNew = _selMap getOrDefault [_stateKey, -999];
        if (_tNew <= -900) then { continue; };
        private _mat = ([_obj, _selName] call FUNC(getSelectionMaterials)) call FUNC(getMaterialThermal);
        private _eps = _mat select 0;
        private _tAir = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
        if !(_tAir isEqualType 0) then { _tAir = 15; };
        // Ground radiance coefficient: the thermal display passes 0.5 as
        // the default ground-term proxy (fnc_applySelectionThermal
        // param 4).  Keep the same value so fusion and thermal agree.
        private _fGround = 0.5;
        private _rad = [_tNew, _eps, _tAir, _fGround, _tNew] call FUNC(calculateBandRadiance);
        if (!(_agcMin isEqualType 0) || !(_agcMax isEqualType 0) || _agcMin >= _agcMax) then {
            _agcMin = [-40, _eps, _tAir, _fGround, _tNew] call FUNC(calculateBandRadiance);
            _agcMax = [150, _eps, _tAir, _fGround, _tNew] call FUNC(calculateBandRadiance);
        };
        _solved pushBack [_idx, _stateKey, _rad];
    } forEach _selIdxs;

    // Pass 2: local-background edge test, then the brightness ladder.  The
    // background is the mean band radiance of the object's OTHER selections.
    // A single-selection object has no other selection, so its background is
    // 0 and the kernel refuses it: no local background, no edge.
    private _n = count _solved;
    for "_i" from 0 to (_n - 1) do {
        private _entryIdx = (_solved select _i) select 0;
        private _entryKey = (_solved select _i) select 1;
        private _entryRad = (_solved select _i) select 2;
        private _bgSum = 0;
        private _bgCount = 0;
        for "_j" from 0 to (_n - 1) do {
            if (_j != _i) then {
                private _other = _solved select _j;
                _bgSum = _bgSum + (_other select 2);
                _bgCount = _bgCount + 1;
            };
        };
        private _localBg = if (_bgCount > 0) then { _bgSum / _bgCount } else { 0 };
        private _edgeResult = [_entryRad, _localBg] call FUNC(evaluateThermalEdge);
        _edgeMap set [_entryKey, _edgeResult select 0];
        private _b = ((_entryRad - _agcMin) / ((_agcMax - _agcMin) max 1e-6)) max 0 min 1;
        if !(finite _b) then { _b = 0; };
        private _band = round (_b * 15) min 15 max 0;
        private _bandPct = round ((_band / 15) * 100) min 100 max 0;
        _obj setObjectMaterial [_entryIdx, format [QPATHTOF(data\fusion_emissive_%1.rvmat), _bandPct]];
    };
} forEach _objects;

// Publish the edge state for the tick.  It is separate from the brightness
// ladder, so an edge can never overwrite a selection's thermal shading.
missionNamespace setVariable [QGVAR(selThermalEdge), _edgeMap];
