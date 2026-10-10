// XEH_PREP.hpp - function prep includes for aee_blast
//
// Split out of its source addon (ADR-032).  Every kernel is PREP'd from
// functions/; callers use FUNC.

PREPS(blast,calculateBlastInjury);
PREPS(blast,calculateBlastOverpressure);
PREPS(blast,calculateBlastThrow);
PREPS(blast,applyDeathMomentum);
PREPS(blast,applyCorpsePhysics);

// Explosion fragmentation physics (issue #107).
PREPS(fragmentation,calculateFragmentAngularFraction);
PREPS(fragmentation,calculateFragmentDecay);
PREPS(fragmentation,calculateFragmentDensity);
PREPS(fragmentation,calculateFragmentHitChance);
PREPS(fragmentation,calculateFragmentLethality);
PREPS(fragmentation,calculateGurneyVelocity);
PREPS(fragmentation,calculateMottCount);
PREPS(fragmentation,calculateMottMass);
PREPS(fragmentation,getFragmentationWarhead);

// Crater kernels (issue #19): Hopkinson-Cranz scaling, the WES / TM 5-855-1
// crater size and shape model, and the terrain grid for setTerrainHeight.
PREPS(crater,calculateCrater);
PREPS(crater,craterShape);
PREPS(crater,craterTerrainPoints);
PREPS(crater,hopkinsonCranzScale);
