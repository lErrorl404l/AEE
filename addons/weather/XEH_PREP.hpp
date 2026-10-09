// XEH_PREP.hpp - function prep includes for aee_weather
//
// Climatology, biome, the weather-coupled terrain kernels and the severe
// weather warnings.  Every kernel is PREP'd from its category folder.

PREPS(warnings,calculateBiologicalAmbient);
PREP(calculateScentDispersion);
PREPS(terrain,calculateCropState);
PREPS(terrain,calculateDustSuppression);
PREPS(terrain,calculateUrbanHeatIsland);
PREPS(terrain,calculateMicroclimate);
PREPS(terrain,calculateWaterInfluence);
PREPS(biome,updateSeasonalFoliage);
PREPS(terrain,calculateConcealment);
PREPS(terrain,getCoastDistance);
PREPS(climatology,calculateLunarIllumination);
PREPS(warnings,calculateSevereWeather);
PREPS(warnings,calculateBlowingSnowVisibility);
PREPS(warnings,calculateDustVisibility);
PREPS(terrain,calculateSnowAccumulation);
PREPS(climatology,calculateSpaceWeather);
PREPS(climatology,calculateQNH);
PREPS(climatology,calculateFogBaseAltitude);
PREPS(biome,classifyBiome);
PREPS(biome,getBiome);
PREPS(biome,getBiomeAtPosition);
PREPS(biome,getSmoothedBiome);
PREPS(biome,getBiomeName);
PREPS(climatology,getClimateNormals);
PREPS(climatology,getLatitudeClimate);
PREPS(biome,scanTerrainSignals);
PREPS(biome,updateBiomePosition);
PREPS(terrain,updateSoundPropagation);
