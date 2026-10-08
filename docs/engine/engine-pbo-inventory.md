# Arma 3 Engine PBO Inventory

Where every engine PBO lives and what it carries.
Compiled 2026-10-08 from the Arma 3 install.

Method: parsed every PBO header directly (no unpacking). Config roots confirmed
by extracting and derapifying `config.bin` for the key PBOs. Sizes are on-disk
bytes. Companion `engine-pbo-inventory.json` holds the machine-readable form
(per-PBO tags, extension histogram, prefix, product, version, sample file list).

## 1. Summary

- PBOs found: **534** (517 standard, 17 non-standard mission archives).
- Config-bearing PBOs: **419**.
- Standard addon PBOs: **517**.
- Total on-disk size: **41.6 GiB**.

| Root | Identity | PBOs |
|---|---|---|
| `Dta` | Engine runtime data | 4 |
| `Addons` | Core engine addons | 196 |
| `@a3pm`, `@a3m`, `@ASCZ`, `z` | Third-party / developer mods | 317 |
| `MPMissions`, `mpmissions` | User mission archives (non-standard PBO) | 17 |

## 2. Tooling and commands

Tool: **HEMTT 1.22.0** (`hemtt`).

Unpack a whole PBO:
```
hemtt utils pbo unpack <pbo> <outdir>
```
Derapify a binarised config. It writes `config.cpp` BESIDE `config.bin`, not to stdout:
```
hemtt utils config derapify <dir>/config.bin
```
Inspect without unpacking (prefix, product, version, full file list):
```
hemtt utils pbo inspect --format json <pbo>
```
Extract one file without unpacking:
```
hemtt utils pbo extract <pbo> config.bin <out>
```

Worked example - read the CfgMarkers root from the UI PBO:
```
P="<Arma 3 install>/Addons/ui_f.pbo"
hemtt utils pbo extract "$P" config.bin ui_out/config.bin
hemtt utils config derapify ui_out/config.bin     # writes ui_out/config.cpp
grep -n 'class CfgMarkers' ui_out/config.cpp       # ui_f.cpp:89477
```

PBO header layout, confirmed from raw bytes: bytes 0-4 are the magic
`\x00sreV`, bytes 5-20 are 16 reserved bytes, then `key\0value\0` extension
pairs terminated by an empty key, then file entries `name\0 mime\0 <5 x uint32>`
terminated by an empty name. The stored data size is the last uint32 of the entry.

## 3. Grouped by domain

Each PBO with size (MiB), what it carries, and a one-line purpose.
`[ROOT]` marks a config-root PBO a mod overrides. `[FUNC]` marks SQF functions or modules.

### 3.1 `Dta/` - Engine runtime data (4 PBOs, 86.3 MiB)

| PBO | MiB | Carries | Purpose |
|---|---:|---|---|
| `bin.pbo` | 78.1 | - | Engine core config: every global root (CfgVehicles, CfgWeapons, CfgAmmo, CfgMagazines, CfgWorlds, CfgSurfaces, CfgMarkers, CfgLocationTypes, CfgMoves*, CfgCloudlets, CfgLights, RscMapControl). |
| `core.pbo` | 0.4 | models, textures, fonts | Engine core data: compiled shaders (.shdc) and core resources. |
| `languagecore_f.pbo` | 6.7 | data | Core engine stringtables (English). |
| `splashwindow.pbo` | 1.0 | textures | Startup splash window assets and config. |

### 3.2 `Addons/` - Core engine addons (196 PBOs, 15541.3 MiB)

