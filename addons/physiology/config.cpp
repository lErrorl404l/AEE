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

/*
CfgEquipment - helmet/vest equipment properties (issue #119).

Per-family values verified from manufacturer specs + army manuals
(Gentex ACH, Crye CPC, BA CIRAS, IOTV/SPCS manuals, Gentex HGU-55,
NIJ standards).  Any item WITHOUT an entry falls back to the
classname-family classification in fnc_getEquipmentProperties.

  weight - kg (real issue weights)
  armor  - NIJ protection level 0..3 (0 none, 1 IIA, 2 IIIA, 3 III+plates)
  nirReflectance - NIR reflectance 0..1 (camo 0.35-0.45, black 0.05-0.20)
  clo    - insulation added to the uniform (BA adds ~0.20-0.26 total)
*/
class CfgEquipment {
    // ─── Plate carriers: NIJ III (ESAPI plates) ──────────────────────────
    class V_PlateCarrier1_blk {
        weight = 5.5;
        armor = 3;
        nirReflectance = 0.35;
        clo = 0.18;
    };
    class V_PlateCarrier2_blk: V_PlateCarrier1_blk {};
    class V_PlateCarrier2_blkI: V_PlateCarrier1_blk {};
    class V_PlateCarrierGL_blk: V_PlateCarrier1_blk {};
    class V_PlateCarrierH_CTRG: V_PlateCarrier1_blk {};

    // ─── Tactical vests: NIJ IIA ─────────────────────────────────────────
    class V_TacVest_blk {
        weight = 2.0;
        armor = 2;
        nirReflectance = 0.38;
        clo = 0.10;
    };

    // ─── Light rigs: no ballistic ────────────────────────────────────────
    class V_BandollierB_blk {
        weight = 1.0;
        armor = 1;
        nirReflectance = 0.40;
        clo = 0.06;
    };
    class V_Chestrig_blk: V_BandollierB_blk {
        weight = 1.2;
        clo = 0.07;
    };
    class V_HarnessO_brn: V_BandollierB_blk {
        weight = 1.5;
        clo = 0.08;
    };

    // ─── Diving rigs ─────────────────────────────────────────────────────
    class V_RebreatherB {
        weight = 3.0;
        armor = 0;
        nirReflectance = 0.20;
        clo = 0.15;
    };

    // ─── Ballistic helmets: NIJ IIIA ─────────────────────────────────────
    class H_HelmetB {
        weight = 1.5;
        armor = 2;
        nirReflectance = 0.40;
        clo = 0.07;
    };
    class H_HelmetB_light: H_HelmetB {};
    class H_HelmetB_plain_blk: H_HelmetB {};
    class H_HelmetO_ocamo: H_HelmetB {};
    class H_HelmetIA_net: H_HelmetB {};

    // ─── Aircrew: IIA, no ballistic core ─────────────────────────────────
    class H_CrewHelmetHeli_B {
        weight = 1.0;
        armor = 1;
        nirReflectance = 0.40;
        clo = 0.05;
    };
    class H_PilotHelmetFighter_B {
        weight = 1.1;
        armor = 1;
        nirReflectance = 0.45;
        clo = 0.15;
    };

    // ─── Light headwear: no ballistic ────────────────────────────────────
    class H_Watchcap_blk {
        weight = 0.1;
        armor = 0;
        nirReflectance = 0.30;
        clo = 0.12;
    };
    class H_Booniehat_grn {
        weight = 0.2;
        armor = 0;
        nirReflectance = 0.40;
        clo = 0.05;
    };
    class H_Bandanna_khk {
        weight = 0.1;
        armor = 0;
        nirReflectance = 0.35;
        clo = 0.04;
    };
    class H_Cap_oli {
        weight = 0.15;
        armor = 0;
        nirReflectance = 0.38;
        clo = 0.05;
    };
    class H_Beret_grn {
        weight = 0.15;
        armor = 0;
        nirReflectance = 0.35;
        clo = 0.04;
    };

    // ─── Backpacks: no ballistic, camo NIR ───────────────────────────────
    // Empty weights (the load command adds the contents).
    class B_AssaultPack_blk {
        weight = 3.0;
        armor = 0;
        nirReflectance = 0.40;
        clo = 0.08;
    };
    class B_Kitbag_rgr: B_AssaultPack_blk {
        weight = 4.0;
        clo = 0.10;
    };
    class B_Carryall_oli: B_AssaultPack_blk {
        weight = 6.0;
        clo = 0.12;
    };
    class B_TacticalPack_oli: B_AssaultPack_blk {
        weight = 3.5;
    };
    class B_Bergen_hex_F: B_AssaultPack_blk {
        weight = 5.0;
        clo = 0.12;
    };
    class B_FieldPack_oli: B_AssaultPack_blk {
        weight = 4.0;
    };
};
