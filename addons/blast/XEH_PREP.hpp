// XEH_PREP.hpp - function prep includes for aee_blast
//
// Split out of its source addon (ADR-032).  Every kernel is PREP'd from
// functions/; callers use FUNC.

PREPS(blast,calculateBlastInjury);
PREPS(blast,calculateBlastOverpressure);

// Crater kernels (issue #19): Hopkinson-Cranz scaling, the WES / TM 5-855-1
// crater size and shape model, and the terrain grid for setTerrainHeight.
PREPS(crater,calculateCrater);
PREPS(crater,craterShape);
PREPS(crater,craterTerrainPoints);
PREPS(crater,hopkinsonCranzScale);