| PBO | MiB | Carries | Purpose |
|---|---:|---|---|
| `3den.pbo` | 2.8 | config, models, textures, materials, scripts, sounds | Eden Editor (3DEN). |
| `3den_language.pbo` | 2.5 | data | Eden Editor (3DEN). |
| `a3.pbo` | 0.0 | textures | Root addon: shared environment and editor textures under a3\. |
| `air_f.pbo` | 113.1 | models, textures, materials, animation, scripts, data | Fixed-wing aircraft. |
| `air_f_beta.pbo` | 166.8 | models, textures, materials, animation, scripts, data | Fixed-wing aircraft - beta/legacy content. |
| `air_f_epb.pbo` | 25.7 | models, textures, materials, data | Fixed-wing aircraft - Episode-B content. |
| `air_f_epc.pbo` | 97.6 | models, textures, materials | Fixed-wing aircraft - Episode-C content. |
| `air_f_gamma.pbo` | 42.2 | models, textures, materials, animation | Fixed-wing aircraft - Gamma/free content. |
| `animals_f.pbo` **[ROOT]** | 15.5 | models, textures, materials, animation, scripts, sounds | Animals. |
| `animals_f_beta.pbo` **[ROOT]** | 124.3 | models, textures, materials, animation, scripts, sounds | Animals - beta/legacy content. |
| `anims_f.pbo` **[ROOT]** | 13.8 | data | Animation state configs and skeleton data (CfgMoves*, CfgGestures*); assets in anims_f_data. |
| `anims_f_bootcamp.pbo` **[ROOT]** | 26.6 | animation | Animation state, skeleton and motion data - Bootcamp campaign content. |
| `anims_f_data.pbo` **[ROOT]** | 233.4 | models, animation | Animation state, skeleton and motion data - data assets. |
| `anims_f_epa.pbo` **[ROOT]** | 114.9 | animation | Animation state, skeleton and motion data - Episode-A content. |
| `anims_f_epc.pbo` **[ROOT]** | 5.3 | animation | Animation state, skeleton and motion data - Episode-C content. |
| `anims_f_exp_a.pbo` **[ROOT]** | 19.7 | animation, data | Apex DLC: Animation state, skeleton and motion data - Expansion-A content. |
| `anims_f_mod.pbo` **[ROOT]** | 0.2 | animation | Animation state, skeleton and motion data - mod-support content. |
| `armor_f.pbo` | 165.9 | textures, materials | Armoured tracked vehicles. |
| `armor_f_beta.pbo` | 379.2 | models, textures, materials, animation | Armoured tracked vehicles - beta/legacy content. |
| `armor_f_decade.pbo` | 14.0 | models, textures, materials | Armoured tracked vehicles - Decade (free) content. |
| `armor_f_epb.pbo` | 139.7 | models, textures, materials | Armoured tracked vehicles - Episode-B content. |
| `armor_f_epc.pbo` | 13.7 | models, textures, materials | Armoured tracked vehicles - Episode-C content. |
| `armor_f_gamma.pbo` | 300.5 | models, textures, materials, animation | Armoured tracked vehicles - Gamma/free content. |
| `baseconfig_f.pbo` **[ROOT]** | 0.0 | - | Base class definitions for inheritance (CfgPatches only, no assets). |
| `boat_f.pbo` | 57.4 | models, textures, materials, animation | Boats and ships. |
| `boat_f_beta.pbo` | 19.8 | models, textures, materials | Boats and ships - beta/legacy content. |
| `boat_f_epc.pbo` | 7.8 | models, textures, materials | Boats and ships - Episode-C content. |
| `boat_f_gamma.pbo` | 52.2 | models, textures, materials | Boats and ships - Gamma/free content. |
| `cargoposes_f.pbo` | 56.3 | animation | Cargo and seat pose animation. |
| `characters_f.pbo` **[ROOT]** | 569.6 | models, textures, materials, animation, scripts | Soldiers, heads, uniforms and characters. |
| `characters_f_beta.pbo` **[ROOT]** | 45.4 | models, textures, materials | Soldiers, heads, uniforms and characters - beta/legacy content. |
| `characters_f_bootcamp.pbo` **[ROOT]** | 50.2 | models, textures, materials, scripts | Soldiers, heads, uniforms and characters - Bootcamp campaign content. |
| `characters_f_decade.pbo` **[ROOT]** | 7.6 | textures, materials | Soldiers, heads, uniforms and characters - Decade (free) content. |
| `characters_f_epa.pbo` **[ROOT]** | 25.9 | models, textures, materials | Soldiers, heads, uniforms and characters - Episode-A content. |
| `characters_f_epb.pbo` **[ROOT]** | 54.3 | models, textures, materials | Soldiers, heads, uniforms and characters - Episode-B content. |
| `characters_f_epc.pbo` **[ROOT]** | 24.9 | models, textures, materials | Soldiers, heads, uniforms and characters - Episode-C content. |
| `characters_f_gamma.pbo` **[ROOT]** | 30.9 | models, textures, materials | Soldiers, heads, uniforms and characters - Gamma/free content. |
| `data_f.pbo` **[ROOT]** | 285.3 | models, textures, materials, scripts | Shared models, textures and global data. |
| `data_f_bootcamp.pbo` **[ROOT]** | 1.5 | models, textures, materials | Shared models, textures and global data - Bootcamp campaign content. |
| `data_f_decade.pbo` **[ROOT]** | 0.0 | - | Shared models, textures and global data - Decade (free) content. |
| `data_f_exp_a.pbo` **[ROOT]** | 1.2 | textures | Apex DLC: Shared models, textures and global data - Expansion-A content. |
| `data_f_exp_b.pbo` **[ROOT]** | 0.5 | textures | Apex DLC: Shared models, textures and global data - Expansion-B content. |
| `data_f_mod.pbo` **[ROOT]** | 0.4 | textures | Shared models, textures and global data - mod-support content. |
| `data_f_warlords.pbo` **[ROOT]** | 1.2 | textures, sounds | Shared models, textures and global data - Warlords content. |
| `drones_f.pbo` | 75.2 | models, textures, materials | UAV and UGV drones. |
| `dubbing_f.pbo` | 3.8 | animation, sounds | Voice dubbing audio. |
| `dubbing_f_beta.pbo` | 6.5 | animation, sounds | Voice dubbing audio - beta/legacy content. |
| `dubbing_f_bootcamp.pbo` | 10.4 | animation, sounds | Voice dubbing audio - Bootcamp campaign content. |
| `dubbing_f_epa.pbo` | 21.9 | animation, sounds | Voice dubbing audio - Episode-A content. |
| `dubbing_f_epb.pbo` | 29.1 | animation, sounds | Voice dubbing audio - Episode-B content. |
| `dubbing_f_epc.pbo` | 19.5 | animation, sounds | Voice dubbing audio - Episode-C content. |
| `dubbing_f_gamma.pbo` | 10.9 | animation, sounds | Voice dubbing audio - Gamma/free content. |
| `dubbing_f_warlords.pbo` | 0.7 | sounds | Voice dubbing audio - Warlords content. |
| `dubbing_radio_f.pbo` | 3.1 | animation, sounds | Radio-protocol voice audio. |
| `dubbing_radio_f_data_eng.pbo` | 456.1 | animation, sounds | Radio-protocol voice audio - data assets. |
| `dubbing_radio_f_data_engb.pbo` | 232.2 | animation, sounds | Radio-protocol voice audio - data assets. |
| `dubbing_radio_f_data_gre.pbo` | 227.9 | animation, sounds | Radio-protocol voice audio - data assets. |
| `dubbing_radio_f_data_per.pbo` | 121.9 | animation, sounds | Radio-protocol voice audio - data assets. |
| `dubbing_radio_f_data_vr.pbo` | 108.1 | animation, sounds | Radio-protocol voice audio - data assets. |
| `editor_f.pbo` | 0.1 | models, textures, scripts | Editor object models. |
| `editorpreviews_f.pbo` | 42.5 | textures | Eden editor preview thumbnails. |
| `editorpreviews_f_decade.pbo` | 0.6 | textures | Eden editor preview thumbnails - Decade (free) content. |
| `functions_f.pbo` **[FUNC]** | 5.8 | config, scripts | SQF function library (CfgFunctions). |
| `functions_f_bootcamp.pbo` **[FUNC]** | 0.7 | scripts | SQF function library (CfgFunctions) - Bootcamp campaign content. |
| `functions_f_decade.pbo` **[FUNC]** | 0.0 | scripts | SQF function library (CfgFunctions) - Decade (free) content. |
| `functions_f_epa.pbo` **[FUNC]** | 0.0 | config, scripts | SQF function library (CfgFunctions) - Episode-A content. |
| `functions_f_epc.pbo` **[FUNC]** | 0.0 | scripts | SQF function library (CfgFunctions) - Episode-C content. |
| `functions_f_exp_a.pbo` **[FUNC]** | 0.1 | config, scripts | Apex DLC: SQF function library (CfgFunctions) - Expansion-A content. |
| `functions_f_warlords.pbo` **[FUNC]** | 0.5 | scripts | SQF function library (CfgFunctions) - Warlords content. |
| `language_f.pbo` | 5.3 | data | Localisation stringtables. |
| `language_f_beta.pbo` | 1.4 | data | Localisation stringtables - beta/legacy content. |
| `language_f_bootcamp.pbo` | 0.9 | data | Localisation stringtables - Bootcamp campaign content. |
| `language_f_decade.pbo` | 0.1 | data | Localisation stringtables - Decade (free) content. |
| `language_f_epa.pbo` | 0.2 | data | Localisation stringtables - Episode-A content. |
| `language_f_epb.pbo` | 1.0 | data | Localisation stringtables - Episode-B content. |
| `language_f_epc.pbo` | 0.7 | data | Localisation stringtables - Episode-C content. |
| `language_f_exp_a.pbo` | 0.4 | data | Apex DLC: Localisation stringtables - Expansion-A content. |
| `language_f_exp_b.pbo` | 0.3 | data | Apex DLC: Localisation stringtables - Expansion-B content. |
| `language_f_gamma.pbo` | 1.5 | data | Localisation stringtables - Gamma/free content. |
| `language_f_mod.pbo` | 0.0 | data | Localisation stringtables - mod-support content. |
| `language_f_warlords.pbo` | 0.4 | data | Localisation stringtables - Warlords content. |
| `languagemissions_f.pbo` | 0.7 | data | Mission localisation stringtables. |
| `languagemissions_f_beta.pbo` | 1.2 | data | Mission localisation stringtables - beta/legacy content. |
| `languagemissions_f_bootcamp.pbo` | 1.5 | data | Mission localisation stringtables - Bootcamp campaign content. |
| `languagemissions_f_epa.pbo` | 2.7 | data | Mission localisation stringtables - Episode-A content. |
| `languagemissions_f_epb.pbo` | 3.0 | data | Mission localisation stringtables - Episode-B content. |
| `languagemissions_f_epc.pbo` | 2.0 | data | Mission localisation stringtables - Episode-C content. |
| `languagemissions_f_exp_a.pbo` | 0.1 | data | Apex DLC: Mission localisation stringtables - Expansion-A content. |
| `languagemissions_f_gamma.pbo` | 1.4 | data | Mission localisation stringtables - Gamma/free content. |
| `map_altis.pbo` **[ROOT]** | 174.9 | terrain | Altis terrain: world binary (.wrp) and CfgWorlds config. |
| `map_altis_data.pbo` | 14.8 | config, models, textures, materials | Altis terrain: terrain models, textures and materials. |
| `map_altis_data_layers.pbo` | 26.5 | materials | Altis terrain: terrain layer materials and masks. |
| `map_altis_data_layers_00_00.pbo` | 178.3 | textures | Altis terrain: terrain layer tile textures (satellite and mask). |
| `map_altis_data_layers_00_01.pbo` | 144.5 | textures | Altis terrain: terrain layer tile textures (satellite and mask). |
| `map_altis_data_layers_01_00.pbo` | 134.4 | textures | Altis terrain: terrain layer tile textures (satellite and mask). |
| `map_altis_data_layers_01_01.pbo` | 110.4 | textures | Altis terrain: terrain layer tile textures (satellite and mask). |
| `map_altis_scenes_f.pbo` | 12.7 | scripts | Altis terrain: scripted scene scripts. |
| `map_data.pbo` | 232.5 | textures, materials | Shared terrain data and materials used by all maps. |
| `map_stratis.pbo` **[ROOT]** | 25.2 | terrain | Stratis terrain: world binary (.wrp) and CfgWorlds config. |
| `map_stratis_data.pbo` | 7.4 | config, models, textures | Stratis terrain: terrain models, textures and materials. |
| `map_stratis_data_layers.pbo` | 69.5 | textures, materials | Stratis terrain: terrain layer materials and masks. |
| `map_stratis_scenes_f.pbo` | 25.8 | scripts | Stratis terrain: scripted scene scripts. |
| `map_vr.pbo` **[ROOT]** | 4.4 | config, models, textures, materials, terrain | VR training terrain: world binary (.wrp) and CfgWorlds config. |
| `map_vr_scenes_f.pbo` | 18.9 | scripts | VR training terrain: scripted scene scripts. |
| `misc_f.pbo` | 0.2 | models, textures, materials | Miscellaneous shared models and textures. |
| `missions_f.pbo` | 0.9 | config, scripts | Mission and campaign assets. |
| `missions_f_beta.pbo` | 3.2 | config, scripts | Mission and campaign assets - beta/legacy content. |
| `missions_f_beta_data.pbo` | 22.9 | models, textures, sounds | Mission and campaign assets - data assets. |
| `missions_f_beta_video.pbo` | 25.1 | - | Mission and campaign assets - intro/outro video. |
| `missions_f_bootcamp.pbo` | 3.1 | config, scripts | Mission and campaign assets - Bootcamp campaign content. |
| `missions_f_bootcamp_data.pbo` | 6.6 | textures, sounds | Mission and campaign assets - data assets. |
| `missions_f_bootcamp_video.pbo` | 13.8 | - | Mission and campaign assets - intro/outro video. |
| `missions_f_data.pbo` | 34.2 | textures, scripts, sounds | Mission and campaign assets - data assets. |
| `missions_f_epa.pbo` | 25.3 | config, scripts | Mission and campaign assets - Episode-A content. |
| `missions_f_epa_data.pbo` | 69.7 | textures, animation, sounds | Mission and campaign assets - data assets. |
| `missions_f_epa_video.pbo` | 326.6 | - | Mission and campaign assets - intro/outro video. |
| `missions_f_epb.pbo` | 0.0 | - | Mission and campaign assets - Episode-B content. |
| `missions_f_epc.pbo` | 0.0 | - | Mission and campaign assets - Episode-C content. |
| `missions_f_exp_a.pbo` | 0.8 | config, scripts | Apex DLC: Mission and campaign assets - Expansion-A content. |
| `missions_f_exp_a_data.pbo` | 0.8 | textures | Apex DLC: Mission and campaign assets - Expansion-A content. |
| `missions_f_gamma.pbo` | 3.6 | config, scripts | Mission and campaign assets - Gamma/free content. |
| `missions_f_gamma_data.pbo` | 44.9 | textures | Mission and campaign assets - data assets. |
| `missions_f_gamma_video.pbo` | 38.9 | - | Mission and campaign assets - intro/outro video. |
| `missions_f_video.pbo` | 24.0 | - | Mission and campaign assets - intro/outro video. |
| `missions_f_warlords.pbo` | 2.7 | config, scripts | Mission and campaign assets - Warlords content. |
| `modules_f.pbo` **[FUNC]** | 1.3 | config, scripts | Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `modules_f_beta.pbo` **[FUNC]** | 0.4 | scripts | Eden/Zeus editor modules (CfgVehicles, CfgFunctions) - beta/legacy content. |
| `modules_f_beta_data.pbo` **[FUNC]** | 0.6 | textures | Eden/Zeus editor modules (CfgVehicles, CfgFunctions) - data assets. |
| `modules_f_bootcamp.pbo` **[FUNC]** | 0.0 | textures, scripts | Eden/Zeus editor modules (CfgVehicles, CfgFunctions) - Bootcamp campaign content. |
| `modules_f_data.pbo` **[FUNC]** | 0.3 | textures | Eden/Zeus editor modules (CfgVehicles, CfgFunctions) - data assets. |
| `modules_f_epb.pbo` **[FUNC]** | 0.0 | scripts | Eden/Zeus editor modules (CfgVehicles, CfgFunctions) - Episode-B content. |
| `modules_f_exp_a.pbo` **[FUNC]** | 0.0 | - | Apex DLC: Eden/Zeus editor modules (CfgVehicles, CfgFunctions) - Expansion-A content. |
| `modules_f_warlords.pbo` **[FUNC]** | 0.0 | - | Eden/Zeus editor modules (CfgVehicles, CfgFunctions) - Warlords content. |
| `music_f.pbo` | 0.0 | - | Music. |
| `music_f_bootcamp.pbo` | 0.0 | - | Music - Bootcamp campaign content. |
| `music_f_bootcamp_music.pbo` | 11.6 | sounds | Music - music audio. |
| `music_f_epa.pbo` | 0.0 | - | Music - Episode-A content. |
| `music_f_epa_music.pbo` | 17.0 | sounds | Music - music audio. |
| `music_f_epb.pbo` | 0.0 | - | Music - Episode-B content. |
| `music_f_epb_music.pbo` | 31.1 | sounds | Music - music audio. |
| `music_f_epc.pbo` | 0.0 | - | Music - Episode-C content. |
| `music_f_epc_music.pbo` | 35.4 | sounds | Music - music audio. |
| `music_f_music.pbo` | 46.2 | sounds | Music - music audio. |
| `plants_f.pbo` | 266.0 | models, textures, materials | Vegetation plants. |
| `props_f_decade.pbo` | 130.1 | models, textures, materials, scripts | Static props - Decade (free) content. |
| `props_f_exp_a.pbo` | 6.6 | models, textures, materials, scripts | Apex DLC: Static props - Expansion-A content. |
| `roads_f.pbo` | 263.7 | models, textures, materials | Road and rail pieces. |
| `rocks_f.pbo` | 271.2 | models, textures, materials | Rocks. |
| `signs_f.pbo` | 83.7 | models, textures, materials | Signs. |
| `soft_f.pbo` | 160.4 | models, textures, materials, animation, scripts | Soft-skinned vehicles (cars, trucks). |
| `soft_f_beta.pbo` | 173.3 | models, textures, materials, animation, scripts | Soft-skinned vehicles (cars, trucks) - beta/legacy content. |
| `soft_f_bootcamp.pbo` | 70.5 | models, textures, materials, scripts | Soft-skinned vehicles (cars, trucks) - Bootcamp campaign content. |
| `soft_f_epc.pbo` | 92.7 | models, textures, materials | Soft-skinned vehicles (cars, trucks) - Episode-C content. |
| `soft_f_gamma.pbo` | 218.4 | models, textures, materials, animation, scripts | Soft-skinned vehicles (cars, trucks) - Gamma/free content. |
| `sounds_f.pbo` **[ROOT]** | 722.2 | sounds | Sound engine config and audio assets. |
| `sounds_f_arsenal.pbo` **[ROOT]** | 354.8 | sounds | Sound engine config and audio assets. |
| `sounds_f_bootcamp.pbo` **[ROOT]** | 45.9 | sounds | Sound engine config and audio assets - Bootcamp campaign content. |
| `sounds_f_characters.pbo` **[ROOT]** | 321.1 | sounds | Sound engine config and audio assets. |
| `sounds_f_decade.pbo` **[ROOT]** | 24.8 | sounds | Sound engine config and audio assets - Decade (free) content. |
| `sounds_f_environment.pbo` **[ROOT]** | 220.2 | sounds | Sound engine config and audio assets. |
| `sounds_f_epb.pbo` **[ROOT]** | 37.9 | sounds | Sound engine config and audio assets - Episode-B content. |
| `sounds_f_epc.pbo` **[ROOT]** | 29.2 | sounds | Sound engine config and audio assets - Episode-C content. |
| `sounds_f_exp_a.pbo` **[ROOT]** | 0.0 | - | Apex DLC: Sound engine config and audio assets - Expansion-A content. |
| `sounds_f_mod.pbo` **[ROOT]** | 2.6 | sounds | Sound engine config and audio assets - mod-support content. |
| `sounds_f_sfx.pbo` **[ROOT]** | 33.4 | sounds | Sound engine config and audio assets. |
| `sounds_f_vehicles.pbo` **[ROOT]** | 446.3 | sounds | Sound engine config and audio assets. |
| `static_f.pbo` **[ROOT]** | 22.0 | models, textures, materials, animation | Static weapons. |
| `static_f_beta.pbo` **[ROOT]** | 0.0 | - | Static weapons - beta/legacy content. |
| `static_f_gamma.pbo` **[ROOT]** | 31.0 | models, textures, materials, animation | Static weapons - Gamma/free content. |
| `structures_f.pbo` | 918.7 | models, textures, materials, scripts | Buildings and structures. |
| `structures_f_bootcamp.pbo` | 26.4 | models, textures, materials | Buildings and structures - Bootcamp campaign content. |
| `structures_f_data.pbo` | 569.7 | models, textures, materials | Buildings and structures - data assets. |
| `structures_f_epa.pbo` | 31.4 | models, textures, materials, scripts | Buildings and structures - Episode-A content. |
| `structures_f_epb.pbo` | 114.2 | models, textures, materials, scripts | Buildings and structures - Episode-B content. |
| `structures_f_epc.pbo` | 231.0 | models, textures, materials, scripts | Buildings and structures - Episode-C content. |
| `structures_f_exp_a.pbo` | 0.1 | models, textures | Apex DLC: Buildings and structures - Expansion-A content. |
| `structures_f_households.pbo` | 494.6 | models, textures, materials | Buildings and structures. |
| `structures_f_ind.pbo` | 568.9 | models, textures, materials, animation, scripts | Buildings and structures. |
| `structures_f_mil.pbo` | 355.4 | models, textures, materials | Buildings and structures. |
| `structures_f_wrecks.pbo` | 410.2 | models, textures, materials, scripts | Buildings and structures. |
| `ui_f.pbo` **[ROOT]** | 82.9 | config, models, textures, materials, scripts | User interface configs (Rsc*, markers, map). |
| `ui_f_bootcamp.pbo` **[ROOT]** | 0.0 | - | User interface configs (Rsc*, markers, map) - Bootcamp campaign content. |
| `ui_f_data.pbo` **[ROOT]** | 104.1 | textures, materials, sounds | User interface configs (Rsc*, markers, map) - data assets. |
| `ui_f_decade.pbo` **[ROOT]** | 0.0 | config, scripts | User interface configs (Rsc*, markers, map) - Decade (free) content. |
| `ui_f_exp_a.pbo` **[ROOT]** | 0.0 | config | Apex DLC: User interface configs (Rsc*, markers, map) - Expansion-A content. |
| `uifonts_f.pbo` | 0.0 | - | UI font family config (CfgFontFamilies). |
| `uifonts_f_data.pbo` | 241.4 | textures, fonts | UI fonts - data assets. |
| `weapons_f.pbo` **[ROOT]** | 479.5 | models, textures, materials, animation, scripts | Weapons, ammunition and magazines. |
| `weapons_f_beta.pbo` **[ROOT]** | 96.6 | models, textures, materials, animation | Weapons, ammunition and magazines - beta/legacy content. |
| `weapons_f_bootcamp.pbo` **[ROOT]** | 10.8 | models, textures, materials | Weapons, ammunition and magazines - Bootcamp campaign content. |
| `weapons_f_decade.pbo` **[ROOT]** | 0.0 | - | Weapons, ammunition and magazines - Decade (free) content. |
| `weapons_f_epa.pbo` **[ROOT]** | 40.2 | models, textures, materials, animation | Weapons, ammunition and magazines - Episode-A content. |
| `weapons_f_epb.pbo` **[ROOT]** | 20.0 | models, textures, materials | Weapons, ammunition and magazines - Episode-B content. |
| `weapons_f_epc.pbo` **[ROOT]** | 1.3 | models | Weapons, ammunition and magazines - Episode-C content. |
| `weapons_f_gamma.pbo` **[ROOT]** | 5.5 | models, textures, materials, animation | Weapons, ammunition and magazines - Gamma/free content. |
| `weapons_f_mod.pbo` **[ROOT]** | 26.9 | models, textures, materials, animation | Weapons, ammunition and magazines - mod-support content. |

