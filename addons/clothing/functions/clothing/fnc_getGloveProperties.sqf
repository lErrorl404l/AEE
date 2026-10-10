#include "..\..\script_component.hpp"
/*
Glove classifier (issue #119).

Arma has no gloves slot: gloves ride inside the uniform model, and the
uniform classname carries the handwear signal (Mechanix/Oakley/PIG
keywords, the UKSF/Zulu "_KP_P"/"_NKP_P" gloves-on scheme, Nomex flight
gloves, ECWCS cold-weather gloves).  The ACE Extended Arsenal makes
gloves a selectable visible item, so modded uniforms genuinely carry
the glove choice in their classname.

Handwear insulation (Gonzalez 1998, measured with ECWCS): light duty
glove 0.86 clo, heavy duty glove 1.05 clo, Arctic mitten 1.46 clo.

Arguments:
  0: unit (OBJECT, default player)

Returns the glove insulation in clo (0 = no gloves).
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { 0.0 };

private _uniformItem = uniform _unit;
if (_uniformItem == "") exitWith { 0.0 };
private _uniform = toLower _uniformItem;

// The uniform displayName is the player-readable arsenal name and
// carries the same glove signal ("Mechanix", "Oakley", "gloves").
private _disp = toLower (getText (configFile >> "CfgWeapons" >> _uniformItem >> "displayName"));

switch (true) do {
    // Arctic mittens: the highest hand insulation (Gonzalez 1.46).
    case (_uniform find "mitten" >= 0 ||
          _disp find "mitten" >= 0):            { 1.46 };
    // Heavy/insulated gloves: cold-weather gloves, ECWCS, wool liners
    // (Gonzalez heavy duty 1.05).
    case (_uniform find "glove" >= 0 ||
          _uniform find "ecwcs" >= 0 ||
          _uniform find "cold" >= 0 ||
          _uniform find "winter" >= 0 ||
          _uniform find "arctic" >= 0 ||
          _uniform find "lined" >= 0 ||
          _disp find "glove" >= 0 ||
          _disp find "cold" >= 0 ||
          _disp find "winter" >= 0):             { 1.05 };
    // Light duty gloves: Mechanix/Oakley/PIG/Nomex flight gloves
    // (Gonzalez light duty 0.86) + the UKSF/Zulu gloves-on scheme.
    case (_uniform find "mechanix" >= 0 ||
          _uniform find "oakley" >= 0 ||
          _uniform find "pig_fdt" >= 0 ||
          _uniform find "nomex" >= 0 ||
          _uniform find "flight" >= 0 ||
          _uniform find "_kp_p" >= 0 ||
          _uniform find "_nkp_p" >= 0 ||
          _disp find "mechanix" >= 0 ||
          _disp find "oakley" >= 0 ||
          _disp find "gloves" >= 0):             { 0.86 };
    default                                     { 0.0 };
};
