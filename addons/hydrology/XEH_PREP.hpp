// XEH_PREP.hpp - function prep includes for aee_hydrology
//
// River level, rainfall-runoff and the thermal-refraction water term.  Split
// out of aee_mobility (ADR-032).  Every kernel is PREP'd from functions/;
// callers use FUNC.

PREP(calculateRiverWaterLevel);
PREP(calculateThermalRefraction);
PREP(calculateErosion);
PREPS(hydrology,calculateBaseflow);
PREPS(hydrology,calculateDepressionStorage);
PREPS(hydrology,calculateGreenAmptInfiltration);
PREPS(hydrology,calculateRunoffSCS);
PREPS(hydrology,calculateSpringFlow);
PREPS(hydrology,calculateWaterTableDepth);
PREPS(hydrology,getAquiferProperties);
PREPS(hydrology,routeRunoffD8);
PREPS(erosion,calculateKineticEnergy);
PREPS(erosion,calculateErosivityIndex);
PREPS(erosion,calculateSoilErodibility);
PREPS(erosion,calculateSlopeLengthGradient);
PREPS(erosion,calculateCoverFactor);
PREPS(erosion,calculateSoilLoss);
PREPS(erosion,calculateSedimentYield);
PREPS(erosion,calculateSedimentDeposition);
PREPS(erosion,calculateErosionDepth);