### 3.xx Third-party and developer roots

| PBO | MiB | Carries | Purpose |
|---|---:|---|---|
| `@a3m/addons/a3m_smooth.pbo` | 0.0 | scripts | a3m_smooth. |
| `@a3pm/addons/a3pm_client.pbo` | 0.0 | config, scripts | a3pm_client. |
| `@a3pm/addons/a3pm_main.pbo` | 0.0 | config, scripts | a3pm_main. |
| `@a3pm/addons/a3pm_monitor.pbo` | 0.0 | config, scripts | a3pm_monitor. |
| `@a3pm/addons/a3pm_rules.pbo` | 0.0 | config, scripts | a3pm_rules. |
| `@a3pm/addons/a3pm_ui.pbo` | 0.0 | config, scripts | a3pm_ui. |
| `@ASCZ Post-process Effects/Addons/addon.pbo` | 0.0 | - | addon. |
| `AoW/Addons/anims_f_aow.pbo` | 0.7 | animation | Art of War DLC: Animation state, skeleton and motion data. |
| `AoW/Addons/characters_f_aow.pbo` | 86.6 | models, textures, materials | Art of War DLC: Soldiers, heads, uniforms and characters. |
| `AoW/Addons/data_f_aow.pbo` | 18.9 | textures | Art of War DLC: Shared models, textures and global data. |
| `AoW/Addons/dubbing_f_aow.pbo` | 6.8 | animation, sounds | Art of War DLC: Voice dubbing audio. |
| `AoW/Addons/editorpreviews_f_aow.pbo` | 2.5 | textures | Art of War DLC: Eden editor preview thumbnails. |
| `AoW/Addons/functions_f_aow.pbo` | 0.0 | scripts | Art of War DLC: SQF function library (CfgFunctions). |
| `AoW/Addons/language_f_aow.pbo` | 0.4 | data | Art of War DLC: Localisation stringtables. |
| `AoW/Addons/languagemissions_f_aow.pbo` | 2.3 | data | Art of War DLC: Mission localisation stringtables. |
| `AoW/Addons/missions_f_aow.pbo` | 11.2 | config, scripts | Art of War DLC: Mission and campaign assets. |
| `AoW/Addons/missions_f_aow_data.pbo` | 165.2 | models, textures, materials | Art of War DLC: Mission and campaign assets - data assets. |
| `AoW/Addons/missions_f_aow_video.pbo` | 17.8 | - | Art of War DLC: Mission and campaign assets - intro/outro video. |
| `AoW/Addons/props_f_aow.pbo` | 141.7 | models, textures, materials | Art of War DLC: Static props. |
| `AoW/Addons/sounds_f_aow.pbo` | 16.8 | sounds | Art of War DLC: Sound engine config and audio assets. |
| `AoW/Addons/structures_f_aow.pbo` | 52.6 | models, textures, materials | Art of War DLC: Buildings and structures. |
| `AoW/Addons/supplies_f_aow.pbo` | 9.2 | models, textures, materials | Art of War DLC: Ammunition, backpacks and items. |
| `AoW/Addons/ui_f_aow.pbo` | 36.9 | textures | Art of War DLC: User interface configs (Rsc*, markers, map). |
| `Argo/Addons/armor_f_argo.pbo` | 0.0 | - | Argo free platform (Malden): Armoured tracked vehicles. |
| `Argo/Addons/characters_f_patrol.pbo` | 0.0 | - | Argo patrol content: Soldiers, heads, uniforms and characters. |
| `Argo/Addons/data_f_argo.pbo` | 18.6 | models, textures | Argo free platform (Malden): Shared models, textures and global data. |
| `Argo/Addons/data_f_patrol.pbo` | 0.0 | - | Argo patrol content: Shared models, textures and global data. |
| `Argo/Addons/editorpreviews_f_argo.pbo` | 7.1 | textures | Argo free platform (Malden): Eden editor preview thumbnails. |
| `Argo/Addons/functions_f_patrol.pbo` | 0.1 | scripts | Argo patrol content: SQF function library (CfgFunctions). |
| `Argo/Addons/language_f_argo.pbo` | 0.6 | data | Argo free platform (Malden): Localisation stringtables. |
| `Argo/Addons/language_f_patrol.pbo` | 0.0 | data | Argo patrol content: Localisation stringtables. |
| `Argo/Addons/languagemissions_f_patrol.pbo` | 0.3 | data | Argo patrol content: Mission localisation stringtables. |
| `Argo/Addons/map_malden.pbo` | 52.9 | terrain | Malden terrain: world binary (.wrp) and CfgWorlds config. |
| `Argo/Addons/map_malden_data.pbo` | 9.9 | config, textures | Malden terrain: terrain models, textures and materials. |
| `Argo/Addons/map_malden_data_layers.pbo` | 70.4 | textures, materials | Malden terrain: terrain layer materials and masks. |
| `Argo/Addons/map_malden_scenes_f.pbo` | 8.2 | scripts | Malden terrain: scripted scene scripts. |
| `Argo/Addons/missions_f_patrol.pbo` | 3.7 | config, textures, scripts | Argo patrol content: Mission and campaign assets. |
| `Argo/Addons/modules_f_patrol.pbo` | 0.0 | - | Argo patrol content: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Argo/Addons/music_f_argo.pbo` | 4.1 | sounds | Argo free platform (Malden): Music. |
| `Argo/Addons/props_f_argo.pbo` | 64.5 | models, textures | Argo free platform (Malden): Static props. |
| `Argo/Addons/rocks_f_argo.pbo` | 28.1 | models, textures, materials | Argo free platform (Malden): Rocks. |
| `Argo/Addons/sounds_f_patrol.pbo` | 10.2 | sounds | Argo patrol content: Sound engine config and audio assets. |
| `Argo/Addons/structures_f_argo.pbo` | 1078.8 | models, textures, materials | Argo free platform (Malden): Buildings and structures. |
| `Argo/Addons/ui_f_patrol.pbo` | 0.0 | - | Argo patrol content: User interface configs (Rsc*, markers, map). |
| `Argo/Addons/vegetation_f_argo.pbo` | 56.1 | models, textures, materials | Argo free platform (Malden): Vegetation. |
| `Argo/Addons/weapons_f_patrol.pbo` | 0.0 | - | Argo patrol content: Weapons, ammunition and magazines. |
| `Contact/Addons/air_f_contact.pbo` | 23.2 | models, textures, materials, scripts | Contact DLC platform: Fixed-wing aircraft. |
| `Contact/Addons/anims_f_contact.pbo` | 0.0 | animation | Contact DLC platform: Animation state, skeleton and motion data. |
| `Contact/Addons/armor_f_contact.pbo` | 0.0 | - | Contact DLC platform: Armoured tracked vehicles. |
| `Contact/Addons/cargoposes_f_contact.pbo` | 1.3 | animation | Contact DLC platform: Cargo and seat pose animation. |
| `Contact/Addons/characters_f_contact.pbo` | 0.1 | - | Contact DLC platform: Soldiers, heads, uniforms and characters. |
| `Contact/Addons/data_f_contact.pbo` | 24.8 | models, textures, materials | Contact DLC platform: Shared models, textures and global data. |
| `Contact/Addons/dubbing_f_contact.pbo` | 51.2 | animation, sounds | Contact DLC platform: Voice dubbing audio. |
| `Contact/Addons/editorpreviews_f_contact.pbo` | 1.6 | textures | Contact DLC platform: Eden editor preview thumbnails. |
| `Contact/Addons/functions_f_contact.pbo` | 1.3 | config, scripts | Contact DLC platform: SQF function library (CfgFunctions). |
| `Contact/Addons/language_f_contact.pbo` | 1.3 | data | Contact DLC platform: Localisation stringtables. |
| `Contact/Addons/languagemissions_f_contact.pbo` | 6.3 | data | Contact DLC platform: Mission localisation stringtables. |
| `Contact/Addons/missions_f_contact.pbo` | 129.4 | config, models, textures, scripts | Contact DLC platform: Mission and campaign assets. |
| `Contact/Addons/modules_f_contact.pbo` | 0.1 | scripts | Contact DLC platform: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Contact/Addons/music_f_contact.pbo` | 0.0 | - | Contact DLC platform: Music. |
| `Contact/Addons/props_f_contact.pbo` | 133.2 | models, textures, materials, scripts | Contact DLC platform: Static props. |
| `Contact/Addons/soft_f_contact.pbo` | 2.2 | textures, materials | Contact DLC platform: Soft-skinned vehicles (cars, trucks). |
| `Contact/Addons/sounds_f_contact.pbo` | 825.0 | config, sounds | Contact DLC platform: Sound engine config and audio assets. |
| `Contact/Addons/static_f_contact.pbo` | 0.0 | - | Contact DLC platform: Static weapons. |
| `Contact/Addons/structures_f_contact.pbo` | 0.0 | - | Contact DLC platform: Buildings and structures. |
| `Contact/Addons/supplies_f_contact.pbo` | 0.0 | - | Contact DLC platform: Ammunition, backpacks and items. |
| `Contact/Addons/ui_f_contact.pbo` | 8.5 | config, models, textures, materials, scripts | Contact DLC platform: User interface configs (Rsc*, markers, map). |
| `Contact/Addons/weapons_f_contact.pbo` | 6.3 | models, textures, materials, scripts | Contact DLC platform: Weapons, ammunition and magazines. |
| `Curator/Addons/data_f_curator.pbo` | 14.9 | models, textures, materials, sounds | Zeus / Curator systems: Shared models, textures and global data. |
| `Curator/Addons/data_f_curator_music.pbo` | 2.1 | sounds | Zeus / Curator systems: Shared models, textures and global data - music audio. |
| `Curator/Addons/functions_f_curator.pbo` | 0.4 | config, scripts | Zeus / Curator systems: SQF function library (CfgFunctions). |
| `Curator/Addons/language_f_curator.pbo` | 1.4 | data | Zeus / Curator systems: Localisation stringtables. |
| `Curator/Addons/missions_f_curator.pbo` | 17.2 | config, textures, scripts | Zeus / Curator systems: Mission and campaign assets. |
| `Curator/Addons/modules_f_curator.pbo` | 1.3 | models, textures, materials, scripts | Zeus / Curator systems: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Curator/Addons/ui_f_curator.pbo` | 16.4 | config, models, textures, materials, scripts, sounds | Zeus / Curator systems: User interface configs (Rsc*, markers, map). |
| `Enoch/Addons/air_f_enoch.pbo` | 5.4 | textures | Contact DLC (Livonia): Fixed-wing aircraft. |
| `Enoch/Addons/anims_f_enoch.pbo` | 61.6 | animation, data | Contact DLC (Livonia): Animation state, skeleton and motion data. |
| `Enoch/Addons/armor_f_enoch.pbo` | 4.0 | textures | Contact DLC (Livonia): Armoured tracked vehicles. |
| `Enoch/Addons/cargoposes_f_enoch.pbo` | 0.0 | animation | Contact DLC (Livonia): Cargo and seat pose animation. |
| `Enoch/Addons/characters_f_enoch.pbo` | 260.6 | models, textures, materials | Contact DLC (Livonia): Soldiers, heads, uniforms and characters. |
| `Enoch/Addons/data_f_enoch.pbo` | 24.4 | models, textures, materials | Contact DLC (Livonia): Shared models, textures and global data. |
| `Enoch/Addons/dubbing_radio_f_enoch.pbo` | 1.6 | - | Contact DLC (Livonia): Radio-protocol voice audio. |
| `Enoch/Addons/dubbing_radio_f_enoch_data.pbo` | 266.0 | animation, sounds | Contact DLC (Livonia): Radio-protocol voice audio - data assets. |
| `Enoch/Addons/editorpreviews_f_enoch.pbo` | 35.5 | textures | Contact DLC (Livonia): Eden editor preview thumbnails. |
| `Enoch/Addons/functions_f_enoch.pbo` | 0.0 | config, scripts | Contact DLC (Livonia): SQF function library (CfgFunctions). |
| `Enoch/Addons/language_f_enoch.pbo` | 2.9 | data | Contact DLC (Livonia): Localisation stringtables. |
| `Enoch/Addons/languagemissions_f_enoch.pbo` | 0.0 | data | Contact DLC (Livonia): Mission localisation stringtables. |
| `Enoch/Addons/map_enoch.pbo` | 198.0 | terrain | Livonia terrain: world binary (.wrp) and CfgWorlds config. |
| `Enoch/Addons/map_enoch_data.pbo` | 127.1 | config, models, textures, materials | Livonia terrain: terrain models, textures and materials. |
| `Enoch/Addons/map_enoch_data_layers.pbo` | 216.5 | textures, materials | Livonia terrain: terrain layer materials and masks. |
| `Enoch/Addons/map_enoch_scenes_f.pbo` | 0.0 | scripts | Livonia terrain: scripted scene scripts. |
| `Enoch/Addons/missions_f_enoch.pbo` | 1.9 | textures, scripts | Contact DLC (Livonia): Mission and campaign assets. |
| `Enoch/Addons/music_f_enoch.pbo` | 0.0 | - | Contact DLC (Livonia): Music. |
| `Enoch/Addons/music_f_enoch_music.pbo` | 472.3 | sounds | Contact DLC (Livonia): Music - music audio. |
| `Enoch/Addons/props_f_enoch.pbo` | 231.6 | models, textures, materials, scripts | Contact DLC (Livonia): Static props. |
| `Enoch/Addons/rocks_f_enoch.pbo` | 183.5 | models, textures, materials | Contact DLC (Livonia): Rocks. |
| `Enoch/Addons/soft_f_enoch.pbo` | 153.9 | models, textures, materials, scripts | Contact DLC (Livonia): Soft-skinned vehicles (cars, trucks). |
| `Enoch/Addons/sounds_f_enoch.pbo` | 714.5 | sounds | Contact DLC (Livonia): Sound engine config and audio assets. |
| `Enoch/Addons/static_f_enoch.pbo` | 1.3 | textures | Contact DLC (Livonia): Static weapons. |
| `Enoch/Addons/structures_f_enoch.pbo` | 477.8 | models, textures, materials | Contact DLC (Livonia): Buildings and structures. |
| `Enoch/Addons/structures_f_enoch_civilian.pbo` | 572.7 | models, textures, materials | Contact DLC (Livonia): Buildings and structures. |
| `Enoch/Addons/structures_f_enoch_commercial.pbo` | 28.5 | models, textures, materials | Contact DLC (Livonia): Buildings and structures. |
| `Enoch/Addons/structures_f_enoch_cultural.pbo` | 258.1 | models, textures, materials | Contact DLC (Livonia): Buildings and structures. |
| `Enoch/Addons/structures_f_enoch_data.pbo` | 1224.6 | textures, materials | Contact DLC (Livonia): Buildings and structures - data assets. |
| `Enoch/Addons/structures_f_enoch_furniture.pbo` | 115.7 | models, textures, materials | Contact DLC (Livonia): Buildings and structures. |
| `Enoch/Addons/structures_f_enoch_industrial.pbo` | 711.4 | models, textures, materials | Contact DLC (Livonia): Buildings and structures. |
| `Enoch/Addons/structures_f_enoch_infrastructure.pbo` | 212.7 | models, textures, materials | Contact DLC (Livonia): Buildings and structures. |
| `Enoch/Addons/structures_f_enoch_military.pbo` | 704.9 | models, textures, materials | Contact DLC (Livonia): Buildings and structures. |
| `Enoch/Addons/supplies_f_enoch.pbo` | 74.1 | models, textures, materials | Contact DLC (Livonia): Ammunition, backpacks and items. |
| `Enoch/Addons/ui_f_enoch.pbo` | 36.2 | config, models, textures, materials, scripts, fonts | Contact DLC (Livonia): User interface configs (Rsc*, markers, map). |
| `Enoch/Addons/vegetation_f_enoch.pbo` | 373.2 | models, textures, materials | Contact DLC (Livonia): Vegetation. |
| `Enoch/Addons/weapons_f_enoch.pbo` | 164.6 | models, textures, materials, animation, scripts | Contact DLC (Livonia): Weapons, ammunition and magazines. |
| `Expansion/Addons/air_f_exp.pbo` | 217.7 | models, textures, materials | Apex DLC: Fixed-wing aircraft. |
| `Expansion/Addons/anims_f_exp.pbo` | 82.1 | models, animation, data | Apex DLC: Animation state, skeleton and motion data. |
| `Expansion/Addons/armor_f_exp.pbo` | 37.0 | textures | Apex DLC: Armoured tracked vehicles. |
| `Expansion/Addons/boat_f_exp.pbo` | 39.2 | models, textures, materials, scripts | Apex DLC: Boats and ships. |
| `Expansion/Addons/cargoposes_f_exp.pbo` | 15.5 | animation | Apex DLC: Cargo and seat pose animation. |
| `Expansion/Addons/characters_f_exp.pbo` | 240.9 | models, textures, materials | Apex DLC: Soldiers, heads, uniforms and characters. |
| `Expansion/Addons/characters_f_oldman.pbo` | 57.3 | textures, materials | Apex DLC Old Man scenario: Soldiers, heads, uniforms and characters. |
| `Expansion/Addons/data_f_exp.pbo` | 35.3 | textures | Apex DLC: Shared models, textures and global data. |
| `Expansion/Addons/data_f_oldman.pbo` | 0.1 | textures | Apex DLC Old Man scenario: Shared models, textures and global data. |
| `Expansion/Addons/dubbing_f_exp.pbo` | 29.4 | animation, sounds | Apex DLC: Voice dubbing audio. |
| `Expansion/Addons/dubbing_f_oldman.pbo` | 163.9 | animation, sounds | Apex DLC Old Man scenario: Voice dubbing audio. |
| `Expansion/Addons/dubbing_radio_f_exp.pbo` | 13.5 | scripts | Apex DLC: Radio-protocol voice audio. |
| `Expansion/Addons/dubbing_radio_f_exp_data_chi.pbo` | 107.4 | animation, sounds | Apex DLC: Radio-protocol voice audio - data assets. |
| `Expansion/Addons/dubbing_radio_f_exp_data_engfre.pbo` | 81.0 | animation, sounds | Apex DLC: Radio-protocol voice audio - data assets. |
| `Expansion/Addons/dubbing_radio_f_exp_data_fre.pbo` | 126.7 | animation, sounds | Apex DLC: Radio-protocol voice audio - data assets. |
| `Expansion/Addons/editorpreviews_f_exp.pbo` | 18.4 | textures | Apex DLC: Eden editor preview thumbnails. |
| `Expansion/Addons/editorpreviews_f_oldman.pbo` | 2.0 | textures | Apex DLC Old Man scenario: Eden editor preview thumbnails. |
| `Expansion/Addons/functions_f_exp.pbo` | 0.0 | scripts | Apex DLC: SQF function library (CfgFunctions). |
| `Expansion/Addons/functions_f_oldman.pbo` | 0.0 | - | Apex DLC Old Man scenario: SQF function library (CfgFunctions). |
| `Expansion/Addons/language_f_exp.pbo` | 2.6 | data | Apex DLC: Localisation stringtables. |
| `Expansion/Addons/language_f_oldman.pbo` | 0.4 | data | Apex DLC Old Man scenario: Localisation stringtables. |
| `Expansion/Addons/languagemissions_f_exp.pbo` | 3.3 | data | Apex DLC: Mission localisation stringtables. |
| `Expansion/Addons/languagemissions_f_oldman.pbo` | 5.4 | data | Apex DLC Old Man scenario: Mission localisation stringtables. |
| `Expansion/Addons/map_data_exp.pbo` | 75.6 | textures, materials | Shared terrain data (all maps): world binary (.wrp) and CfgWorlds config. |
| `Expansion/Addons/map_tanoa_scenes_f.pbo` | 21.8 | scripts | Tanoa terrain: scripted scene scripts. |
| `Expansion/Addons/map_tanoabuka.pbo` | 162.9 | terrain | Tanoa terrain: world binary (.wrp) and CfgWorlds config. |
| `Expansion/Addons/map_tanoabuka_data.pbo` | 10.6 | config, models, textures, materials, scripts | Tanoa terrain: terrain models, textures and materials. |
| `Expansion/Addons/map_tanoabuka_data_layers.pbo` | 9.6 | materials | Tanoa terrain: terrain layer materials and masks. |
| `Expansion/Addons/map_tanoabuka_data_layers_00_00.pbo` | 465.3 | textures | Tanoa terrain: terrain layer tile textures (satellite and mask). |
| `Expansion/Addons/missions_f_exp.pbo` | 6.3 | config, scripts | Apex DLC: Mission and campaign assets. |
| `Expansion/Addons/missions_f_exp_data.pbo` | 39.9 | textures, sounds | Apex DLC: Mission and campaign assets - data assets. |
| `Expansion/Addons/missions_f_exp_video.pbo` | 803.1 | - | Apex DLC: Mission and campaign assets - intro/outro video. |
| `Expansion/Addons/missions_f_oldman.pbo` | 183.4 | config, models, textures, scripts, sounds | Apex DLC Old Man scenario: Mission and campaign assets. |
| `Expansion/Addons/modules_f_exp.pbo` | 0.0 | - | Apex DLC: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Expansion/Addons/modules_f_oldman.pbo` | 0.0 | - | Apex DLC Old Man scenario: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Expansion/Addons/music_f_exp.pbo` | 0.0 | - | Apex DLC: Music. |
| `Expansion/Addons/music_f_exp_music.pbo` | 52.9 | sounds | Apex DLC: Music - music audio. |
| `Expansion/Addons/music_f_oldman.pbo` | 0.0 | - | Apex DLC Old Man scenario: Music. |
| `Expansion/Addons/music_f_oldman_music.pbo` | 182.7 | sounds | Apex DLC Old Man scenario: Music - music audio. |
| `Expansion/Addons/props_f_exp.pbo` | 401.8 | models, textures, materials | Apex DLC: Static props. |
| `Expansion/Addons/props_f_oldman.pbo` | 3.1 | models, textures, materials | Apex DLC Old Man scenario: Static props. |
| `Expansion/Addons/rocks_f_exp.pbo` | 242.6 | models, textures, materials | Apex DLC: Rocks. |
| `Expansion/Addons/soft_f_exp.pbo` | 244.4 | models, textures, materials | Apex DLC: Soft-skinned vehicles (cars, trucks). |
| `Expansion/Addons/soft_f_oldman.pbo` | 5.8 | models | Apex DLC Old Man scenario: Soft-skinned vehicles (cars, trucks). |
| `Expansion/Addons/sounds_f_exp.pbo` | 532.9 | sounds | Apex DLC: Sound engine config and audio assets. |
| `Expansion/Addons/sounds_f_oldman.pbo` | 19.5 | sounds | Apex DLC Old Man scenario: Sound engine config and audio assets. |
| `Expansion/Addons/static_f_exp.pbo` | 0.0 | - | Apex DLC: Static weapons. |
| `Expansion/Addons/static_f_oldman.pbo` | 0.0 | - | Apex DLC Old Man scenario: Static weapons. |
| `Expansion/Addons/structures_f_exp.pbo` | 547.3 | models, textures, materials, scripts | Apex DLC: Buildings and structures. |
| `Expansion/Addons/structures_f_exp_civilian.pbo` | 345.3 | models, textures, materials | Apex DLC: Buildings and structures. |
| `Expansion/Addons/structures_f_exp_commercial.pbo` | 405.3 | models, textures, materials | Apex DLC: Buildings and structures. |
| `Expansion/Addons/structures_f_exp_cultural.pbo` | 239.2 | models, textures, materials | Apex DLC: Buildings and structures. |
| `Expansion/Addons/structures_f_exp_data.pbo` | 1243.2 | textures, materials | Apex DLC: Buildings and structures - data assets. |
| `Expansion/Addons/structures_f_exp_industrial.pbo` | 641.8 | models, textures, materials | Apex DLC: Buildings and structures. |
| `Expansion/Addons/structures_f_exp_infrastructure.pbo` | 381.1 | models, textures, materials, scripts | Apex DLC: Buildings and structures. |
| `Expansion/Addons/structures_f_oldman.pbo` | 59.3 | models, textures, materials | Apex DLC Old Man scenario: Buildings and structures. |
| `Expansion/Addons/supplies_f_exp.pbo` | 46.0 | models, textures, materials | Apex DLC: Ammunition, backpacks and items. |
| `Expansion/Addons/supplies_f_oldman.pbo` | 0.0 | - | Apex DLC Old Man scenario: Ammunition, backpacks and items. |
| `Expansion/Addons/ui_f_exp.pbo` | 0.0 | - | Apex DLC: User interface configs (Rsc*, markers, map). |
| `Expansion/Addons/ui_f_oldman.pbo` | 44.6 | config, textures, scripts | Apex DLC Old Man scenario: User interface configs (Rsc*, markers, map). |
| `Expansion/Addons/vegetation_f_exp.pbo` | 604.0 | models, textures, materials | Apex DLC: Vegetation. |
| `Expansion/Addons/weapons_f_exp.pbo` | 344.3 | models, textures, materials, animation | Apex DLC: Weapons, ammunition and magazines. |
| `Heli/Addons/air_f_heli.pbo` | 166.6 | models, textures, materials, scripts, data | Helicopters DLC: Fixed-wing aircraft. |
| `Heli/Addons/anims_f_heli.pbo` | 0.0 | - | Helicopters DLC: Animation state, skeleton and motion data. |
| `Heli/Addons/boat_f_heli.pbo` | 0.0 | - | Helicopters DLC: Boats and ships. |
| `Heli/Addons/cargoposes_f_heli.pbo` | 31.9 | animation | Helicopters DLC: Cargo and seat pose animation. |
| `Heli/Addons/data_f_heli.pbo` | 13.8 | textures | Helicopters DLC: Shared models, textures and global data. |
| `Heli/Addons/dubbing_f_heli.pbo` | 11.4 | animation, sounds | Helicopters DLC: Voice dubbing audio. |
| `Heli/Addons/functions_f_heli.pbo` | 0.5 | config, scripts | Helicopters DLC: SQF function library (CfgFunctions). |
| `Heli/Addons/language_f_heli.pbo` | 1.1 | data | Helicopters DLC: Localisation stringtables. |
| `Heli/Addons/languagemissions_f_heli.pbo` | 1.4 | data | Helicopters DLC: Mission localisation stringtables. |
| `Heli/Addons/missions_f_heli.pbo` | 2.2 | config, scripts | Helicopters DLC: Mission and campaign assets. |
| `Heli/Addons/missions_f_heli_data.pbo` | 5.3 | textures | Helicopters DLC: Mission and campaign assets - data assets. |
| `Heli/Addons/missions_f_heli_video.pbo` | 8.8 | - | Helicopters DLC: Mission and campaign assets - intro/outro video. |
| `Heli/Addons/modules_f_heli.pbo` | 0.5 | scripts | Helicopters DLC: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Heli/Addons/music_f_heli.pbo` | 0.0 | - | Helicopters DLC: Music. |
| `Heli/Addons/music_f_heli_music.pbo` | 2.9 | sounds | Helicopters DLC: Music - music audio. |
| `Heli/Addons/soft_f_heli.pbo` | 0.0 | - | Helicopters DLC: Soft-skinned vehicles (cars, trucks). |
| `Heli/Addons/sounds_f_heli.pbo` | 20.3 | sounds | Helicopters DLC: Sound engine config and audio assets. |
| `Heli/Addons/structures_f_heli.pbo` | 114.2 | models, textures, materials | Helicopters DLC: Buildings and structures. |
| `Heli/Addons/supplies_f_heli.pbo` | 37.4 | models, textures, materials | Helicopters DLC: Ammunition, backpacks and items. |
| `Heli/Addons/ui_f_heli.pbo` | 0.0 | - | Helicopters DLC: User interface configs (Rsc*, markers, map). |
| `Jets/Addons/air_f_jets.pbo` | 527.6 | models, textures, materials | Jets DLC: Fixed-wing aircraft. |
| `Jets/Addons/anims_f_jets.pbo` | 13.3 | animation | Jets DLC: Animation state, skeleton and motion data. |
| `Jets/Addons/boat_f_destroyer.pbo` | 295.9 | models, textures, materials | Jets DLC destroyer: Boats and ships. |
| `Jets/Addons/boat_f_jets.pbo` | 215.1 | models, textures, materials | Jets DLC: Boats and ships. |
| `Jets/Addons/cargoposes_f_jets.pbo` | 1.9 | animation | Jets DLC: Cargo and seat pose animation. |
| `Jets/Addons/characters_f_jets.pbo` | 13.9 | models, textures, materials | Jets DLC: Soldiers, heads, uniforms and characters. |
| `Jets/Addons/data_f_destroyer.pbo` | 0.3 | textures | Jets DLC destroyer: Shared models, textures and global data. |
| `Jets/Addons/data_f_jets.pbo` | 17.8 | models, textures | Jets DLC: Shared models, textures and global data. |
| `Jets/Addons/data_f_sams.pbo` | 0.1 | textures | Jets DLC SAM systems: Shared models, textures and global data. |
| `Jets/Addons/dubbing_f_jets.pbo` | 5.2 | sounds | Jets DLC: Voice dubbing audio. |
| `Jets/Addons/editorpreviews_f_destroyer.pbo` | 0.5 | textures | Jets DLC destroyer: Eden editor preview thumbnails. |
| `Jets/Addons/editorpreviews_f_jets.pbo` | 0.9 | textures | Jets DLC: Eden editor preview thumbnails. |
| `Jets/Addons/editorpreviews_f_sams.pbo` | 0.2 | textures | Jets DLC SAM systems: Eden editor preview thumbnails. |
| `Jets/Addons/functions_f_destroyer.pbo` | 0.0 | config, scripts | Jets DLC destroyer: SQF function library (CfgFunctions). |
| `Jets/Addons/functions_f_jets.pbo` | 0.1 | config, scripts | Jets DLC: SQF function library (CfgFunctions). |
| `Jets/Addons/language_f_destroyer.pbo` | 0.1 | data | Jets DLC destroyer: Localisation stringtables. |
| `Jets/Addons/language_f_jets.pbo` | 0.6 | data | Jets DLC: Localisation stringtables. |
| `Jets/Addons/language_f_sams.pbo` | 0.1 | data | Jets DLC SAM systems: Localisation stringtables. |
| `Jets/Addons/languagemissions_f_jets.pbo` | 0.3 | data | Jets DLC: Mission localisation stringtables. |
| `Jets/Addons/missions_f_jets.pbo` | 4.8 | config, textures, scripts | Jets DLC: Mission and campaign assets. |
| `Jets/Addons/modules_f_jets.pbo` | 0.0 | - | Jets DLC: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Jets/Addons/music_f_jets.pbo` | 8.5 | sounds | Jets DLC: Music. |
| `Jets/Addons/props_f_destroyer.pbo` | 0.0 | models | Jets DLC destroyer: Static props. |
| `Jets/Addons/props_f_jets.pbo` | 32.1 | models, textures, materials | Jets DLC: Static props. |
| `Jets/Addons/sounds_f_jets.pbo` | 107.4 | sounds | Jets DLC: Sound engine config and audio assets. |
| `Jets/Addons/static_f_destroyer.pbo` | 65.1 | models, textures, materials | Jets DLC destroyer: Static weapons. |
| `Jets/Addons/static_f_jets.pbo` | 103.9 | models, textures, materials | Jets DLC: Static weapons. |
| `Jets/Addons/static_f_sams.pbo` | 332.0 | models, textures, materials | Jets DLC SAM systems: Static weapons. |
| `Jets/Addons/ui_f_jets.pbo` | 1.0 | textures | Jets DLC: User interface configs (Rsc*, markers, map). |
| `Jets/Addons/weapons_f_destroyer.pbo` | 6.5 | models, textures, materials | Jets DLC destroyer: Weapons, ammunition and magazines. |
| `Jets/Addons/weapons_f_jets.pbo` | 23.7 | models, textures, materials | Jets DLC: Weapons, ammunition and magazines. |
| `Jets/Addons/weapons_f_sams.pbo` | 49.1 | models, textures, materials | Jets DLC SAM systems: Weapons, ammunition and magazines. |
| `Kart/Addons/anims_f_kart.pbo` | 3.6 | animation | Karts DLC: Animation state, skeleton and motion data. |
| `Kart/Addons/characters_f_kart.pbo` | 41.2 | models, textures, materials | Karts DLC: Soldiers, heads, uniforms and characters. |
| `Kart/Addons/data_f_kart.pbo` | 20.8 | textures | Karts DLC: Shared models, textures and global data. |
| `Kart/Addons/language_f_kart.pbo` | 0.4 | data | Karts DLC: Localisation stringtables. |
| `Kart/Addons/languagemissions_f_kart.pbo` | 0.1 | data | Karts DLC: Mission localisation stringtables. |
| `Kart/Addons/missions_f_kart.pbo` | 0.4 | config, scripts | Karts DLC: Mission and campaign assets. |
| `Kart/Addons/missions_f_kart_data.pbo` | 3.7 | textures | Karts DLC: Mission and campaign assets - data assets. |
| `Kart/Addons/modules_f_kart.pbo` | 0.3 | scripts | Karts DLC: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Kart/Addons/modules_f_kart_data.pbo` | 0.0 | textures | Karts DLC: Eden/Zeus editor modules (CfgVehicles, CfgFunctions) - data assets. |
| `Kart/Addons/soft_f_kart.pbo` | 30.2 | models, textures, materials, animation, scripts | Karts DLC: Soft-skinned vehicles (cars, trucks). |
| `Kart/Addons/sounds_f_kart.pbo` | 2.9 | sounds | Karts DLC: Sound engine config and audio assets. |
| `Kart/Addons/structures_f_kart.pbo` | 12.9 | models, textures, materials | Karts DLC: Buildings and structures. |
| `Kart/Addons/ui_f_kart.pbo` | 0.0 | config, scripts | Karts DLC: User interface configs (Rsc*, markers, map). |
| `Kart/Addons/weapons_f_kart.pbo` | 3.7 | models, textures, materials | Karts DLC: Weapons, ammunition and magazines. |
| `Mark/Addons/anims_f_mark.pbo` | 5.0 | animation | Marksmen DLC: Animation state, skeleton and motion data. |
| `Mark/Addons/characters_f_mark.pbo` | 65.0 | models, textures, materials | Marksmen DLC: Soldiers, heads, uniforms and characters. |
| `Mark/Addons/data_f_mark.pbo` | 24.7 | models, textures, materials | Marksmen DLC: Shared models, textures and global data. |
| `Mark/Addons/dubbing_f_mark.pbo` | 4.1 | animation, sounds | Marksmen DLC: Voice dubbing audio. |
| `Mark/Addons/dubbing_f_mp_mark.pbo` | 1.3 | animation, sounds | Marksmen DLC: Voice dubbing audio. |
| `Mark/Addons/functions_f_mark.pbo` | 0.7 | scripts | Marksmen DLC: SQF function library (CfgFunctions). |
| `Mark/Addons/functions_f_mp_mark.pbo` | 0.1 | config, scripts | Marksmen DLC: SQF function library (CfgFunctions). |
| `Mark/Addons/language_f_mark.pbo` | 0.9 | data | Marksmen DLC: Localisation stringtables. |
| `Mark/Addons/language_f_mp_mark.pbo` | 0.4 | data | Marksmen DLC: Localisation stringtables. |
| `Mark/Addons/languagemissions_f_mark.pbo` | 0.6 | data | Marksmen DLC: Mission localisation stringtables. |
| `Mark/Addons/languagemissions_f_mp_mark.pbo` | 0.1 | data | Marksmen DLC: Mission localisation stringtables. |
| `Mark/Addons/missions_f_mark.pbo` | 1.9 | config, scripts | Marksmen DLC: Mission and campaign assets. |
| `Mark/Addons/missions_f_mark_data.pbo` | 6.0 | textures | Marksmen DLC: Mission and campaign assets - data assets. |
| `Mark/Addons/missions_f_mark_video.pbo` | 18.0 | - | Marksmen DLC: Mission and campaign assets - intro/outro video. |
| `Mark/Addons/missions_f_mp_mark.pbo` | 0.5 | config, scripts | Marksmen DLC: Mission and campaign assets. |
| `Mark/Addons/missions_f_mp_mark_data.pbo` | 0.5 | textures | Marksmen DLC: Mission and campaign assets. |
| `Mark/Addons/modules_f_mark.pbo` | 0.0 | scripts | Marksmen DLC: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Mark/Addons/modules_f_mp_mark.pbo` | 0.8 | config, textures, scripts | Marksmen DLC: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Mark/Addons/music_f_mark.pbo` | 0.0 | - | Marksmen DLC: Music. |
| `Mark/Addons/music_f_mark_music.pbo` | 7.0 | sounds | Marksmen DLC: Music - music audio. |
| `Mark/Addons/sounds_f_mark.pbo` | 52.7 | sounds | Marksmen DLC: Sound engine config and audio assets. |
| `Mark/Addons/static_f_mark.pbo` | 10.2 | models, textures, materials, scripts | Marksmen DLC: Static weapons. |
| `Mark/Addons/structures_f_mark.pbo` | 47.0 | models, textures, materials, scripts | Marksmen DLC: Buildings and structures. |
| `Mark/Addons/supplies_f_mark.pbo` | 0.2 | models | Marksmen DLC: Ammunition, backpacks and items. |
| `Mark/Addons/ui_f_mark.pbo` | 0.0 | - | Marksmen DLC: User interface configs (Rsc*, markers, map). |
| `Mark/Addons/ui_f_mp_mark.pbo` | 0.0 | config | Marksmen DLC: User interface configs (Rsc*, markers, map). |
| `Mark/Addons/weapons_f_mark.pbo` | 300.2 | models, textures, materials, animation | Marksmen DLC: Weapons, ammunition and magazines. |
| `Orange/Addons/air_f_orange.pbo` | 41.0 | models, textures, materials | Laws of War DLC: Fixed-wing aircraft. |
| `Orange/Addons/cargoposes_f_orange.pbo` | 2.1 | animation | Laws of War DLC: Cargo and seat pose animation. |
| `Orange/Addons/characters_f_orange.pbo` | 146.5 | models, textures, materials | Laws of War DLC: Soldiers, heads, uniforms and characters. |
| `Orange/Addons/data_f_orange.pbo` | 32.8 | models, textures, materials | Laws of War DLC: Shared models, textures and global data. |
| `Orange/Addons/dubbing_f_orange.pbo` | 44.1 | animation, sounds | Laws of War DLC: Voice dubbing audio. |
| `Orange/Addons/editorpreviews_f_orange.pbo` | 3.5 | textures | Laws of War DLC: Eden editor preview thumbnails. |
| `Orange/Addons/functions_f_orange.pbo` | 0.0 | scripts | Laws of War DLC: SQF function library (CfgFunctions). |
| `Orange/Addons/language_f_orange.pbo` | 1.7 | data | Laws of War DLC: Localisation stringtables. |
| `Orange/Addons/languagemissions_f_orange.pbo` | 4.0 | data | Laws of War DLC: Mission localisation stringtables. |
| `Orange/Addons/missions_f_orange.pbo` | 106.5 | config, models, textures, materials, scripts | Laws of War DLC: Mission and campaign assets. |
| `Orange/Addons/modules_f_orange.pbo` | 0.0 | scripts | Laws of War DLC: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Orange/Addons/music_f_orange.pbo` | 14.2 | sounds | Laws of War DLC: Music. |
| `Orange/Addons/props_f_orange.pbo` | 230.8 | models, textures, materials, scripts | Laws of War DLC: Static props. |
| `Orange/Addons/soft_f_orange.pbo` | 375.8 | models, textures, materials | Laws of War DLC: Soft-skinned vehicles (cars, trucks). |
| `Orange/Addons/sounds_f_orange.pbo` | 316.3 | sounds | Laws of War DLC: Sound engine config and audio assets. |
| `Orange/Addons/structures_f_orange.pbo` | 116.5 | models, textures, materials | Laws of War DLC: Buildings and structures. |
| `Orange/Addons/supplies_f_orange.pbo` | 39.4 | models, textures, materials | Laws of War DLC: Ammunition, backpacks and items. |
| `Orange/Addons/ui_f_orange.pbo` | 39.5 | config, textures, scripts | Laws of War DLC: User interface configs (Rsc*, markers, map). |
| `Orange/Addons/weapons_f_orange.pbo` | 31.4 | models, textures, materials, scripts | Laws of War DLC: Weapons, ammunition and magazines. |
| `Tacops/Addons/characters_f_tacops.pbo` | 6.1 | textures, materials | Tac-Ops mission pack: Soldiers, heads, uniforms and characters. |
| `Tacops/Addons/data_f_tacops.pbo` | 36.7 | models, textures, materials, scripts | Tac-Ops mission pack: Shared models, textures and global data. |
| `Tacops/Addons/dubbing_f_tacops.pbo` | 37.5 | animation, sounds | Tac-Ops mission pack: Voice dubbing audio. |
| `Tacops/Addons/functions_f_tacops.pbo` | 0.1 | config, scripts | Tac-Ops mission pack: SQF function library (CfgFunctions). |
| `Tacops/Addons/language_f_tacops.pbo` | 0.3 | data | Tac-Ops mission pack: Localisation stringtables. |
| `Tacops/Addons/languagemissions_f_tacops.pbo` | 3.8 | data | Tac-Ops mission pack: Mission localisation stringtables. |
| `Tacops/Addons/missions_f_tacops.pbo` | 74.6 | config, textures, scripts, sounds | Tac-Ops mission pack: Mission and campaign assets. |
| `Tacops/Addons/modules_f_tacops.pbo` | 0.1 | config, textures, scripts | Tac-Ops mission pack: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Tacops/Addons/music_f_tacops.pbo` | 21.8 | sounds | Tac-Ops mission pack: Music. |
| `Tacops/Addons/sounds_f_tacops.pbo` | 18.2 | sounds | Tac-Ops mission pack: Sound engine config and audio assets. |
| `Tacops/Addons/ui_f_tacops.pbo` | 53.8 | config, textures, scripts | Tac-Ops mission pack: User interface configs (Rsc*, markers, map). |
| `Tank/Addons/armor_f_tank.pbo` | 618.0 | models, textures, materials | Tanks DLC: Armoured tracked vehicles. |
| `Tank/Addons/cargoposes_f_tank.pbo` | 1.4 | animation | Tanks DLC: Cargo and seat pose animation. |
| `Tank/Addons/characters_f_tank.pbo` | 19.5 | models, textures, materials | Tanks DLC: Soldiers, heads, uniforms and characters. |
| `Tank/Addons/data_f_tank.pbo` | 20.1 | textures | Tanks DLC: Shared models, textures and global data. |
| `Tank/Addons/dubbing_f_tank.pbo` | 13.6 | animation, sounds | Tanks DLC: Voice dubbing audio. |
| `Tank/Addons/editorpreviews_f_tank.pbo` | 1.4 | textures | Tanks DLC: Eden editor preview thumbnails. |
| `Tank/Addons/functions_f_tank.pbo` | 0.0 | scripts | Tanks DLC: SQF function library (CfgFunctions). |
| `Tank/Addons/language_f_tank.pbo` | 0.6 | data | Tanks DLC: Localisation stringtables. |
| `Tank/Addons/languagemissions_f_tank.pbo` | 1.7 | data | Tanks DLC: Mission localisation stringtables. |
| `Tank/Addons/missions_f_tank.pbo` | 10.6 | config, scripts | Tanks DLC: Mission and campaign assets. |
| `Tank/Addons/missions_f_tank_data.pbo` | 125.6 | textures, sounds | Tanks DLC: Mission and campaign assets - data assets. |
| `Tank/Addons/modules_f_tank.pbo` | 0.0 | scripts | Tanks DLC: Eden/Zeus editor modules (CfgVehicles, CfgFunctions). |
| `Tank/Addons/music_f_tank.pbo` | 12.2 | sounds | Tanks DLC: Music. |
| `Tank/Addons/props_f_tank.pbo` | 136.3 | models, textures, materials | Tanks DLC: Static props. |
| `Tank/Addons/sounds_f_tank.pbo` | 32.8 | sounds | Tanks DLC: Sound engine config and audio assets. |
| `Tank/Addons/structures_f_tank.pbo` | 120.8 | models, textures, materials | Tanks DLC: Buildings and structures. |
| `Tank/Addons/ui_f_tank.pbo` | 23.3 | textures | Tanks DLC: User interface configs (Rsc*, markers, map). |
| `Tank/Addons/weapons_f_tank.pbo` | 64.7 | models, textures, materials, animation | Tanks DLC: Weapons, ammunition and magazines. |
| `z/a3db/addons/a3db_main.pbo` | 0.5 | config, textures | a3db_main. |
| `z/a3db/addons/a3db_sql.pbo` | 0.0 | config, scripts | a3db_sql. |

