// XEH_PREP.hpp - function prep includes for aee_blast
//
// Split out of its source addon (ADR-032).  Every kernel is PREP'd from
// functions/; callers use FUNC.

PREPS(blast,calculateBlastInjury);
PREPS(blast,calculateBlastOverpressure);
PREPS(blast,calculateBlastThrow);
PREPS(blast,applyDeathMomentum);
PREPS(blast,applyCorpsePhysics);
