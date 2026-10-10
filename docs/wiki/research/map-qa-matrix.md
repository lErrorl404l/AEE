# Map QA matrix

Every map invariant maps to one machine check. This record names the invariant,
the check that proves it and the file that holds the check. Where an existing
suite already proves the invariant, this record cites it. It adds a check only
for an invariant that no suite proves.

The live oracle is the Docker mission. Probe `P117` holds the four ADR-028 map
defects, `P121` the ADR-030 legibility surface, `P127` the cardinal MGRS grid,
`P134` the density constants and `P142` the surface reach.

## The invariants

| # | Invariant | Machine check | File |
|---|---|---|---|
| 1 | Exactly one grid: the AEE MGRS overlay is the single complete ruler, and the engine grid fields are off on every AEE target. | TestTerrainMgrsContrast.test_the_engine_grid_fields_are_off_on_every_target | tools/tests/test_terrain.py |
| 2 | The engine numeric numbers and the engine lines follow the shipped contract: both engine grid fields are off on every AEE target. | TestTerrainMgrsContrast.test_the_engine_grid_fields_are_off_on_every_target | tools/tests/test_terrain.py |
| 3 | Every engine marker family renders an AEE symbol. | TestMapQaChecks.test_every_engine_marker_family_renders_an_aee_symbol | tools/tests/test_map_qa.py |
| 4 | The AEE markers carry categories. | TestSymbologyMarkerConfig.test_the_marker_class_group_is_declared | tools/tests/test_symbology.py |
| 5 | The echelon overlay is a 1:2 box above the frame. | TestMapQaChecks.test_the_echelon_overlay_is_a_one_to_two_box | tools/tests/test_map_qa.py |
| 6 | The location classes restate their parent. | TestTerrainInheritance.test_every_parented_location_class_restates_its_vanilla_parent | tools/tests/test_terrain.py |
| 7 | The object icons cover every engine object name (config class names resolve case-insensitively). | TestTerrainObjectConfig.test_every_object_icon_is_in_the_aee_terrain_prefix | tools/tests/test_terrain.py |
| 8 | The MGRS grid is cardinal: the emitted lines are axis aligned and carry no tilt. | TestDefect5Straightness.test_the_emitted_lines_are_axis_aligned | tools/tests/test_mgrs_map_layer.py |
| 9 | The MGRS line contrast is dark and high. | TestTerrainMgrsContrast.test_the_line_colours_are_dark_and_high_contrast | tools/tests/test_terrain.py |
| 10 | The terrain symbol size is the vanilla interface-scaled value. | TestTerrainLook.test_the_icon_sizes_scale_with_the_interface_size | tools/tests/test_terrain.py |

Row 1 and row 2 are the same shipped contract. The earlier ADR-030 text said
the engine numbers return and only the lines stay off. The shipped config sets
both fields to alpha 0, so the AEE MGRS overlay is the single ruler. The check
is the shipped contract.

Row 3 and row 5 had no machine check. The live probe `P117` proves both, but a
probe needs Docker. `tools/tests/test_map_qa.py` adds a source-contract check
for each: the engine marker family textures and the pure echelon size kernel.

Row 6 is proved by `test_terrain.py`. `test_map_qa.py` adds a second check that
the parent graph recorded below matches the shipped config, so this record
cannot go stale.

## The location parent graph

The parents are read from the engine config (`Dta/bin.pbo`, `Addons/ui_f.pbo`).
The three parentless roots have no parent to restate.

| Class | Parent |
|---|---|
| Strategic | Name |
| StrongpointArea | Strategic |
| FlatArea | Strategic |
| FlatAreaCity | FlatArea |
| FlatAreaCitySmall | FlatAreaCity |
| CityCenter | Strategic |
| Airport | Strategic |
| NameMarine | Name |
| NameCityCapital | Name |
| NameCity | Name |
| NameVillage | Name |
| NameLocal | Name |
| Hill | Name |
| ViewPoint | Hill |
| RockArea | Hill |
| BorderCrossing | Hill |
| VegetationBroadleaf | Hill |
| VegetationFir | Hill |
| VegetationPalm | Hill |
| VegetationVineyard | Hill |
| fakeTown | Name |
| Flag | Hill |

The roots are `Mount`, `Name` and `Area`.
