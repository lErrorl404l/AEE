/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
Per-optic thermal configuration (aee-thermal-realism T11).

This file is GENERATED. The generator tools/validation/gen_thermal_optics.py
writes it from the device corpus data/device/catalogue/thermal_devices.json
and the authored class bindings data/device/class_bindings.json. Do not edit
it by hand. Edit the corpus or the bindings and regenerate it.

VERIFIED ENGINE PATH. The per-optic thermal keys live at
  CfgWeapons >> <optic class> >> ItemInfo >> OpticsModes >> <mode>
in the vanilla derap /tmp/opencode/ti-research/v2/weapons_f/acc/config.cpp
(optic_tws line 1026, optic_Nightstalker line 986, optic_tws_mg line 1069).
The vanilla optic_tws mode TWS carries thermalMode[] = {0,1}. The vanilla
config carries no thermalNoise[] and no thermalResolution[]. The shapes below
follow the same flat number-array interface.

INTERFACE EVIDENCE, NO VALUE COPIED. The surveyed mods A3RO (3341786920)
and AH-64D (1351428303) place thermalMode[], thermalNoise[] and
thermalResolution[] on the optic class or on the OpticsModes mode. Their
arrays are interface shapes only. No mod value is copied.

BINDINGS. The class bindings are AUTHORED. Each binding links one real Arma
optic class to one corpus device. The mapping and its identity evidence are
in data/device/class_bindings.json.

DERIVATIONS. Every emitted number has one recorded source:
  thermalMode[]       DECLARED. The engine-minimum palette pair, WHOT (0)
                      and BHOT (1), per the thermal mode table in
                      docs/wiki/research/engine-thermal-mechanisms.md. It is
                      not a corpus figure. The corpus holds no palette.
  thermalNoise[]      DERIVED. The detector NETD in C, from the corpus field
                      netd_c.
  thermalResolution[] DERIVED. The detector pixel array, from the corpus
                      fields resolution_x and resolution_y.

FAIL CLOSED. A binding with no corpus row, or with no held netd_c,
resolution_x or resolution_y, emits no declaration. The withheld bindings
are named below. No value is invented.

WITHHELD BINDINGS
  - none
*/
class CfgWeapons {
    // External parents: the engine defines both.  The re-open below must name
    // them, or the engine clears the optic's inheritance.
    class ItemCore;
    class InventoryOpticsItem_Base_F;
    class optic_Nightstalker: ItemCore {
        class ItemInfo: InventoryOpticsItem_Base_F {
            class OpticsModes {
                class NCTALKEP {
                    thermalMode[] = {0, 1};
                    thermalNoise[] = {0.04};
                    thermalResolution[] = {640, 480};
                };
            };
        };
    };

    class optic_tws: ItemCore {
        class ItemInfo: InventoryOpticsItem_Base_F {
            class OpticsModes {
                class TWS {
                    thermalMode[] = {0, 1};
                    thermalNoise[] = {0.05};
                    thermalResolution[] = {640, 480};
                };
            };
        };
    };

    class optic_tws_mg: ItemCore {
        class ItemInfo: InventoryOpticsItem_Base_F {
            class OpticsModes {
                class TWS {
                    thermalMode[] = {0, 1};
                    thermalNoise[] = {0.05};
                    thermalResolution[] = {640, 480};
                };
            };
        };
    };
};
