/*
Vanilla animal species table (reuse only, never fetch and never add a class).

Each row is [biomeFamily, [vanillaClass, ...]].  The biome families are the
Koppen first-letter groups: "a" tropical, "b" arid, "d" and "e" cold, and
everything else temperate.  The "water" overlay holds the shore and fish
classes.  The "settlement" overlay holds the farm and dog classes, reserved
for a future structure signal.

Every class ends in _random_F or _F and is a confirmed vanilla CfgVehicles
Animals class (BIKI CfgVehicles Animals, Wayback 2025-01-16).  There is no
cow class, no owl unit class and no dolphin class in vanilla.  Those are
findings in docs/wiki/research/wildlife-ambience-dossier.md, never classes
here.
*/

[
    ["cold", ["Sheep_random_F", "Goat_random_F", "Rabbit_F"]],
    ["temperate", [
        "Sheep_random_F", "Goat_random_F", "Hen_random_F", "Cock_random_F",
        "Cock_white_F", "Rabbit_F", "Snake_random_F", "Fin_random_F",
        "Alsatian_Random_F"
    ]],
    ["arid", ["Goat_random_F", "Snake_vipera_random_F", "Snake_random_F", "Rabbit_F"]],
    ["tropical", ["Snake_random_F", "Snake_vipera_random_F", "Hen_random_F", "Cock_random_F", "Turtle_F"]],
    ["water", ["Turtle_F", "Salema_F", "Ornate_random_F", "Mackerel_F", "Tuna_F", "Mullet_F", "CatShark_F"]],
    ["settlement", ["Hen_random_F", "Cock_random_F", "Fin_sand_F", "Alsatian_Black_F"]]
]
