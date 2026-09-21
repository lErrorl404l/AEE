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

/*
CfgClothing - per-uniform clothing properties (issue #119).

Explicit overrides for the known vanilla uniform families.  Values are
the researched constants (ASHRAE 55 / ISO 11079 clo, DLA NIR camo
reflectance, colour-based solar absorptivity).  Any uniform WITHOUT an
entry falls back to the classname-family classification in
fnc_getClothingInsulation - the dynamic pattern that handles modded
uniforms.

  clo          - insulation in clo (1 clo = 0.155 m2K/W)
  alphaSolar   - solar absorptivity 0..1 (colour; black 0.90, white 0.25)
  nirReflectance - NIR reflectance 0..1 (the NVG black-hole effect)
  permeability - fabric permeability 0..1 (wind penetration)
  emissivity   - thermal emissivity 8-14 um (fabric ~0.93)
*/
class CfgClothing {
    // Standard combat uniform (OCP/MTP-style): the NVG-matched baseline.
    class U_B_CombatUniform_mcam {
        clo = 0.75;
        alphaSolar = 0.80;
        nirReflectance = 0.40;
        permeability = 0.35;
        emissivity = 0.93;
    };
    class U_B_CombatUniform_mcam_tshirt: U_B_CombatUniform_mcam {};
    class U_B_CombatUniform_mcam_vest: U_B_CombatUniform_mcam {};
    class U_B_CombatUniform_mcam_worn: U_B_CombatUniform_mcam {};

    // Ghillie: high insulation (traps air), NIR-matched, low permeability.
    class U_B_GhillieSuit {
        clo = 1.20;
        alphaSolar = 0.70;
        nirReflectance = 0.45;
        permeability = 0.30;
        emissivity = 0.93;
    };

    // Wetsuit: high insulation wet, high absorptivity, near-zero wind.
    class U_B_Wetsuit {
        clo = 1.50;
        alphaSolar = 0.85;
        nirReflectance = 0.35;
        permeability = 0.05;
        emissivity = 0.95;
    };

    // Pilot coveralls: light, moderate absorptivity.
    class U_B_PilotCoveralls {
        clo = 0.65;
        alphaSolar = 0.70;
        nirReflectance = 0.45;
        permeability = 0.30;
        emissivity = 0.93;
    };
    class U_B_HeliPilotCoveralls: U_B_PilotCoveralls {};
};
