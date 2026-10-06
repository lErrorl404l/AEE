/*
Wildlife ecology corpus (generated).

This file is GENERATED. The generator tools/validation/gen_wildlife_ecology.py
writes it from the validated wildlife corpus under data/wildlife/. Do not
edit it by hand. Edit the corpus and regenerate it.

One row per species group, sorted by group id. A row has fourteen columns:

  0  family           string, a Koppen family or an overlay
  1  group_id         string, the stable corpus key
  2  taxa             array of strings
  3  activity         string, "diurnal", "nocturnal" or "crepuscular"
  4  season_months    array of month numbers, 1 to 12
  5  temp_band        array [min_c, max_c]
  6  wind_rule        array [limit_ms, suppression]
  7  rain_rule        array [limit, suppression, triggers]
  8  gregariousness   string
  9  habitat_weights  array [foliage, surface, water, structures], each 0 to 1
  10 temporal_bins    array of seven weights, each 0 to 1
  11 dolbear          bool, the Dolbear shortcut drives the rate
  12 sound_group      string, a key in asset_map.sqf
  13 grade            string, the group source grade

The seven temporal bins, in order, are pre_dawn, dawn, morning, midday,
afternoon, dusk and night. The pure matcher aee_wildlife_fnc_getSpeciesMatch
reads this table. The Dolbear shortcut is the only cricket rate source.
*/
[
    ["arid", "arid_amphibian", ["Amphibia"], "nocturnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [10, 40], [6, 0.6], [1, 0, true], "chorus", [0.1, 0, 0.9, 0], [0.4, 0.1, 0, 0, 0, 0.5, 0.9], false, "frog", "R"],
    ["arid", "arid_bird_dawn", ["Aves"], "diurnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [0, 45], [8, 0.7], [0.6, 0.5, false], "flocking", [0.2, 0, 0, 0], [0.6, 1, 0.5, 0.05, 0.05, 0.4, 0], false, "songbird", "S"],
    ["arid", "arid_bird_day", ["Aves"], "diurnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [0, 45], [8, 0.7], [0.6, 0.5, false], "mixed", [0.2, 0, 0, 0], [0.2, 0.5, 0.7, 0.3, 0.4, 0.4, 0], false, "songbird", "R"],
    ["arid", "arid_bird_night", ["Aves"], "nocturnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [0, 40], [6, 0.6], [0.4, 0.4, false], "solitary", [0.2, 0, 0, 0], [0.2, 0, 0, 0, 0, 0.3, 1], false, "owl", "R"],
    ["arid", "arid_insect_cricket", ["Insecta"], "nocturnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [10, 45], [5, 0.7], [0.4, 0.6, false], "solitary", [0.2, 0.7, 0, 0], [0.3, 0, 0, 0, 0, 0.6, 1], true, "cricket", "S"],
    ["arid", "arid_insect_grasshopper", ["Insecta"], "diurnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [15, 45], [5, 0.6], [0.4, 0.5, false], "solitary", [0.2, 0.7, 0, 0], [0, 0.2, 0.5, 0.9, 0.9, 0.4, 0], false, "cicada", "R"],
    ["arid", "arid_mammal", ["Mammalia"], "nocturnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [0, 45], [10, 0.5], [0.4, 0.4, false], "solitary", [0.2, 0, 0, 0], [0.2, 0, 0, 0, 0, 0.5, 0.8], false, "none", "R"],
    ["cold", "cold_amphibian", ["Amphibia"], "nocturnal", [3, 4, 5, 6], [2, 28], [6, 0.6], [1, 0, true], "chorus", [0.2, 0, 0.8, 0], [0.4, 0.1, 0, 0, 0, 0.5, 0.9], false, "frog", "R"],
    ["cold", "cold_bird_dawn", ["Aves"], "diurnal", [4, 5, 6, 7], [-10, 30], [8, 0.6], [0.6, 0.5, false], "flocking", [0.6, 0, 0, 0], [0.6, 1, 0.5, 0.05, 0.05, 0.4, 0], false, "songbird", "S"],
    ["cold", "cold_bird_tundra", ["Aves"], "diurnal", [6, 7, 8], [-20, 15], [10, 0.6], [0.5, 0.5, false], "flocking", [0.1, 0, 0, 0], [0.6, 1, 0.5, 0.05, 0.05, 0.4, 0], false, "songbird", "R"],
    ["cold", "cold_insect_cricket", ["Insecta"], "nocturnal", [6, 7, 8], [5, 30], [5, 0.7], [0.5, 0.6, false], "solitary", [0.3, 0.6, 0, 0], [0.3, 0, 0, 0, 0, 0.6, 1], true, "cricket", "S"],
    ["cold", "cold_insect_mosquito", ["Insecta"], "crepuscular", [6, 7, 8], [5, 30], [4, 0.6], [0.5, 0.4, false], "swarm", [0.3, 0, 0.2, 0], [0.5, 0.4, 0.2, 0.1, 0.1, 0.5, 0.4], false, "none", "R"],
    ["cold", "cold_mammal_deer", ["Mammalia"], "crepuscular", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [-20, 30], [10, 0.5], [0.5, 0.4, false], "herd", [0.8, 0, 0, 0], [0.2, 0, 0, 0, 0, 0.5, 0.8], false, "deer", "R"],
    ["cold", "cold_mammal_wolf", ["Mammalia"], "nocturnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [-25, 25], [12, 0.4], [0.5, 0.4, false], "pack", [0.7, 0, 0, 0], [0.2, 0, 0, 0, 0, 0.5, 0.8], false, "wolf", "R"],
    ["settlement", "settlement_bird", ["Aves"], "diurnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [0, 40], [8, 0.6], [0.7, 0.4, false], "flocking", [0.1, 0, 0, 0.8], [0.2, 0.5, 0.6, 0.6, 0.6, 0.5, 0.1], false, "songbird", "R"],
    ["settlement", "settlement_bird_poultry", ["Aves"], "diurnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [0, 40], [8, 0.6], [0.7, 0.4, false], "flocking", [0.1, 0, 0, 0.9], [0.2, 0.5, 0.6, 0.6, 0.6, 0.5, 0.1], false, "hen", "R"],
    ["settlement", "settlement_mammal", ["Mammalia"], "diurnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [0, 40], [10, 0.5], [0.7, 0.3, false], "pair", [0.1, 0, 0, 0.9], [0.2, 0.3, 0.4, 0.4, 0.4, 0.5, 0.4], false, "dog", "R"],
    ["temperate", "temperate_amphibian", ["Amphibia"], "nocturnal", [3, 4, 5, 6], [2, 30], [6, 0.6], [1, 0, true], "chorus", [0.2, 0, 0.8, 0], [0.4, 0.1, 0, 0, 0, 0.5, 0.9], false, "frog", "R"],
    ["temperate", "temperate_bird_dawn", ["Aves"], "diurnal", [3, 4, 5, 6], [0, 35], [8, 0.7], [0.7, 0.5, false], "territorial", [0.6, 0, 0, 0.1], [0.6, 1, 0.5, 0.05, 0.05, 0.4, 0], false, "songbird", "S"],
    ["temperate", "temperate_bird_day", ["Aves"], "diurnal", [4, 5, 6, 7], [0, 35], [8, 0.7], [0.7, 0.5, false], "mixed", [0.5, 0, 0, 0.1], [0.2, 0.5, 0.7, 0.3, 0.4, 0.4, 0], false, "songbird", "S"],
    ["temperate", "temperate_bird_night", ["Aves"], "nocturnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [0, 35], [6, 0.6], [0.5, 0.4, false], "solitary", [0.5, 0, 0, 0], [0.2, 0, 0, 0, 0, 0.3, 1], false, "owl", "S"],
    ["temperate", "temperate_insect_cicada", ["Insecta"], "diurnal", [6, 7, 8], [18, 40], [5, 0.6], [0.5, 0.5, false], "chorus", [0.5, 0, 0, 0], [0, 0.2, 0.5, 0.9, 0.9, 0.4, 0], false, "cicada", "S"],
    ["temperate", "temperate_insect_cricket", ["Insecta"], "nocturnal", [5, 6, 7, 8, 9], [5, 30], [5, 0.7], [0.5, 0.6, false], "solitary", [0.3, 0.6, 0, 0], [0.3, 0, 0, 0, 0, 0.6, 1], true, "cricket", "S"],
    ["temperate", "temperate_mammal", ["Mammalia"], "nocturnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [0, 35], [10, 0.5], [0.5, 0.4, false], "solitary", [0.5, 0, 0, 0], [0.2, 0, 0, 0, 0, 0.5, 0.8], false, "none", "R"],
    ["tropical", "tropical_amphibian", ["Amphibia"], "nocturnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [18, 35], [6, 0.6], [1, 0, true], "chorus", [0.2, 0, 0.8, 0], [0.4, 0.1, 0, 0, 0, 0.5, 0.9], false, "frog", "R"],
    ["tropical", "tropical_bird_dawn", ["Aves"], "diurnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [15, 40], [8, 0.7], [0.7, 0.5, false], "flocking", [0.6, 0, 0, 0.1], [0.6, 1, 0.5, 0.05, 0.05, 0.4, 0], false, "songbird", "S"],
    ["tropical", "tropical_bird_day", ["Aves"], "diurnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [15, 42], [8, 0.7], [0.7, 0.5, false], "mixed", [0.5, 0, 0, 0.1], [0.2, 0.5, 0.7, 0.3, 0.4, 0.4, 0], false, "songbird", "S"],
    ["tropical", "tropical_bird_night", ["Aves"], "nocturnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [12, 35], [6, 0.6], [0.5, 0.4, false], "solitary", [0.4, 0, 0, 0], [0.2, 0, 0, 0, 0, 0.3, 1], false, "owl", "R"],
    ["tropical", "tropical_insect_cicada", ["Insecta"], "diurnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [20, 40], [5, 0.6], [0.6, 0.5, false], "chorus", [0.5, 0, 0, 0], [0, 0.2, 0.5, 0.9, 0.9, 0.4, 0], false, "cicada", "R"],
    ["tropical", "tropical_insect_cricket", ["Insecta"], "nocturnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [15, 35], [5, 0.7], [0.5, 0.6, false], "solitary", [0.3, 0.6, 0, 0], [0.3, 0, 0, 0, 0, 0.6, 1], true, "cricket", "S"],
    ["tropical", "tropical_mammal", ["Mammalia"], "nocturnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [15, 40], [10, 0.5], [0.5, 0.4, false], "solitary", [0.5, 0, 0, 0], [0.2, 0, 0, 0, 0, 0.5, 0.8], false, "none", "R"],
    ["water", "water_amphibian", ["Amphibia"], "nocturnal", [3, 4, 5, 6], [2, 30], [6, 0.6], [1, 0, true], "chorus", [0.1, 0, 0.9, 0], [0.4, 0.1, 0, 0, 0, 0.5, 0.9], false, "frog", "R"],
    ["water", "water_bird", ["Aves"], "diurnal", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [2, 30], [10, 0.6], [0.8, 0.4, false], "flocking", [0.1, 0, 0.9, 0], [0.4, 0.8, 0.6, 0.4, 0.4, 0.6, 0.2], false, "gull", "R"],
    ["water", "water_insect", ["Insecta"], "diurnal", [6, 7, 8], [12, 38], [5, 0.6], [0.6, 0.5, false], "solitary", [0.1, 0, 0.9, 0], [0, 0.2, 0.5, 0.9, 0.9, 0.4, 0], false, "none", "R"]
]
