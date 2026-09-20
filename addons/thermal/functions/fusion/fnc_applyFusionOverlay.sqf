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
 * Params:
 *   0: _player (OBJECT, default player)
 *
 * Returns: nothing.
 */
params [["_player", player, [objNull]]];
if (isNull _player) exitWith {};

// Reuse the exact band quantisation from the thermal display: the AGC
// window and selection state are per-frame.
private _selMap = missionNamespace getVariable [QGVAR(selTemperature), createHashMap];
private _agcMin = missionNamespace getVariable [QGVAR(agcRadMin), -1];
private _agcMax = missionNamespace getVariable [QGVAR(agcRadMax), -1];

private _objects = _player nearObjects 300;
{
    private _obj = _x;
    // Shared dynamic discovery (issue #204): Man = all texture slots,
    // vehicle = config override > textureSources > all-but-MFD.  The
    // single source of truth so fusion and thermal agree on every part.
    private _selIdxs = [_obj] call FUNC(getThermalSelections);
    private _hs = getArray (configOf _obj >> "hiddenSelections");

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
        private _b = ((_rad - _agcMin) / ((_agcMax - _agcMin) max 1e-6)) max 0 min 1;
        if !(finite _b) then { _b = 0; };
        private _band = round (_b * 15) min 15 max 0;
        private _bandPct = round ((_band / 15) * 100) min 100 max 0;
        _obj setObjectMaterial [_idx, format [QPATHTOF(data\fusion_emissive_%1.rvmat), _bandPct]];
    } forEach _selIdxs;
} forEach _objects;
