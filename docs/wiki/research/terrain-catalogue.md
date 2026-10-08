# AEE terrain symbol catalogue

The AEE terrain symbol catalogue, a map legend for the terrain and map-feature textures. The mapping is data driven from the DGIWG Symbol Register concept index: each feature names the register concept it needs, and the SO_#### the register publishes for that concept. A feature that has no dedicated register glyph is recorded, never silently substituted.

Source: STANAG 3675 Edition 2, succeeded by the DGIWG Symbol Register (DTM50, DGIWG 252-3); USGS Topographic Map Symbols (2005) for the one public-domain fallback.

Attribution: Contains DGIWG Symbol Register data, (C) DGIWG, CC BY 2.0.

The register id is the DGIWG Symbol Register symbol. The concept is the
register concept the feature needs. The grade is specific when the register
publishes a dedicated glyph, generic when only a shared catch-all glyph
exists, substituted when the register has no usable glyph and a different
published glyph is used, and non_register when no register source exists.

Count: 31 symbols (generic 2, non_register 1, specific 24, substituted 4).

## Hill (spot height) (`hill`)

- Depicts: a geodetic survey point at the highest elevation, a triangle with a central dot.
- Register: SO_0097 SurveyPointGeodeticHighestP.
- Concept needed: SurveyPointGeodeticHighestP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: CfgLocationTypes Hill.

## Rock formation (`rock`)

- Depicts: a rock formation, an open irregular outline.
- Register: SO_0364 RockFormationP.
- Concept needed: RockFormationP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: CfgLocationTypes RockArea, RscMapControl Rock.

## Brushwood (scrub) (`brushwood`)

- Depicts: brush or scrub, an area of small tufts.
- Register: SO_0048 BrushA.
- Concept needed: BrushA.
- Grade: specific.
- Geometry: Area.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl Bush.

## Coniferous tree (`coniferous`)

- Depicts: an evergreen tree, a pointed crown on a stem.
- Register: SO_0047 TreeEvergreenP.
- Concept needed: TreeEvergreenP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: CfgLocationTypes VegetationFir.

## Deciduous tree (`deciduous`)

- Depicts: a deciduous tree, a rounded crown on a stem.
- Register: SO_0046 TreeDeciduousP.
- Concept needed: TreeDeciduousP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: CfgLocationTypes VegetationBroadleaf, RscMapControl SmallTree, RscMapControl Tree.

## Palm tree (`palm`)

- Depicts: other forest or wood, a generic tree symbol.
- Register: SO_0044 ForestWoodOtherP.
- Concept needed: none published.
- Grade: substituted.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: CfgLocationTypes VegetationPalm.

## Vineyard (`vineyard`)

- Depicts: a vineyard, an area of vine rows.
- Register: SO_0034 PlantationVineyardA.
- Concept needed: PlantationVineyardA.
- Grade: specific.
- Geometry: Area.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: CfgLocationTypes VegetationVineyard.

## Shipwreck (`shipwreck`)

- Depicts: a wreck, a hull shape.
- Register: SO_0160 WreckP.
- Concept needed: WreckP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl Shipwreck.

## Chapel (`chapel`)

- Depicts: a Christian chapel, a small building with a cross.
- Register: SO_0619 ChristianChapelNonObstructionIntactA.
- Concept needed: ChristianChapelNonObstructionIntactA.
- Grade: specific.
- Geometry: Area.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl Chapel.

## Church (`church`)

- Depicts: a Christian church, a building with a cross.
- Register: SO_0140 ChristianChurchP.
- Concept needed: ChristianChurchP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl church.

## Cemetery cross (`cross`)

- Depicts: a Christian cemetery, a cross on a grave.
- Register: SO_0124 CemeteryChristianP.
- Concept needed: CemeteryChristianP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl Cross.

## Fountain (`fountain`)

- Depicts: a fountain, a jet of water.
- Register: SO_0180 FountainP.
- Concept needed: FountainP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl Fountain.

## Fuel station (`fuel_station`)

- Depicts: a motor vehicle station, a fuel pump.
- Register: SO_0146 MotorVehicleStationP.
- Concept needed: MotorVehicleStationP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl fuelstation.

## Hospital (`hospital`)

