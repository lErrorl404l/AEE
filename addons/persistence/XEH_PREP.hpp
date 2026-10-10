// XEH_PREP.hpp - function prep includes for aee_persistence
//
// Ground-state persistence: freeze/thaw, frost, soil moisture, surface
// wetness, ice load, CBRN, fire spread, flash flood and avalanche.

PREPS(warnings,calculateFireSpreadRisk);
PREPS(warnings,calculateAvalancheRisk);
PREPS(terrain,calculateIceLoad);
PREPS(warnings,calculateCBRNPersistence);
PREPS(warnings,getCbrnProtection);
PREPS(warnings,calculateFlashFloodRisk);
PREPS(terrain,calculateFreezeThawCycling);
PREPS(terrain,calculateFrostOnWindscreens);
PREPS(terrain,detectGroundFrost);
PREPS(terrain,calculateSurfaceWetness);
PREPS(terrain,updateSoilMoisture);

// Seismic activity (#27): the ground-motion, liquefaction, landslide,
// damage, shake and terrain-deformation kernels, and their tick consumer.
PREPS(seismic,seismicGroundMotion);
PREPS(seismic,seismicLiquefaction);
PREPS(seismic,seismicLandslide);
PREPS(seismic,seismicDamage);
PREPS(seismic,seismicShake);
PREPS(seismic,seismicTerrainPoints);
PREPS(seismic,calculateSeismicActivity);
