// XEH_PREP.hpp - function prep includes for aee_blast
//
// Split out of its source addon (ADR-032).  Every kernel is PREP'd from
// functions/; callers use FUNC.

PREPS(blast,calculateBlastInjury);
PREPS(blast,calculateBlastOverpressure);

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
