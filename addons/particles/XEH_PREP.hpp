// XEH_PREP.hpp - function prep includes for aee_particles
//
// Split out of its source addon (ADR-032).  Every kernel is PREP'd from
// functions/; callers use FUNC.

PREPS(particle,calculateDownwash);
PREPS(particle,heatHazeAlpha);
PREPS(particle,heatHazeSize);
PREPS(particle,kickupParams);
PREPS(particle,particleAllocate);
PREPS(particle,particleEffectConfig);
PREPS(particle,particleEmission);
PREPS(particle,particleMaterial);
PREPS(particle,particlePipeline);
PREPS(particle,particlePipelineEmit);
PREPS(particle,particleState);
PREPS(particle,registerParticleSource);
PREPS(particle,renderSupersonicTrace);
PREPS(particle,surfaceMaterial);
PREPS(particle,surfaceSample);
PREPS(particle,weatherParticleAlpha);
PREP(dumpState);