## 4. Config-root PBOs a mod overrides

These PBOs define the global config roots. A mod overrides by reopening the
class in its own CfgPatches addon. Root classes verified by derapifying each
`config.bin` and grepping the top-level `class` declarations.

| PBO | Root classes carried (verified) |
|---|---|
| `Addons/animals_f.pbo` | CfgMovesAnimal, CfgMovesBird, CfgMovesButterfly, CfgFSMs, CfgVehicles (animals) |
| `Addons/anims_f.pbo` | CfgMoves* and CfgGestures* (via a3\anims_f\config) |
| `Addons/characters_f.pbo` | CfgVehicles (units), CfgWeapons (uniforms/headgear), CfgGlasses, CfgIdentities, CfgSkeletonParameters, CfgFSMs |
| `Addons/data_f.pbo` | CfgGroups, CfgFactionClasses, CfgSurfaces, CfgCloudlets, CfgOpticsEffect, CfgDifficultyPresets, CfgMods |
| `Addons/editor_f.pbo` | CfgEditorObjects, CfgNonAIVehicles |
| `Addons/functions_f.pbo` | CfgFunctions (A3), CfgCommands, CfgRemoteExec, CfgRespawnTemplates, CfgWaypoints |
| `Addons/map_altis.pbo` | CfgWorlds (Altis), CfgWorldList |
| `Addons/modules_f.pbo` | CfgVehicles (modules), CfgFactionClasses, CfgFunctions, Cfg3DEN |
| `Addons/sounds_f.pbo` | CfgEnvSounds, CfgEnvSpatialSounds, CfgSoundSets, CfgSoundShaders, CfgSFX, CfgMusic |
| `Addons/static_f.pbo` | CfgMovesBasic, CfgMovesMaleSdr, CfgMovesWomen, CfgVehicles (static weapons) |
| `Addons/ui_f.pbo` | UI ROOT: RscMapControl, CfgMarkers, CfgMarkerClasses, CfgMarkerColors, CfgLocationTypes, CfgCurator, CfgVehicleIcons, CfgWorlds |
| `Addons/weapons_f.pbo` | CfgWeapons, CfgAmmo, CfgMagazines, CfgRecoils, CfgMagazineWells |
| `Dta/bin.pbo` | ENGINE CORE: CfgVehicles, CfgWeapons, CfgAmmo, CfgMagazines, CfgRecoils, CfgWorlds, CfgSurfaces, CfgMarkers, CfgLocationTypes, CfgMovesBasic, CfgEnvSounds, CfgFontFamilies, CfgCloudlets, CfgLights, RscMapControl |

