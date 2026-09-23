// fx function compilation (issue #203 grouping; #149 additions).
// Groups are alphabetical; names within a group are alphabetical.

// ── blast ─────────────────────────────────────────────────────────────────
PREPS(blast,calculateBlastInjury);
PREPS(blast,calculateBlastOverpressure);

// ── particle ──────────────────────────────────────────────────────────────
PREPS(particle,calculateDownwash);
PREPS(particle,kickupParams);
PREPS(particle,particleAllocate);
PREPS(particle,particleEffectConfig);
PREPS(particle,particleEmission);
PREPS(particle,particleMaterial);
PREPS(particle,particlePipeline);
PREPS(particle,particlePipelineEmit);
PREPS(particle,particleState);
PREPS(particle,registerParticleSource);
PREPS(particle,surfaceMaterial);
PREPS(particle,surfaceSample);

// ── weather ───────────────────────────────────────────────────────────────
PREPS(weather,applyAtmosphericDust);
PREPS(weather,applyBreathCondensation);
PREPS(weather,applyFootfallDust);
PREPS(weather,applyRotorWash);
PREPS(weather,applyRainSurfaceDrops);
PREPS(weather,applyRainVehicleSound);
PREPS(weather,applyVehicleDust);
PREPS(weather,applyWeatherParticles);
PREPS(weather,applyWindNoise);
PREPS(weather,calculateLightningStrikeEffects);
PREPS(weather,triggerLightning);
PREPS(weather,triggerSevereWeatherFX);
