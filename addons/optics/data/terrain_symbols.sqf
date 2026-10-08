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
        ["hill", "relief", "point", [0.7, 0.48, 0.32, 1], "10", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0097 SurveyPointGeodeticHighestP"],
        ["mountain", "relief", "point", [0.7, 0.48, 0.32, 1], "10", "derived", "FM 21-31 section 10 relief; a mountain is a summit, drawn as a peak"],
        ["rock", "relief", "point", [0.7, 0.48, 0.32, 1], "10", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0364 RockFormationP"],
        ["depression", "relief", "point", [0.7, 0.48, 0.32, 1], "10", "derived", "FM 21-31 section 10 relief; a depression is a hachured closed contour with the ticks inward"],
        ["spot_height", "control", "point", [0.0, 0.0, 0.0, 1], "22", "derived", "FM 21-31 section 22 control points and elevations; spot height is a dot with a value"],
        ["triangulation_point", "control", "point", [0.0, 0.0, 0.0, 1], "22", "derived", "FM 21-31 section 22; a triangulation point is a triangle"],
        ["benchmark", "control", "point", [0.0, 0.0, 0.0, 1], "22", "derived", "FM 21-31 section 22; a benchmark is a levelling mark"],
        ["deciduous", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0046 TreeDeciduousP"],
        ["coniferous", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0047 TreeEvergreenP"],
        ["mixed_forest", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "derived", "FM 21-31 section 11 vegetation; mixed forest is the two canopies together"],
        ["orchard", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "derived", "FM 21-31 section 11 vegetation; an orchard is a regular row of trees"],
        ["vineyard", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0034 PlantationVineyardA"],
        ["brushwood", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0048 BrushA"],
        ["palm", "vegetation", "point", [0.0, 0.5, 0.0, 1], "11", "derived", "DGIWG Symbol Register, symbol SO_0044 ForestWoodOtherP; no dedicated register glyph, nearest register drawing used"],
        ["stream", "hydrography", "line", [0.0, 0.5, 0.75, 1], "9", "derived", "FM 21-31 section 9 drainage; a perennial stream is a continuous line"],
        ["intermittent_stream", "hydrography", "line", [0.0, 0.5, 0.75, 1], "9", "derived", "FM 21-31 section 9 drainage; an intermittent stream is a dashed line"],
        ["lake", "hydrography", "area", [0.0, 0.5, 0.75, 1], "9", "derived", "FM 21-31 section 9 drainage; a lake is a closed water body"],
        ["marsh", "hydrography", "point", [0.0, 0.5, 0.75, 1], "9", "derived", "FM 21-31 section 9 drainage; a marsh is a grass tuft over water"],
        ["spring", "hydrography", "point", [0.0, 0.5, 0.75, 1], "9", "derived", "FM 21-31 section 9 drainage; a spring is a source point"],
        ["city", "populated", "point", [0.15, 0.15, 0.15, 1], "20", "derived", "FM 21-31 section 20 populated places; a city is a large built-up block"],
        ["town", "populated", "point", [0.15, 0.15, 0.15, 1], "20", "derived", "FM 21-31 section 20 populated places; a town is a medium built-up block"],
        ["village", "populated", "point", [0.15, 0.15, 0.15, 1], "20", "derived", "FM 21-31 section 20 populated places; a village is a small built-up block"],
        ["built_up_area", "populated", "area", [0.15, 0.15, 0.15, 1], "19", "derived", "FM 21-31 section 19 buildings and populated places; a built-up area is a hatched block"],
        ["church", "works", "point", [0.1, 0.1, 0.1, 1], "19", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0140 ChristianCathedralP"],
        ["chapel", "works", "point", [0.1, 0.1, 0.1, 1], "19", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0619 ChristianChapelNonObstructionIntactA"],
        ["cross", "works", "point", [0.1, 0.1, 0.1, 1], "19", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0124 CemeteryChristianP"],
        ["ruin", "works", "point", [0.1, 0.1, 0.1, 1], "19", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0102 RuinsNonObstructionP"],
        ["hospital", "works", "point", [0.1, 0.1, 0.1, 1], "21", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0151 HospitalNonObstructionIntactP"],
        ["monument", "works", "point", [0.1, 0.1, 0.1, 1], "21", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0104 MonumentP"],
        ["radio_tower", "works", "point", [0.1, 0.1, 0.1, 1], "21", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0600 TowerCommunicationNonObstructionP"],
        ["telephone_exchange", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; telephone exchanges and repeaters (DGIWG DTM PO_0454)"],
        ["lighthouse", "works", "point", [0.1, 0.1, 0.1, 1], "12", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0080 LighthouseP"],
        ["water_tower", "works", "point", [0.1, 0.1, 0.1, 1], "21", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0015 TowerWaterTowerP"],
        ["power_plant", "works", "point", [0.1, 0.1, 0.1, 1], "21", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0155 PowerSubstationP"],
        ["solar", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "DGIWG Symbol Register, symbol SO_0001 SolarPanelP; no dedicated register glyph, nearest register drawing used"],
        ["wind", "works", "point", [0.1, 0.1, 0.1, 1], "21", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0157 WindTurbineP"],
        ["wave", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "DGIWG Symbol Register, symbol SO_0001 TidalWaterA; no dedicated register glyph, nearest register drawing used"],
        ["fuel_station", "works", "point", [0.1, 0.1, 0.1, 1], "21", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0146 MotorVehicleStationP"],
        ["factory", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a factory is a building with a sawtooth roof"],
        ["quarry", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a quarry is an open pit"],
        ["stack", "works", "point", [0.1, 0.1, 0.1, 1], "21", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0156 SmokestackP"],
        ["water_tank", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "FM 21-31 section 21; a water tank is a tank on the ground"],
        ["fountain", "works", "point", [0.0, 0.5, 0.75, 1], "21", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0180 FountainP"],
        ["tourism", "works", "point", [0.1, 0.1, 0.1, 1], "21", "derived", "DGIWG Symbol Register, symbol SO_0001 AmusementParkAttractionP; no dedicated register glyph, nearest register drawing used"],
        ["view_tower", "works", "point", [0.1, 0.1, 0.1, 1], "21", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0079 TowerOtherP"],
        ["shipwreck", "hydrography", "point", [0.0, 0.5, 0.75, 1], "12", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0160 WreckP"],
        ["bunker", "military", "point", [0.1, 0.4, 0.1, 1], "19", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0330 SurfaceBunkerP"],
        ["fortress", "military", "point", [0.1, 0.4, 0.1, 1], "19", "sourced", "DGIWG Symbol Register (DTM50 / DGIWG 130 Web Symbology / STANAG 3675), symbol SO_0099 FortificationP"],
        ["airfield", "transport", "point", [0.8, 0.1, 0.1, 1], "15", "derived", "FM 21-31 section 15 roads small scale; an airfield is crossed runways"],
        ["bus_stop", "transport", "point", [0.8, 0.1, 0.1, 1], "16", "derived", "DGIWG Symbol Register, symbol SO_0153 TransportationStationCheckpointNonObstructionIntactP; no dedicated register glyph, nearest register drawing used"],
        ["quay", "transport", "point", [0.1, 0.1, 0.1, 1], "12", "sourced", "USGS Topographic Map Symbols (2005), GIP; BreakwaterPierJettyOrWharf; the register has no point symbol for a quay"],
        ["bridge", "transport", "point", [0.1, 0.1, 0.1, 1], "18", "derived", "FM 21-31 section 18 crossings; a bridge passes over water"],
        ["tunnel", "transport", "point", [0.1, 0.1, 0.1, 1], "16", "derived", "FM 21-31 section 16; a tunnel is an arch"],
        ["ford", "transport", "point", [0.0, 0.5, 0.75, 1], "18", "derived", "FM 21-31 section 18 crossings; a ford is a crossing on water"],
        ["railway", "transport", "line", [0.0, 0.0, 0.0, 1], "17", "derived", "FM 21-31 section 17 railroads; a railway is a line with cross-ties"],
        ["international_boundary", "boundary", "line", [0.0, 0.0, 0.0, 1], "23", "derived", "FM 21-31 section 23 boundaries; an international boundary is a dash-dot-dot line"],
        ["provincial_boundary", "boundary", "line", [0.0, 0.0, 0.0, 1], "23", "derived", "FM 21-31 section 23 boundaries; a provincial boundary is a dashed line"],
        ["border_crossing", "boundary", "point", [0.0, 0.0, 0.0, 1], "23", "derived", "DGIWG Symbol Register, symbol SO_0153 GateBorderCrossingP; no dedicated register glyph, nearest register drawing used"]
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
        ["Hill", "hill", "relief", [1, 1, 1, 1], 14, "", 0.05, 0, "derived", "CfgLocationTypes Hill, drawStyle icon; DGIWG SO_0097 SurveyPointGeodeticHighestP"],
        ["ViewPoint", "monument", "works", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes ViewPoint, drawStyle icon; DGIWG SO_0104 MonumentP"],
        ["RockArea", "rock", "relief", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes RockArea, drawStyle icon; DGIWG SO_0364 RockFormationP"],
        ["BorderCrossing", "border_crossing", "boundary", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes BorderCrossing, drawStyle icon; DGIWG SO_0153 GateBorderCrossingP"],
        ["VegetationBroadleaf", "deciduous", "vegetation", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes VegetationBroadleaf, drawStyle icon; DGIWG SO_0046 TreeDeciduousP"],
        ["VegetationFir", "coniferous", "vegetation", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes VegetationFir, drawStyle icon; DGIWG SO_0047 TreeEvergreenP"],
        ["VegetationPalm", "palm", "vegetation", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes VegetationPalm, drawStyle icon; DGIWG SO_0044 ForestWoodOtherP"],
        ["VegetationVineyard", "vineyard", "vegetation", [1, 1, 1, 1], 12, "", 0.05, 0, "derived", "CfgLocationTypes VegetationVineyard, drawStyle icon; DGIWG SO_0034 PlantationVineyardA"],
        ["fakeTown", "", "populated", [0.15, 0.15, 0.15, 1], 12, "AEEFont", 0.06, 0, "derived", "CfgLocationTypes fakeTown, drawStyle area"],
        ["Area", "", "populated", [0.15, 0.15, 0.15, 1], 12, "AEEFont", 0.06, 0, "derived", "CfgLocationTypes Area, drawStyle area"],
        ["Flag", "", "populated", [0.8, 0.1, 0.1, 1], 12, "AEEFont", 0.05, 0, "derived", "CfgLocationTypes Flag, drawStyle icon"]
    ],
    [
        ["Bush", "brushwood", "vegetation", [1, 1, 1, 1], 10, 1, "derived", "RscMapControl Bush; DGIWG SO_0048 BrushA"],
        ["Rock", "rock", "relief", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Rock; DGIWG SO_0364 RockFormationP"],
        ["SmallTree", "deciduous", "vegetation", [1, 1, 1, 1], 10, 1, "derived", "RscMapControl SmallTree; DGIWG SO_0046 TreeDeciduousP"],
        ["Tree", "deciduous", "vegetation", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Tree; DGIWG SO_0046 TreeDeciduousP"],
        ["busstop", "bus_stop", "transport", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl busstop; DGIWG SO_0153 TransportationStationCheckpointNonObstructionIntactP"],
        ["fuelstation", "fuel_station", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl fuelstation; DGIWG SO_0146 MotorVehicleStationP"],
        ["hospital", "hospital", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl hospital; DGIWG SO_0151 HospitalNonObstructionIntactP"],
        ["church", "church", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl church; DGIWG SO_0140 ChristianCathedralP"],
        ["lighthouse", "lighthouse", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl lighthouse; DGIWG SO_0080 LighthouseP"],
        ["power", "power_plant", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl power; DGIWG SO_0155 PowerSubstationP"],
        ["powersolar", "solar", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl powersolar; DGIWG SO_0001 SolarPanelP"],
        ["powerwave", "wave", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl powerwave; DGIWG SO_0001 TidalWaterA"],
        ["powerwind", "wind", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl powerwind; DGIWG SO_0157 WindTurbineP"],
        ["quay", "quay", "transport", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl quay; USGS (2005) pier symbol, PD"],
        ["transmitter", "radio_tower", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl transmitter; DGIWG SO_0600 TowerCommunicationNonObstructionP"],
        ["watertower", "water_tower", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl watertower; DGIWG SO_0015 TowerWaterTowerP"],
        ["Cross", "cross", "works", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Cross; DGIWG SO_0124 CemeteryChristianP"],
        ["Chapel", "chapel", "works", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Chapel; DGIWG SO_0619 ChristianChapelNonObstructionIntactA"],
        ["Shipwreck", "shipwreck", "hydrography", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl Shipwreck; DGIWG SO_0160 WreckP"],
        ["Bunker", "bunker", "military", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl Bunker; DGIWG SO_0330 SurfaceBunkerP"],
        ["Fortress", "fortress", "military", [1, 1, 1, 1], 16, 1, "derived", "RscMapControl Fortress; DGIWG SO_0099 FortificationP"],
        ["Fountain", "fountain", "works", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Fountain; DGIWG SO_0180 FountainP"],
        ["Ruin", "ruin", "works", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Ruin; DGIWG SO_0102 RuinsNonObstructionP"],
        ["Stack", "stack", "works", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Stack; DGIWG SO_0156 SmokestackP"],
        ["Tourism", "tourism", "works", [1, 1, 1, 1], 12, 1, "derived", "RscMapControl Tourism; DGIWG SO_0001 AmusementParkAttractionP"],
        ["ViewTower", "view_tower", "works", [1, 1, 1, 1], 14, 1, "derived", "RscMapControl ViewTower; DGIWG SO_0079 TowerOtherP"]
    ]
]