- Depicts: a hospital, a building with a cross.
- Register: SO_0151 HospitalNonObstructionIntactP.
- Concept needed: HospitalNonObstructionIntactP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl hospital.

## Lighthouse (`lighthouse`)

- Depicts: a lighthouse, a tower with a light.
- Register: SO_0080 LighthouseP.
- Concept needed: LighthouseP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl lighthouse.

## Monument (`monument`)

- Depicts: a monument, a pillar on a base.
- Register: SO_0104 MonumentP.
- Concept needed: MonumentP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: CfgLocationTypes ViewPoint.

## Power plant (`power_plant`)

- Depicts: a power substation, a transformer symbol.
- Register: SO_0155 PowerSubstationP.
- Concept needed: PowerSubstationP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl power.

## Radio mast (`radio_tower`)

- Depicts: a communication tower, a lattice mast.
- Register: SO_0600 TowerCommunicationNonObstructionP.
- Concept needed: TowerCommunicationNonObstructionP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl transmitter.

## Ruins (`ruin`)

- Depicts: ruins, a broken outline.
- Register: SO_0102 RuinsNonObstructionP.
- Concept needed: RuinsNonObstructionP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl Ruin.

## Solar power plant (`solar`)

- Depicts: the register's generic point symbol, a ring and a dot; the register publishes no dedicated solar-panel glyph.
- Register: SO_0001 SolarPanelP.
- Concept needed: SolarPanelP.
- Grade: generic.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl powersolar.
- Shared drawing with: tourism, wave.

## Smokestack (`stack`)

- Depicts: a smokestack, a tall chimney.
- Register: SO_0156 SmokestackP.
- Concept needed: SmokestackP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl Stack.

## Tourist attraction (`tourism`)

- Depicts: the register's generic point symbol, a ring and a dot; the register publishes no dedicated attraction glyph.
- Register: SO_0001 AmusementParkAttractionP.
- Concept needed: AmusementParkAttractionP.
- Grade: generic.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl Tourism.
- Shared drawing with: solar, wave.

## Viewing tower (`view_tower`)

- Depicts: another tower, a generic tower.
- Register: SO_0079 TowerOtherP.
- Concept needed: TowerOtherP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl ViewTower.

## Water tower (`water_tower`)

- Depicts: a water tower, a tank on a stem.
- Register: SO_0015 TowerWaterTowerP.
- Concept needed: TowerWaterTowerP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl watertower.

## Wave power plant (`wave`)

- Depicts: the register's generic point symbol, a ring and a dot; the register publishes no wave-power glyph.
- Register: SO_0001.
- Concept needed: none published.
- Grade: substituted.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl powerwave.
- Shared drawing with: solar, tourism.

## Wind turbine (`wind`)

- Depicts: a wind turbine, a rotor on a mast.
- Register: SO_0157 WindTurbineP.
- Concept needed: WindTurbineP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl powerwind.

## Bus stop (`bus_stop`)

- Depicts: a checkpoint, a barrier gate.
- Register: SO_0153 CheckpointP.
- Concept needed: none published.
- Grade: substituted.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl busstop.
- Shared drawing with: border_crossing.

## Quay (`quay`)

- Depicts: a quay, a pier symbol.
- Register: none.
- Concept needed: none published.
- Grade: non_register.
- Geometry: n/a.
- Licence: public domain, US Government work.
- Used for: RscMapControl quay.

## Border crossing (`border_crossing`)

- Depicts: a checkpoint, a barrier gate.
- Register: SO_0153 CheckpointP.
- Concept needed: GateBorderCrossingP.
- Grade: substituted.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: CfgLocationTypes BorderCrossing.
- Shared drawing with: bus_stop.

## Bunker (`bunker`)

- Depicts: a surface bunker, a low structure.
- Register: SO_0330 SurfaceBunkerP.
- Concept needed: SurfaceBunkerP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl Bunker.

## Fortress (`fortress`)

- Depicts: a fortification, a walled outline.
- Register: SO_0099 FortificationP.
- Concept needed: FortificationP.
- Grade: specific.
- Geometry: Point.
- Licence: CC BY 2.0, (C) DGIWG, attribution required.
- Used for: RscMapControl Fortress.
