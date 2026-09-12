/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "aee_main",
            "aee_core",
            "cba_main",
            "cba_xeh"
        };
        author = AUTHOR;
        authors[] = AUTHORS;
        url = URL;
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"

// ─── CfgSurfaces dust overrides per terrain type ─────────────────────
// Adapted from ANZACSAS Helicopter Dust (1537745369).
// Arma reads the dust value to scale ambient surface particles.
// AEE maps these values by biome: arid biomes get higher dust,
// wet/forested biomes get lower dust. These are passive overrides —
// they tune the engine's built-in surface particle system.
class CfgSurfaces {
    class Default;

    // Desert / sand surfaces — high dust (arid biomes)
    class GdtDesert: Default { dust = 0.08; };
    class GdtSand: Default { dust = 0.1; };
    class GdtDunes: Default { dust = 0.12; };

    // Grassland — moderate dust (dry grass)
    class GdtGrassShort: Default { dust = 0.02; };
    class GdtGrassTall: Default { dust = 0.02; };
    class GdtGrassLong: Default { dust = 0.02; };
    class GdtGrassLand: Default { dust = 0.03; };
    class GdtPrairie: Default { dust = 0.04; };

    // Forest — low dust (vegetation binds soil)
    class GdtForest: Default { dust = 0.01; };
    class GdtConiferous: Default { dust = 0.01; };
    class GdtRainForest: Default { dust = 0.005; };
    class GdtJungle: Default { dust = 0.005; };

    // Hard surfaces — minimal dust
    class GdtConcrete: Default { dust = 0.03; };
    class GdtAsphalt: Default { dust = 0.02; };
    class GdtStratisConcrete: Default { dust = 0.03; };
    class GdtStratisGreenGrass: Default { dust = 0.02; };

    // Snow / ice — near-zero dust (moisture binds particles)
    class GdtSnow: Default { dust = 0.005; };
    class GdtTundra: Default { dust = 0.01; };
    class GdtIce: Default { dust = 0.001; };
    class GdtGlacier: Default { dust = 0.001; };

    // Wet surfaces — suppressed dust
    class GdtSwamp: Default { dust = 0.003; };
    class GdtMarsh: Default { dust = 0.003; };

    // Rocky / mountain — moderate (loose scree)
    class GdtRock: Default { dust = 0.03; };
    class GdtMountain: Default { dust = 0.02; };

    // Cultivated land — moderate (tilled soil)
    class GdtField: Default { dust = 0.05; };
    class GdtCrop: Default { dust = 0.04; };
    class GdtVineyard: Default { dust = 0.03; };
    class GdtOrchard: Default { dust = 0.02; };
};
