#include "..\..\script_component.hpp"
/*
Backpack properties (issue #119).

Classifies the backpack slot (CfgVehicles B_ classes) by family keywords
and returns [weight kg (the pack itself), armor NIJ 0..3, nirReflectance,
clo].  The values are the researched IRL figures from equipment-library.md.
The pack CONTENTS are added separately (the engine load command).

Groups (sortable by country -> company -> era):
  WW1-WW2        | M1910 haversack (US), 1908/1937 Pattern (UK),
    Tornister (DE), M1928/M1936/M1941 (US), RD-54 (USSR)
  Cold War       | M1956/M1967, ALICE (US), 58 Pattern, PLCE, SAS
    bergen (UK), Sidor (USSR), F1 (FR)
  Modern         | MOLLE II, ILBE, FILBE (US), Virtus, Berghaus (UK),
    Tortila, 6Sh118 (RU), NICE/Kifaru/Eberlestock (commercial)
  Vanilla        | Assault/Tactical/Field/Kitbag/Bergen/Carryall

Arguments:
  0: unit (OBJECT, default player)

Returns [weight, armor, nirReflectance, clo].
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { [5.0, 0, 0.40, 0.10] };

private _packItem = backpack _unit;
if (_packItem == "") exitWith { [5.0, 0, 0.40, 0.10] };

private _packDef = [5.0, 0, 0.40, 0.10];
private _b = toLower _packItem;
switch (true) do {
    // ── Russia: Ratnik packs ──
    // 6Sh118 (60 L, 3.5 kg) + 6Sh117 vest.
    case (_b find "6sh118" >= 0 ||
          _b find "6sh117" >= 0 ||
          _b find "6b38" >= 0):      { [3.5, 0, 0.40, 0.10] };
    // RD-54 (sap-perka assault pack, 16.5 L, 1.3 kg).
    case (_b find "rd54" >= 0):      { [1.3, 0, 0.40, 0.08] };
    // Sidor (veshmeshok, 25-30 L) / Tortila (40 L, 2.15 kg).
    case (_b find "sidor" >= 0):     { [2.2, 0, 0.40, 0.09] };
    case (_b find "tort" >= 0):      { [2.15, 0, 0.40, 0.09] };
    // ── USA military ──
    // ALICE (Large 62 L, 3.2 kg; Medium 30-33 L, lighter).
    case (_b find "alice" >= 0):     { [3.2, 0, 0.40, 0.10] };
    // MOLLE II (Large 65.5 L, 3.6 kg; Medium 49 L, 1.6 kg).
    case (_b find "molle" >= 0):     { [3.6, 0, 0.40, 0.10] };
    // ILBE (82 L, 3.6 kg, Arc'teryx) / FILBE (81 L, 4.3 kg).
    case (_b find "ilbe" >= 0):      { [3.6, 0, 0.40, 0.11] };
    case (_b find "filbe" >= 0):     { [4.3, 0, 0.40, 0.11] };
    // ── USA commercial ──
    // Eagle Industries III (assault pack) + Falcon II + M240/M249
    // support packs + insurgent packs.
    case (_b find "eagle" >= 0 ||
          _b find "falcon" >= 0 ||
          _b find "pack_slackman" >= 0 ||
          _b find "ins_pack" >= 0):  { [2.5, 0, 0.40, 0.09] };
    // ── UK ──
    // PLCE bergen (90 L, 2.45 kg) / Virtus 90 L (3.5 kg).
    case (_b find "plce" >= 0):      { [2.45, 0, 0.40, 0.10] };
    case (_b find "virtus" >= 0):    { [3.5, 0, 0.40, 0.10] };
    // Berghaus (Munro 35 L, 1.0 kg; Vulcan 100 L).
    case (_b find "munro" >= 0 ||
          _b find "vulcan" >= 0 ||
          _b find "berghaus" >= 0):  { [2.0, 0, 0.40, 0.09] };
    // ── Russia: patrol packs + specials ──
    // RK-SHT-30 (6Sh104-series) + UMBTS assault pack + medic bag +
    // R-148 radio pack + RPG ammunition packs.
    case (_b find "rk_sht" >= 0 ||
          _b find "6sh104" >= 0 ||
          _b find "umbts" >= 0 ||
          _b find "medic_bag" >= 0 ||
          _b find "r148" >= 0 ||
          _b find "rpg" >= 0):       { [2.5, 0, 0.40, 0.09] };
    // ── Vanilla large packs (empty weights) ──
    case (_b find "assaultpack" >= 0): { [3.0, 0, 0.40, 0.10] };
    case (_b find "tacticalpack" >= 0):{ [3.5, 0, 0.40, 0.10] };
    case (_b find "fieldpack" >= 0):   { [4.0, 0, 0.40, 0.10] };
    case (_b find "kitbag" >= 0):      { [4.0, 0, 0.40, 0.10] };
    case (_b find "bergen" >= 0):      { [5.0, 0, 0.40, 0.11] };
    case (_b find "carryall" >= 0):    { [6.0, 0, 0.40, 0.12] };
    case (_b find "radiobag" >= 0):    { [2.0, 0, 0.40, 0.09] };
    // Generic rucksack/backpack fallback.
    case (_b find "backpack" >= 0 ||
          _b find "rucksack" >= 0):    { [5.0, 0, 0.40, 0.10] };
    default                        { _packDef };
};