Every DLC reopens the same roots with a `_<dlc>` suffix (flagged `[ROOT]`).
`ui_f*` carries the map and marker roots (`RscMapControl`, `CfgMarkers`,
`CfgMarkerClasses`, `CfgMarkerColors`, `CfgLocationTypes`, `CfgCurator`,
`CfgVehicleIcons`). `weapons_f*` carries `CfgWeapons`/`CfgAmmo`/`CfgMagazines`.
`characters_f*` carries the unit classes. `data_f*` carries `CfgGroups`,
`CfgFactionClasses`, `CfgSurfaces`. `map_*` carries one `CfgWorlds` per terrain.

Terrains (CfgWorlds): Altis, Stratis, VR (base); Malden (Argo); Livonia
(Enoch); Tanoa (Expansion). Each terrain is three kinds of PBO: `<map>.pbo`
(world binary and CfgWorlds), `<map>_data*` (models, textures, materials), and
`<map>_scenes_f` (scripted scenes).

## 5. SQF function and module PBOs

- `Addons/functions_f.pbo` - the A3 function library, 2307 files, prefix
  `a3\functions_f`. Carries `CfgFunctions`, `CfgCommands`, `CfgRemoteExec`,
  `CfgRespawnTemplates`, `CfgWaypoints`, `CfgORBATDefault`,
  `CfgPostProcessTemplates`. Public functions compile as `BIS_fnc_*`.
