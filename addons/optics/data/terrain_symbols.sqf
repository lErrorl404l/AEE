/*
Terrain and map-feature symbol tables (generated).

This file is GENERATED. The generator tools/validation/gen_terrain_tables.py
writes it from the validated source data/symbology/terrain_symbols.json. Do
not edit it by hand. Edit the source and regenerate it.

The authority is STANAG 3675, succeeded by the DGIWG Symbol Register (the
DTM50 product), with the US Army FM 21-31 and the USGS Topographic Map
Symbols sheet as the public-domain fallback. AEE draws the standard geometry
itself.

The three sections are, in order:

  0  terrain symbol id -> [id, category, dimension, colour, section, grade, source]
  1  location class     -> [class, symbol, category, colour, size, font, shadow, grade, source]
  2  object icon class  -> [class, symbol, category, colour, size, importance, grade, source]

A location or object row whose symbol is "" carries a colour only and no icon.
No value is invented: every row is sourced or derived and carries its source.
*/
[
    [
        ["hill", "relief", "point", [0.7, 0.48, 0.32, 1], "10", "derived", "FM 21-31 section 10 relief; a hill is a closed contour, drawn here as an open hachured mound"],
        ["mountain", "relief", "point", [0.7, 0.48, 0.32, 1], "10", "derived", "FM 21-31 section 10 relief; a mountain is a summit, drawn as a peak"],
        ["rock", "relief", "point", [0.7, 0.48, 0.32, 1], "10", "derived", "USGS Topographic Map Symbols; rock outcrop"],
        ["depression", "relief", "point", [0.7, 0.48, 0.32, 1], "10", "derived", "FM 21-31 section 10 relief; a depression is a hachured closed contour with the ticks inward"],
        ["spot_height", "control", "point", [0.0, 0.0, 0.0, 1], "22", "derived", "FM 21-31 section 22 control points and elevations; spot height is a dot with a value"],
        ["triangulation_point", "control", "point", [0.0, 0.0, 0.0, 1], "22", "derived", "FM 21-31 section 22; a triangulation point is a triangle"],
        ["benchmark", "control", "point", [0.0, 0.0, 0.0, 1], "22", "derived", "FM 21-31 section 22; a benchmark is a levelling mark"],
        ["deciduous", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "derived", "FM 21-31 section 11 vegetation; deciduous woodland is a broad canopy"],
        ["coniferous", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "derived", "FM 21-31 section 11 vegetation; coniferous woodland is a conical canopy"],
        ["mixed_forest", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "derived", "FM 21-31 section 11 vegetation; mixed forest is the two canopies together"],
        ["orchard", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "derived", "FM 21-31 section 11 vegetation; an orchard is a regular row of trees"],
        ["vineyard", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "derived", "FM 21-31 section 11 vegetation; a vineyard is a regular row of vines"],
        ["brushwood", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "derived", "FM 21-31 section 11 vegetation; brushwood is low scattered growth"],
        ["palm", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "derived", "FM 21-31 section 11 vegetation; a palm is a fronded tree"],
        ["stream", "hydrography", "line", [0.0, 0.5, 0.75, 1], "9", "derived", "FM 21-31 section 9 drainage; a perennial stream is a continuous line"],
        ["intermittent_stream", "hydrography", "line", [0.0, 0.5, 0.75, 1], "9", "derived", "FM 21-31 section 9 drainage; an intermittent stream is a dashed line"],
        ["lake", "hydrography", "area", [0.0, 0.5, 0.75, 1], "9", "derived", "FM 21-31 section 9 drainage; a lake is a closed water body"],
        ["marsh", "hydrography", "point", [0.0, 0.5, 0.75, 1], "9", "derived", "FM 21-31 section 9 drainage; a marsh is a grass tuft over water"],
        ["spring", "hydrography", "point", [0.0, 0.5, 0.75, 1], "9", "derived", "FM 21-31 section 9 drainage; a spring is a source point"],
        ["city", "populated", "point", [0.15, 0.15, 0.15, 1], "20", "derived", "FM 21-31 section 20 populated places; a city is a large built-up block"],
        ["town", "populated", "point", [0.15, 0.15, 0.15, 1], "20", "derived", "FM 21-31 section 20 populated places; a town is a medium built-up block"],
        ["village", "populated", "point", [0.15, 0.15, 0.15, 1], "20", "derived", "FM 21-31 section 20 populated places; a village is a small built-up block"],
        ["built_up_area", "populated", "area", [0.15, 0.15, 0.15, 1], "19", "derived", "FM 21-31 section 19 buildings and populated places; a built-up area is a hatched block"],
        ["church", "works", "point", [0.1, 0.1, 0.1, 1], "19", "derived", "FM 21-31 section 19; a church carries a cross"],
        ["chapel", "works", "point", [0.1, 0.1, 0.1, 1], "19", "derived", "FM 21-31 section 19; a chapel carries a cross"],
        ["cross", "works", "point", [0.1, 0.1, 0.1, 1], "19", "derived", "FM 21-31 section 19; a cross is a religious monument"],
        ["ruin", "works", "point", [0.1, 0.1, 0.1, 1], "19", "derived", "FM 21-31 section 19; a ruin is a broken building"],
        ["hospital", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21 industrial and public works; a hospital carries a cross in a frame"],
        ["monument", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a monument is an obelisk on a base"],
        ["radio_tower", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21 industrial works; radio and television broadcasting (DGIWG DTM PO_0409)"],
        ["telephone_exchange", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; telephone exchanges and repeaters (DGIWG DTM PO_0454)"],
        ["lighthouse", "works", "point", [0.1, 0.1, 0.1, 1], "12", "derived", "FM 21-31 section 12 coastal hydrography; a lighthouse (DGIWG DTM PO_1399)"],
        ["water_tower", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a water tower is a tank on legs"],
        ["power_plant", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a power plant is a building with a stack"],
        ["solar", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a solar works is a tilted panel"],
        ["wind", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a wind works is a turbine"],
        ["wave", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a wave works is a sea wave"],
        ["fuel_station", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a fuel station is a pump"],
        ["factory", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a factory is a building with a sawtooth roof"],
        ["quarry", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a quarry is an open pit"],
        ["stack", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a stack is a tall chimney"],
        ["water_tank", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a water tank is a tank on the ground"],
        ["fountain", "works", "point", [0.0, 0.5, 0.75, 1], "21", "derived", "FM 21-31 section 21; a fountain is a basin with a jet"],
        ["tourism", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a tourism or viewpoint point is a sight point"],
        ["view_tower", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a viewing tower is a tower with a platform"],
        ["shipwreck", "hydrography", "point", [0.0, 0.5, 0.75, 1], "12", "derived", "FM 21-31 section 12 coastal hydrography; a wreck is a broken hull"],
        ["bunker", "military", "point", [0.1, 0.4, 0.1, 1], "19", "derived", "FM 21-31 section 19 structures; a bunker is a low block with a slit"],
        ["fortress", "military", "point", [0.1, 0.4, 0.1, 1], "19", "derived", "FM 21-31 section 19 structures; a fortress is a block with battlements"],
        ["airfield", "transport", "point", [0.8, 0.1, 0.1, 1], "15", "derived", "FM 21-31 section 15 roads small scale; an airfield is crossed runways"],
        ["bus_stop", "transport", "point", [0.8, 0.1, 0.1, 1], "16", "derived", "FM 21-31 section 16 related road features; a bus stop is a stop mark"],
        ["quay", "transport", "point", [0.1, 0.1, 0.1, 1], "12", "derived", "FM 21-31 section 12 coastal hydrography; a quay is a wharf"],
        ["bridge", "transport", "point", [0.1, 0.1, 0.1, 1], "18", "derived", "FM 21-31 section 18 crossings; a bridge passes over water"],
        ["tunnel", "transport", "point", [0.1, 0.1, 0.1, 1], "16", "derived", "FM 21-31 section 16; a tunnel is an arch"],
        ["ford", "transport", "point", [0.0, 0.5, 0.75, 1], "18", "derived", "FM 21-31 section 18 crossings; a ford is a crossing on water"],
        ["railway", "transport", "line", [0.0, 0.0, 0.0, 1], "17", "derived", "FM 21-31 section 17 railroads; a railway is a line with cross-ties"],
        ["international_boundary", "boundary", "line", [0.0, 0.0, 0.0, 1], "23", "derived", "FM 21-31 section 23 boundaries; an international boundary is a dash-dot-dot line"],
        ["provincial_boundary", "boundary", "line", [0.0, 0.0, 0.0, 1], "23", "derived", "FM 21-31 section 23 boundaries; a provincial boundary is a dashed line"],
        ["border_crossing", "boundary", "point", [0.0, 0.0, 0.0, 1], "23", "derived", "FM 21-31 section 23 boundaries; a border crossing is a gate"]
    ],
    [
        ["Mount", "", "relief", [0.7, 0.48, 0.32, 1], 18, "AEEFont", 0.09, 1, "derived", "CfgLocationTypes Mount, drawStyle mount; the engine draws the relief, the colour is the standard relief brown"],
        ["Name", "", "populated", [0.15, 0.15, 0.15, 1], 12, "AEEFont", 0.06, 1, "derived", "CfgLocationTypes Name, drawStyle name; a place label"],
        ["Strategic", "", "military", [0.8, 0.1, 0.1, 1], 16, "AEEFont", 0.08, 1, "derived", "CfgLocationTypes Strategic, drawStyle area; a strategic area"],
        ["StrongpointArea", "", "military", [0.8, 0.1, 0.1, 1], 14, "AEEFont", 0.07, 1, "derived", "CfgLocationTypes StrongpointArea, drawStyle area"],
        ["FlatArea", "", "populated", [0.15, 0.15, 0.15, 1], 14, "AEEFont", 0.07, 0, "derived", "CfgLocationTypes FlatArea, drawStyle area"],
        ["FlatAreaCity", "", "populated", [0.15, 0.15, 0.15, 1], 14, "AEEFont", 0.07, 0, "derived", "CfgLocationTypes FlatAreaCity, drawStyle area"],
        ["FlatAreaCitySmall", "", "populated", [0.15, 0.15, 0.15, 1], 12, "AEEFont", 0.06, 0, "derived", "CfgLocationTypes FlatAreaCitySmall, drawStyle area"],
        ["CityCenter", "", "populated", [0.15, 0.15, 0.15, 1], 16, "AEEFont", 0.08, 1, "derived", "CfgLocationTypes CityCenter, drawStyle area; a city centre area"],
        ["Airport", "", "transport", [0.8, 0.1, 0.1, 1], 16, "AEEFont", 0.07, 1, "derived", "CfgLocationTypes Airport, drawStyle area; an airport area"],
        ["NameMarine", "", "hydrography", [0.0, 0.5, 0.75, 1], 12, "AEEFont", 0.06, 1, "derived", "CfgLocationTypes NameMarine, drawStyle name; a marine place label"],
        ["NameCityCapital", "", "populated", [0.15, 0.15, 0.15, 1], 14, "AEEFont", 0.09, 1, "derived", "CfgLocationTypes NameCityCapital, drawStyle name"],
        ["NameCity", "", "populated", [0.15, 0.15, 0.15, 1], 13, "AEEFont", 0.075, 1, "derived", "CfgLocationTypes NameCity, drawStyle name"],
        ["NameVillage", "", "populated", [0.15, 0.15, 0.15, 1], 11, "AEEFont", 0.06, 1, "derived", "CfgLocationTypes NameVillage, drawStyle name"],
        ["NameLocal", "", "populated", [0.15, 0.15, 0.15, 1], 10, "AEEFont", 0.05, 1, "derived", "CfgLocationTypes NameLocal, drawStyle name"],
        ["Hill", "hill", "relief", [1, 1, 1, 1], 14, "", 0.05, 0, "derived", "CfgLocationTypes Hill, drawStyle icon; relief prints brown"],
        ["ViewPoint", "monument", "works", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes ViewPoint, drawStyle icon; a sight point"],
        ["RockArea", "rock", "relief", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes RockArea, drawStyle icon; a rock outcrop"],
        ["BorderCrossing", "border_crossing", "boundary", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes BorderCrossing, drawStyle icon; a boundary gate"],
        ["VegetationBroadleaf", "deciduous", "vegetation", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes VegetationBroadleaf, drawStyle icon; vegetation prints green"],
        ["VegetationFir", "coniferous", "vegetation", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes VegetationFir, drawStyle icon; a conical canopy"],
        ["VegetationPalm", "palm", "vegetation", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes VegetationPalm, drawStyle icon; a fronded tree"],
        ["VegetationVineyard", "vineyard", "vegetation", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes VegetationVineyard, drawStyle icon; a row of vines"],
        ["fakeTown", "", "populated", [0.15, 0.15, 0.15, 1], 12, "AEEFont", 0.06, 0, "derived", "CfgLocationTypes fakeTown, drawStyle area"],
        ["Area", "", "populated", [0.15, 0.15, 0.15, 1], 12, "AEEFont", 0.06, 0, "derived", "CfgLocationTypes Area, drawStyle area"],
        ["Flag", "", "populated", [0.8, 0.1, 0.1, 1], 12, "AEEFont", 0.05, 0, "derived", "CfgLocationTypes Flag, drawStyle icon"]
    ],
    [
        ["Bush", "brushwood", "vegetation", [1, 1, 1, 1], 10, 1, "derived", "RscMapControl Bush; low growth, FM 21-31 section 11"],
        ["Rock", "rock", "relief", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Rock; a rock outcrop"],
        ["SmallTree", "deciduous", "vegetation", [1, 1, 1, 1], 10, 1, "derived", "RscMapControl SmallTree; FM 21-31 section 11"],
        ["Tree", "deciduous", "vegetation", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Tree; FM 21-31 section 11"],
        ["busstop", "bus_stop", "transport", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl busstop; FM 21-31 section 16"],
        ["fuelstation", "fuel_station", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl fuelstation; FM 21-31 section 21"],
        ["hospital", "hospital", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl hospital; FM 21-31 section 21"],
        ["church", "church", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl church; FM 21-31 section 19"],
        ["lighthouse", "lighthouse", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl lighthouse; FM 21-31 section 12"],
        ["power", "power_plant", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl power; FM 21-31 section 21"],
        ["powersolar", "solar", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl powersolar; FM 21-31 section 21"],
        ["powerwave", "wave", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl powerwave; FM 21-31 section 21"],
        ["powerwind", "wind", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl powerwind; FM 21-31 section 21"],
        ["quay", "quay", "transport", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl quay; FM 21-31 section 12"],
        ["transmitter", "radio_tower", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl transmitter; FM 21-31 section 21 and DGIWG DTM PO_0409"],
        ["watertower", "water_tower", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl watertower; FM 21-31 section 21"],
        ["Cross", "cross", "works", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Cross; FM 21-31 section 19"],
        ["Chapel", "chapel", "works", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Chapel; FM 21-31 section 19"],
        ["Shipwreck", "shipwreck", "hydrography", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl Shipwreck; FM 21-31 section 12"],
        ["Bunker", "bunker", "military", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl Bunker; FM 21-31 section 19"],
        ["Fortress", "fortress", "military", [1, 1, 1, 1], 16, 1, "derived", "RscMapControl Fortress; FM 21-31 section 19"],
        ["Fountain", "fountain", "works", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Fountain; FM 21-31 section 21"],
        ["Ruin", "ruin", "works", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Ruin; FM 21-31 section 19"],
        ["Stack", "stack", "works", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Stack; FM 21-31 section 21"],
        ["Tourism", "tourism", "works", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Tourism; FM 21-31 section 21"],
        ["ViewTower", "view_tower", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl ViewTower; FM 21-31 section 21"]
    ]
]
