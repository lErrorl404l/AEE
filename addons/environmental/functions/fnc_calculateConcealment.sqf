#include "..\script_component.hpp"

/*
Seasonal vegetation concealment (issue #137).

The chain vegetationState -> concealment -> camo -> detection did not
exist: foliage and crop density were computed (and their comments said
"for concealment") but nothing consumed them.  This function produces
the concealment factor at a position:

    concealment 0..1 = how much the local vegetation/snow hides a
    standing person from an observer.

Basis per surface class (engine surfaceType, the same lowercase table
the biome scan uses):
  forest/jungle/rainforest/orchard    foliage-density driven (leaf-on
                                      July full, leaf-off January ~2-3x
                                      detection)
  crop/vineyard                       crop-density driven (standing
                                      corn ~2 m hides a person)
  grass/grassland/prairie/tundra      low base; tall grass hides
                                      prone only (scaled)
  marsh/swamp                         foliage + base
  snow/glacier/ice                    white background: a NON-white
                                      camo is more visible; penalty
                                      scales with snow depth
  desert/sand/dunes/rock/mountain     near-zero concealment (base 0.05)

The result is published as the camo coefficient (aee_core_camoCoefficient)
for the future concealment consumers (#119 clothing camo, #74 AI
detection).  Factor = base x (1 + concealable vegetation/snow).
*/

params [["_posASL", [], [[]]], ["_stance", "STAND", [""]]];

if (_posASL isEqualTo []) then {
    private _unit = call CBA_fnc_currentUnit;
    _posASL = getPosASL _unit;
};

// ─── Inputs (all pre-existing computed state) ─────────────────────────────
private _foliage = missionNamespace getVariable [QEGVAR(environmental,currentFoliageDensity), 0];
if !(_foliage isEqualType 0) then { _foliage = 0; };
private _crop = missionNamespace getVariable [QEGVAR(core,currentCropDensity), 0];
if !(_crop isEqualType 0) then { _crop = 0; };
private _snow = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];
if !(_snow isEqualType 0) then { _snow = 0; };

private _surface = toLower (surfaceType _posASL);
private _prone = _stance == "PRONE";
private _crouched = _stance == "CROUCH";

// ─── Surface class factor ─────────────────────────────────────────────────
private _factor = 0.05;   // bare/desert floor
private _class = "";

if (_surface find "#gdtforest" >= 0 || _surface find "#gdtconiferous" >= 0 ||
    _surface find "#gdtjungle" >= 0 || _surface find "#gdtrainforest" >= 0 ||
    _surface find "#gdtorchard" >= 0) then {
    // Deciduous leaf cycle: full concealment leaf-on, winter leaf-off.
    _factor = _foliage;
    _class = "forest";
} else {
    if (_surface find "#gdtcrop" >= 0 || _surface find "#gdtvineyard" >= 0) then {
        // Standing corn ~2 m hides a standing person; bare stubble none.
        _factor = _crop;
        _class = "crop";
    } else {
        if (_surface find "#gdtgrass" >= 0 || _surface find "#gdtgrassland" >= 0 ||
            _surface find "#gdtprairie" >= 0 || _surface find "#gdttundra" >= 0) then {
            // Tall grass hides prone/crouched; a standing figure is
            // visible above it.  Prone 0.5, crouched 0.2, standing 0.05.
            _factor = [0.5, 0.2, 0.05] select ([_prone, _crouched] find true);
            _class = "grass";
        } else {
            if (_surface find "#gdtmarsh" >= 0 || _surface find "#gdtswamp" >= 0) then {
                _factor = 0.3 + 0.7 * _foliage;
                _class = "marsh";
            } else {
                if (_surface find "#gdtsnow" >= 0 || _surface find "#gdtglacier" >= 0 ||
                    _surface find "#gdtice" >= 0) then {
                    // White background: a non-white camo stands out.
                    _factor = -0.3 * (0.1 + _snow);   // penalty (negative)
                    _class = "snow";
                } else {
                    // desert/sand/dunes/rock/mountain/bare -> floor
                    _class = "bare";
                };
            };
        };
    };
};

// ─── Snow white-background penalty over vegetation ───────────────────────
// A snow-covered forest still gives structure concealment, but the snow
// reduces it: white on white is harder, khaki on white is easier to spot.
private _snowPenalty = 0;
if (_snow > 0 && _class != "snow") then {
    _snowPenalty = 0.2 * (_snow min 0.5);
};

private _concealment = ((_factor - _snowPenalty) max 0) min 1;

missionNamespace setVariable [QGVAR(concealmentFactor), _concealment];
missionNamespace setVariable [QGVAR(concealmentClass), _class];

if (EGVAR(core,diagnostic)) then {
    diag_log text format [
        "[AEE] Concealment: %1 (%2) foliage=%3 crop=%4 snow=%5",
        [_concealment, 2] call CBA_fnc_formatNumber, _class,
        [_foliage, 2] call CBA_fnc_formatNumber,
        [_crop, 2] call CBA_fnc_formatNumber,
        [_snow, 2] call CBA_fnc_formatNumber
    ];
};

_concealment