- `Addons/modules_f.pbo` - editor and Zeus modules. Carries `CfgVehicles`
  module classes, `CfgFactionClasses`, `CfgFunctions`, `Cfg3DEN`.
- Every DLC ships `functions_f_<dlc>` and `modules_f_<dlc>` (flagged `[FUNC]`).
- Supporting function PBOs: `functions_f_bootcamp`, `functions_f_decade`,
  `functions_f_epa`, `functions_f_epc`, `functions_f_exp_a`,
  `functions_f_warlords`, `functions_f_curator`.

Script-bearing PBOs with a different root: `missions_f*` (framework scripts),
`map_*_scenes_f` (scene scripts), `editor_f` (`CfgEditorObjects`), `3den`
(Eden editor scripts), `anims_f*` and `animals_f` (`CfgFSMs`).

## 6. Non-standard PBOs

17 mission archives under `MPMissions/` and `mpmissions/` do not use
the `\x00sreV` header. They begin with mission data (for example
`description.ext`). They are playable missions, not addons. A raw header parse
cannot read them; the engine and `hemtt utils pbo inspect` can. They are
listed in the JSON with `error: not a standard PBO header`.

## 7. Code citations

- `hemtt` 1.22.0 (`~/.local/bin/hemtt`).
- PBO header spec derived from raw bytes of the install; cross-checked against
  `hemtt utils pbo inspect` output (prefix, product, version, file count).
- Config roots verified against derapified `config.bin` for 15 PBOs; engine
  line numbers cross-checked with `engine-config-surface.md`.

