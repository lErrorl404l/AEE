// XEH_PREP.hpp - function prep includes for aee_hydrology
//
// River level, rainfall-runoff and the thermal-refraction water term.  Split
// out of aee_mobility (ADR-032).  Every kernel is PREP'd from functions/;
// callers use FUNC.

PREP(calculateRiverWaterLevel);
PREP(calculateThermalRefraction);
PREPS(hydrology,calculateBaseflow);
PREPS(hydrology,calculateDepressionStorage);
PREPS(hydrology,calculateGreenAmptInfiltration);
PREPS(hydrology,calculateRunoffSCS);
PREPS(hydrology,routeRunoffD8);
