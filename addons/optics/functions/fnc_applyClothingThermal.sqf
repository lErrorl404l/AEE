#include "..\script_component.hpp"
/*
 * Per-clothing thermal for infantry (issue #124 migration).
 *
 * The engine composites each equipped clothing item's TI texture onto the
 * wearer: the ghillie suit hides the wearer because ghillie.p3d references
 * ghillie_ti.paa (a cold TI map).  This is the per-item thermal mechanism.
 *
 * The OLD version swapped clothing materials to ti_cloth_hot/cold.rvmat
 * (the #123 bug class - keyword-matched rvmats that broke on third-party
 * uniform paths like ZuluCustomG3\data\g2\g2_pants.rvmat).  This version
 * drives the per-selection thermal substrate: each unit's selections get
 * their temperature solved from physics (solar absorptance read from the
 * worn garment's own colour, McAdams convection, Stefan-Boltzmann
 * radiation to MRT, real body mass) and painted with the FLIR white-hot
 * procedural colour.
 *
 * The substrate reads the selection's OWN texture for solar absorptance
 * (a unit's textures ARE its worn clothing: uniform/vest/helmet/goggles,
 * each with its own colour and therefore its own solar loading), so the
 * helmet reads different from the uniform - the real per-item look,
 * physics-driven, no keyword matching.
 *
 * Multiplayer: setObjectTexture is LOCAL, correct here.  Each client
 * renders its own thermal pass and computes identical physics, so each
 * client applies the same colour locally and every player sees the same
 * thermal appearance.  No network traffic.
 *
 * Cost: one setObjectTexture per thermal selection per throttle tick
 * (0.05 s), NOT per frame.  All units are scanned because there is no
 * reason for a range limit.
 *
 * Restored on EXIT (mode "EXIT") to the saved originals.
 */
params ["_mode"];

if (!hasInterface) exitWith { 0 };

// ─── EXIT: restore every saved texture ───────────────────────────────────
if (_mode == "EXIT") then {
    ["", "", "EXIT"] call EFUNC(thermal,applySelectionThermal);
    0
};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith { 0 };

// ─── Physics inputs ────────────────────────────────────────────────────────
// Thermal state: insulation + ambient drive the solve's convection term
// through the ambient temperature.  The substrate reads the real air
// temperature, wind, and solar flux from the core environment state.
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };

// ─── Apply to ALL units (no radius: one-shot texture is cheap) ────────────
private _applied = 0;
{
    if (isNull _x || !alive _x) then { continue; };
    private _obj = _x;

    // Per-class thermal selections, cached (A3TI fn_getThermalSelections).
    private _cacheKey = format [QGVAR(tiSelections_%1), typeOf _obj];
    private _selections = missionNamespace getVariable [_cacheKey, []];

    if (count _selections == 0) then {
        // Men: all texture selections are thermal-eligible (A3TI pattern).
        _selections = [];
        {
            _selections pushBack _forEachIndex;
        } forEach (getObjectTextures _obj);
        missionNamespace setVariable [_cacheKey, _selections];
    };

    if (count _selections == 0) then { continue; };

    // Selection names for per-selection classification (for fGround).
    private _selNames = getArray (configOf _obj >> "hiddenSelections");
    if (_selNames isEqualTo []) then { _selNames = selectionNames _obj; };

    // ─── Per-selection substrate solve + FLIR paint ────────────────────
    // Each selection: the substrate reads the material via the #96
    // detector chain (hiddenSelectionsMaterials -> rvmat surfaceInfo ->
    // bisurf class, selection-name conventions, then object fallback),
    // reads the selection's own texture for solar absorptance (NASA
    // TP-2005-212792), and solves the lumped-capacity energy balance
    // with the unit's real mass.  q_internal = 0 (no engine heat on a
    // person); fGround 0.5 (standing soldier).
    {
        private _selIdx = _x;
        private _fGround = 0.5;
        if (_selIdx < count _selNames) then {
            private _sn = toLower (_selNames select _selIdx);
            // Headgear/goggles/glasses face mostly sky; feet/legs see
            // ground; the body is split.  Refined by the material solve.
            if (_sn find "head" >= 0 || _sn find "helmet" >= 0 || _sn find "glass" >= 0
                || _sn find "goggle" >= 0) then {
                _fGround = 0.2;
            };
            if (_sn find "foot" >= 0 || _sn find "leg" >= 0 || _sn find "boot" >= 0) then {
                _fGround = 0.7;
            };
        };
        [_obj, _selIdx, "", 0, _fGround] call EFUNC(thermal,applySelectionThermal);
        _applied = _applied + 1;
    } forEach _selections;
} forEach (allUnits);

_applied
