/*
Vanilla ambient-sound manifest (reuse only, never fetch or generate).

Each row is [contextKey, vanillaPathOrCfgSFXClass, maxDistance, baseGain].
A row whose second value contains a dot is a raw vanilla .wss file, loaded
with playSound3D and the local argument true.  A row without a dot is a
vanilla CfgSFX class, loaded client-local with createSoundSourceLocal as a
looping positional bed.  contextKey is the key fnc_soundBedForContext returns.

A context the plan requests but vanilla cannot supply is a recorded finding
in docs/wiki/research/wildlife-ambience-dossier.md, never a fetch.  The
night-insect, deer and wolf contexts are findings for that reason.

The day contexts carry an open-ground row set under the day_<family> key and
a forest row set under the day_<family>_forest key.  Both reuse the same
vanilla bird files.  The forest rows carry the higher base gain, because a
wooded bed is denser than the open field in the same climate.
*/

[
    ["water", "Sound_Stream", 120, 0.60],
    ["night", "Owl", 120, 0.45],
    ["night", "a3\sounds_f\ambient\animals\owl1.wss", 120, 0.70],
    ["night", "a3\sounds_f\ambient\animals\owl2.wss", 120, 0.70],
    ["night", "a3\sounds_f\ambient\animals\owl3.wss", 120, 0.70],
    ["day_temperate", "a3\sounds_f\ambient\animals\birds1.wss", 120, 0.70],
    ["day_temperate", "a3\sounds_f\ambient\animals\birds2.wss", 120, 0.70],
    ["day_temperate", "a3\sounds_f\ambient\animals\birds3.wss", 120, 0.70],
    ["day_temperate", "a3\sounds_f\ambient\animals\birds4.wss", 120, 0.70],
    ["day_temperate", "a3\sounds_f\ambient\animals\birds5.wss", 120, 0.70],
    ["day_cold", "a3\sounds_f\ambient\animals\birds1.wss", 120, 0.55],
    ["day_cold", "a3\sounds_f\ambient\animals\birds4.wss", 120, 0.55],
    ["day_arid", "a3\sounds_f\ambient\animals\birds3.wss", 120, 0.45],
    ["day_arid", "a3\sounds_f\ambient\animals\birds5.wss", 120, 0.45],
    ["day_tropical", "a3\sounds_f\ambient\animals\birds2.wss", 120, 0.75],
    ["day_tropical", "a3\sounds_f\ambient\animals\birds3.wss", 120, 0.75],
    ["day_temperate_forest", "a3\sounds_f\ambient\animals\birds1.wss", 120, 0.85],
    ["day_temperate_forest", "a3\sounds_f\ambient\animals\birds2.wss", 120, 0.85],
    ["day_temperate_forest", "a3\sounds_f\ambient\animals\birds3.wss", 120, 0.85],
    ["day_temperate_forest", "a3\sounds_f\ambient\animals\birds4.wss", 120, 0.85],
    ["day_temperate_forest", "a3\sounds_f\ambient\animals\birds5.wss", 120, 0.85],
    ["day_cold_forest", "a3\sounds_f\ambient\animals\birds1.wss", 120, 0.70],
    ["day_cold_forest", "a3\sounds_f\ambient\animals\birds4.wss", 120, 0.70],
    ["day_arid_forest", "a3\sounds_f\ambient\animals\birds3.wss", 120, 0.60],
    ["day_arid_forest", "a3\sounds_f\ambient\animals\birds5.wss", 120, 0.60],
    ["day_tropical_forest", "a3\sounds_f\ambient\animals\birds2.wss", 120, 0.90],
    ["day_tropical_forest", "a3\sounds_f\ambient\animals\birds3.wss", 120, 0.90],
    ["farm", "a3\sounds_f\ambient\animals\hen1.wss", 120, 0.55],
    ["farm", "a3\sounds_f\ambient\animals\hen2.wss", 120, 0.55],
    ["farm", "a3\sounds_f\ambient\animals\hen3.wss", 120, 0.55],
    ["farm", "a3\sounds_f\ambient\animals\dog1.wss", 120, 0.60],
    ["farm", "a3\sounds_f\ambient\animals\dog2.wss", 120, 0.60],
    ["farm", "a3\sounds_f\ambient\animals\dog3.wss", 120, 0.60],
    ["farm", "a3\sounds_f\ambient\animals\dog4.wss", 120, 0.60],
    ["coast", "a3\sounds_f\ambient\animals\seagul_1.wss", 120, 0.60],
    ["grass", "a3\animals_f_beta\sheep\data\sound\sheep1.wss", 120, 0.55],
    ["grass", "a3\animals_f_beta\sheep\data\sound\sheep2.wss", 120, 0.55],
    ["grass", "a3\animals_f_beta\sheep\data\sound\sheep3.wss", 120, 0.55],
    ["grass", "a3\animals_f_beta\sheep\data\sound\sheep4.wss", 120, 0.55],
    ["grass", "a3\animals_f_beta\sheep\data\sound\sheep5.wss", 120, 0.55],
    ["fear", "a3\sounds_f\ambient\animals\scared_animal1.wss", 120, 0.90],
    ["fear", "a3\sounds_f\ambient\animals\scared_animal2.wss", 120, 0.90],
    ["fear", "a3\sounds_f\ambient\animals\scared_animal3.wss", 120, 0.90],
    ["fear", "a3\sounds_f\ambient\animals\scared_animal4.wss", 120, 0.90],
    ["fear", "a3\sounds_f\ambient\animals\scared_animal5.wss", 120, 0.90],
    ["fear", "a3\sounds_f\ambient\animals\scared_animal6.wss", 120, 0.90],
    ["fear", "a3\sounds_f\ambient\animals\scared_animal7.wss", 120, 0.90]
]
