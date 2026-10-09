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
