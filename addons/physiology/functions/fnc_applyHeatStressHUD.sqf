#include "..\script_component.hpp"

/*
Heat stress HUD warning via structured title text.

Reads EGVAR(core,currentWBGT) (°C) and QGVAR(dehydrationRisk) (0–1) produced
by fn_calculateDehydrationRisk.  Gates on GVAR(environmentalEnabled).

ISO 7243 WBGT categories:
  <18 °C safe, 18–23 caution, 23–28 extreme caution, 28–32 danger,
  >32 very dangerous (heat stroke risk).

Shows a persistent severity-coloured warning when the WBGT category is 1 or
higher, or when dehydration risk > 0.3.  The warning names the category,
the WBGT value, and the dehydration risk percentage.  Clears when the
category drops to 0 AND risk falls back to 0.3 or below, using a flag
(QGVAR(hudWarningActive)) to avoid spamming titleText every tick.
*/

if (!EGVAR(core,environmentalEnabled)) exitWith {};

private _risk   = missionNamespace getVariable [QGVAR(dehydrationRisk), 0];
private _WBGT   = missionNamespace getVariable [QEGVAR(core,currentWBGT), 15];
private _active = missionNamespace getVariable [QGVAR(hudWarningActive), false];

private _cat = switch (true) do {
    case (_WBGT >= 32): { 4 };   // very dangerous
    case (_WBGT >= 28): { 3 };   // danger
    case (_WBGT >= 23): { 2 };   // extreme caution
    case (_WBGT >= 18): { 1 };   // caution
    default             { 0 };   // safe
};

private _show = (_cat >= 1 || _risk > 0.3);

if (_show) then {
    if (!_active) then {
        private _name = switch (_cat) do {
            case 1: { "CAUTION" };
            case 2: { "EXTREME CAUTION" };
            case 3: { "DANGER" };
            case 4: { "VERY DANGEROUS" };
            default { "HEAT STRESS" };
        };
        private _colour = switch (_cat) do {
            case 1: { "#ffaa00" };
            case 2: { "#ff6600" };
            case 3: { "#ff0000" };
            case 4: { "#cc0000" };
            default { "#ff6600" };   // dehydration-only warning
        };
        private _text = format [
            "<t color='%1' size='1.2'>%2</t><br/><t color='#cccccc' size='0.9'>WBGT: %3°C</t>",
            _colour, _name, round _WBGT
        ];
        if (_risk > 0.3) then {
            _text = _text + format [
                "<br/><t color='#cccccc' size='0.9'>Dehydration risk: %1%2</t>",
                floor (_risk * 100), "%"
            ];
        };
        titleText [_text, "PLAIN DOWN", 0.5, true, true];
        missionNamespace setVariable [QGVAR(hudWarningActive), true];
    };
} else {
    if (_active) then {
        titleText ["", "PLAIN DOWN"];
        missionNamespace setVariable [QGVAR(hudWarningActive), false];
    };
};
