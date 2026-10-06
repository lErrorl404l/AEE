/*
Wildlife asset map (generated).

This file is GENERATED. The generator tools/validation/gen_wildlife_ecology.py
writes it from the validated wildlife corpus under data/wildlife/. Do not
edit it by hand. Edit the corpus and regenerate it.

One row per sound group and per faunal group, sorted by kind then id. A row
has six columns:

  0 kind           string, "sound" or "fauna"
  1 id             string, the sound-group key or the family key
  2 identity       string, "CONFIRMED", "UNCONFIRMED" or "UNKNOWN"
  3 media          array of strings, a raw a3 path or a CfgSFX class
  4 fauna_classes  array of vanilla CfgVehicles Animals classes
  5 species        string, empty when the recording is not given a species

A media string with a dot is a raw vanilla .wss file. A media string without
a dot is a vanilla CfgSFX class. An UNKNOWN or UNCONFIRMED recording is
never given a species. The sound map aee_wildlife_fnc_speciesSound reads
this table.
*/
[
    ["fauna", "arid", "CONFIRMED", [], ["Goat_random_F", "Snake_vipera_random_F", "Snake_random_F", "Rabbit_F"], ""],
    ["fauna", "cold", "CONFIRMED", [], ["Sheep_random_F", "Goat_random_F", "Rabbit_F"], ""],
    ["fauna", "settlement", "CONFIRMED", [], ["Hen_random_F", "Cock_random_F", "Fin_sand_F", "Alsatian_Black_F"], ""],
    ["fauna", "temperate", "CONFIRMED", [], ["Sheep_random_F", "Goat_random_F", "Hen_random_F", "Cock_random_F", "Cock_white_F", "Rabbit_F", "Snake_random_F", "Fin_random_F", "Alsatian_Random_F"], ""],
    ["fauna", "tropical", "CONFIRMED", [], ["Snake_random_F", "Snake_vipera_random_F", "Hen_random_F", "Cock_random_F", "Turtle_F"], ""],
    ["fauna", "water", "CONFIRMED", [], ["Turtle_F", "Salema_F", "Ornate_random_F", "Mackerel_F", "Tuna_F", "Mullet_F", "CatShark_F"], ""],
    ["sound", "chicken", "CONFIRMED", [], [], ""],
    ["sound", "chicken_grill", "UNKNOWN", ["a3\sounds_f\ambient\animals\chicken_grill_1.wss", "a3\sounds_f\ambient\animals\chicken_grill_2.wss"], [], ""],
    ["sound", "cicada", "UNKNOWN", [], [], ""],
    ["sound", "cricket", "CONFIRMED", [], [], ""],
    ["sound", "deer", "CONFIRMED", [], [], ""],
    ["sound", "dog", "UNCONFIRMED", ["a3\sounds_f\ambient\animals\dog1.wss", "a3\sounds_f\ambient\animals\dog2.wss", "a3\sounds_f\ambient\animals\dog3.wss", "a3\sounds_f\ambient\animals\dog4.wss"], [], ""],
    ["sound", "fear", "CONFIRMED", ["a3\sounds_f\ambient\animals\scared_animal1.wss", "a3\sounds_f\ambient\animals\scared_animal2.wss", "a3\sounds_f\ambient\animals\scared_animal3.wss", "a3\sounds_f\ambient\animals\scared_animal4.wss", "a3\sounds_f\ambient\animals\scared_animal5.wss", "a3\sounds_f\ambient\animals\scared_animal6.wss", "a3\sounds_f\ambient\animals\scared_animal7.wss"], [], ""],
    ["sound", "frog", "UNKNOWN", [], [], ""],
    ["sound", "goat", "CONFIRMED", [], [], ""],
    ["sound", "gull", "UNCONFIRMED", ["a3\sounds_f\ambient\animals\Seagul_1.wss"], [], ""],
    ["sound", "hen", "UNCONFIRMED", ["a3\sounds_f\ambient\animals\hen1.wss", "a3\sounds_f\ambient\animals\hen2.wss", "a3\sounds_f\ambient\animals\hen3.wss"], [], ""],
    ["sound", "night_insect", "CONFIRMED", [], [], ""],
    ["sound", "none", "UNKNOWN", [], [], ""],
    ["sound", "owl", "CONFIRMED", ["a3\sounds_f\ambient\animals\owl1.wss", "a3\sounds_f\ambient\animals\owl2.wss", "a3\sounds_f\ambient\animals\owl3.wss", "Owl"], [], ""],
    ["sound", "sarance", "UNKNOWN", ["a3\sounds_f\ambient\animals\sarance1.wss", "a3\sounds_f\ambient\animals\sarance2.wss", "a3\sounds_f\ambient\animals\sarance3.wss", "a3\sounds_f\ambient\animals\sarance4.wss"], [], ""],
    ["sound", "sheep", "UNCONFIRMED", ["a3\animals_f_beta\sheep\data\sound\sheep1.wss", "a3\animals_f_beta\sheep\data\sound\sheep2.wss", "a3\animals_f_beta\sheep\data\sound\sheep3.wss", "a3\animals_f_beta\sheep\data\sound\sheep4.wss", "a3\animals_f_beta\sheep\data\sound\sheep5.wss"], [], ""],
    ["sound", "songbird", "CONFIRMED", ["a3\sounds_f\ambient\animals\birds1.wss", "a3\sounds_f\ambient\animals\birds2.wss", "a3\sounds_f\ambient\animals\birds3.wss", "a3\sounds_f\ambient\animals\birds4.wss", "a3\sounds_f\ambient\animals\birds5.wss"], [], ""],
    ["sound", "water", "CONFIRMED", ["Sound_Stream"], [], ""],
    ["sound", "wolf", "CONFIRMED", [], [], ""]
]
