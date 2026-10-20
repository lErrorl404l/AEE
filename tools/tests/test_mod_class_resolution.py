#!/usr/bin/env python3
"""Modded-class resolution locks (vehicle and aircraft identity ladders).

The runtime matchers name a game class from the class text and the display
name. The vehicle matcher has one more layer: where the text names nothing,
the ENGINE ancestry answers, from the config parent chain. A modded class
resolves when its own text carries a designation the catalogue entry
publishes - the exact mapped class, a curated alias, a keyword or the closest
layer - or, on the vehicle side, when it is a descendant of an ancestor the
table names AND its own text names what that ancestor's entry is. It resolves
to nothing when neither holds, and that is the correct answer: the matcher
never guesses.

This module locks the modded gaps that were closed and the modded classes
that stay open on purpose. Each closed class names the catalogue entry it
must resolve to; each inherited one also names the config chain that puts it
there. Each open class is listed with the reason it stays open, so a later
change that closes or breaks one shows up here.

The vehicle table closes seventy-seven modded classes: twenty-one by their
own text (the RHS M1237 RG-33L "Plus" and M1239 SOCOM AUV families, the PHAN
Typhoon truck, the four Tahoe marks, the RHS Object 681, the Jbad Caterpillar
789D, and the five the counterpart research closed), one more by the
identity-only entry its text names (the Project OPFOR Nissan pickup), thirty
by the family-word work of 2026-10-20 (the twelve M113A3 classes, the sixteen
M1240A1 classes, the HEMTT A4 and the BTR-70 base, each closed because a
family word left the specific mark's alias set), eight by the family rung of
2026-10-20, and seventeen by engine ancestry - the seven Arma 3 Offroad
re-uses and the ten Project OPFOR KAMAZ trucks, whose chain reaches the Zamak
that the wiki ties to the KamAZ-4310 family.

The family rung answers a class whose text names a family and no mark. The
family entry is identity-only and sits in its own table, so the family word is
never a mark's keyword: that is what closed the two Land Rover base classes,
the two RG-33 marks and the FMTV base class. It also let the T-72MS and the
two M1238A1 marks answer on their own terms once `t72` and `rg33` left the
marks that were claiming them. Five modded classes still tie above the rung:
the two T-72B3 marks against `t72b`, the two T-90SA marks against `t90s`, and
the RG-33 4x4 SOCOM base against the configuration word `4x4`. A tie is
final, so the family rung is never reached for them.

An inherited closure says the class IS that ancestor in the engine. It does
not say the mod's own paint names a different real vehicle, because where the
class text names a different article the rung refuses, and the ladder then
continues to the family rung rather than treating the refusal as an answer.
`LOP_Nissan_PKM_base` closes on the maker alias, which names no other class.
The base game's fictional M4 Scorcher also stays open, and it is not a modded
gap.

The aircraft table closed forty-four: the base game's fictional AR-2 Darter,
whose display name the wiki ties to the Parrot AR.Drone 2.0, and forty-three
modded classes closed by the family-word work of 2026-10-20. Nine family
entries carry the corpus: `uh1_family`, `uh60_family`, `hh60_family`,
`ah1_family`, `mi24_family`, `su25_family`, `ch53_family`, `ch47_family` and
`mig29_family`. Each owns one designation, so no mark row carries it, and a
class that names its own mark now answers at the keyword layer. Forty-two
modded classes still stay open: ten F/A-181 loadout configurations of an
Arma 3 fictional type, eight ArmaFPV Crocus drones that no published source
designates, and twenty-four that tie at a layer above the family rung.

The KamAZ-4310 entry publishes the real truck and binds the Arma 3 Zamak
classes through the wiki's own statement ("Zamak is simply Kamaz spelt
backwards, which is the name of the company that designs the real-life
"KamAZ-4310" family of trucks that the Zamak is based on"). The Project OPFOR
KAMAZ trucks carry no 4310 token, so no text layer may name them: an alias on
the maker word would also capture the RHS KamAZ-5350, which is a different
truck. The chain separates them, because the 5350 does not descend from the
Zamak.

Run: python3 -m unittest tools.tests.test_mod_class_resolution -v
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

VEHICLE_MATCH = REPO / "addons" / "vehicles" / "functions" / "fnc_getVehicleMatch.sqf"
AIRCRAFT_MATCH = REPO / "addons" / "flight" / "functions" / "fnc_getAircraftMatch.sqf"
MUNITION_MATCH = (
    REPO / "addons" / "blast" / "functions" / "munition" / "fnc_getMunitionMatch.sqf"
)

# The generator that emits the vehicle ladder, the coverage measurement, and
# the corpus validator. The family rung is specified by the runtime file and
# the two Python mirrors must answer the same, so the locks compare them.
from tools import report_match_coverage as report  # noqa: E402
from tools.validation import (  # noqa: E402
    gen_vehicle_data,
    validate_aircraft_data,
    validate_vehicle_data,
    vehicle_catalogue,
)

# The shortest alias or keyword the closest layer accepts, as the runtime does.
SCAN_MIN = 3

# Modded classes that must resolve, with the catalogue entry that names them.
# The class and the display name are the ones the installed content declares.
CLOSED_VEHICLE_CASES: tuple[tuple[str, str, str], ...] = (
    ("rhsusf_M1237_M2_usarmy_d", "M1237 (O-GPK/M2)", "bae_systems_rg_33l_6x6"),
    ("rhsusf_M1237_M2_usarmy_wd", "M1237 (O-GPK/M2)", "bae_systems_rg_33l_6x6"),
    ("rhsusf_M1237_MK19_usarmy_d", "M1237 (O-GPK/Mk19)", "bae_systems_rg_33l_6x6"),
    ("rhsusf_M1237_MK19_usarmy_wd", "M1237 (O-GPK/Mk19)", "bae_systems_rg_33l_6x6"),
    (
        "rhsusf_M1239_socom_d",
        "M1239 AUV",
        "bae_systems_rg_33l_socom_armored_utility_vehicle_auv",
    ),
    (
        "rhsusf_M1239_M2_socom_d",
        "M1239 AUV (CROWS/M2)",
        "bae_systems_rg_33l_socom_armored_utility_vehicle_auv",
    ),
    (
        "rhsusf_M1239_MK19_socom_d",
        "M1239 AUV (CROWS/Mk19)",
        "bae_systems_rg_33l_socom_armored_utility_vehicle_auv",
    ),
    (
        "rhsusf_M1239_M2_Deploy_socom_d",
        "M1239 AUV Deploy (CROWS/M2)",
        "bae_systems_rg_33l_socom_armored_utility_vehicle_auv",
    ),
    (
        "rhsusf_M1239_MK19_Deploy_socom_d",
        "M1239 AUV Deploy (CROWS/Mk19)",
        "bae_systems_rg_33l_socom_armored_utility_vehicle_auv",
    ),
    ("CBRN_Typhoon_Truck", "Typhoon Truck", "kamaz_63968_typhoon_k"),
    ("tahoe_08", "Chevrolet Tahoe", "chevrolet_tahoe_gmt900"),
    ("tahoe_ltz_08", "Chevrolet Tahoe VIP", "chevrolet_tahoe_gmt900"),
    ("tahoe_UNM", "Chevrolet Tahoe Security", "chevrolet_tahoe_gmt900"),
    ("tahoe_LUMI", "Chevrolet Tahoe'08 Lumi Edition", "chevrolet_tahoe_gmt900"),
    ("rhs_Ob_681_2", "Obyekt-681-2", "object_681"),
    ("Jbad_cat_dumper", "Cat 789D", "caterpillar_789d"),
    # Closed by the 2026-10-20 counterpart research: each display name now
    # carries a maker or a model the wiki names, so the ladder resolves it.
    ("LOP_SUV_base", "SUV", "bmw_x6_concept"),
    ("LOP_Hatchback_base", "Hatchback", "hyundai_iblue_concept"),
    ("CBRN_Containment_Vehicle", "Van (Utility)", "mercedes_benz_sprinter"),
    ("Gendarmerie_CBRN_Vehicle", "Van (Utility)", "mercedes_benz_sprinter"),
    ("RHS_Civ_Truck_02_transport_F", "Zamak Transport", "kamaz_4310"),
    # Closed by the 2026-10-20 identity-only capture: the class names its
    # entry from its own text, so it never reaches the ancestry rung.
    ("LOP_Nissan_PKM_base", "Nissan (PKM)", "nissan_pickup_technical"),
    # Closed by the 2026-10-20 family-word work: the family term left the
    # alias or keyword set of the specific mark that shared it, so the mark
    # the class text names is the only candidate left at that layer.
    ("LOP_AA_M113_C", "M113A3 M2 (Camo)", "m113a3"),
    ("LOP_AA_M113_D", "M113A3 M2 (Desert)", "m113a3"),
    ("LOP_AA_M113_W", "M113A3 M2 (Woodland)", "m113a3"),
    ("LOP_M113_base", "M113A3 M2", "m113a3"),
    ("rhsusf_m113_usarmy", "M113A3 (M2)", "m113a3"),
    ("rhsusf_m113_usarmy_M240", "M113A3 (M240)", "m113a3"),
    ("rhsusf_m113_usarmy_M2_90", "M113A3 (M2/Early)", "m113a3"),
    ("rhsusf_m113_usarmy_MK19", "M113A3 (Mk19)", "m113a3"),
    ("rhsusf_m113_usarmy_MK19_90", "M113A3 (Mk19/Early)", "m113a3"),
    ("rhsusf_m113_usarmy_medical", "M113A3 (MEV)", "m113a3"),
    ("rhsusf_m113_usarmy_supply", "M113A3 (Ammo)", "m113a3"),
    ("rhsusf_m113_usarmy_unarmed", "M113A3 (Unarmed)", "m113a3"),
    ("rhsusf_m1240a1_usarmy_d", "M1240", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_usarmy_wd", "M1240", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_usmc_d", "M1240", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_usmc_wd", "M1240", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_m2_usarmy_d", "M1240 (O-GPK/M2)", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_m2_usarmy_wd", "M1240 (O-GPK/M2)", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_m2_usmc_d", "M1240 (O-GPK/M2)", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_m2_usmc_wd", "M1240 (O-GPK/M2)", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_mk19_usarmy_d", "M1240 (O-GPK/Mk19)", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_mk19_usarmy_wd", "M1240 (O-GPK/Mk19)", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_mk19_usmc_d", "M1240 (O-GPK/Mk19)", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_mk19_usmc_wd", "M1240 (O-GPK/Mk19)", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_m240_usarmy_d", "M1240 (O-GPK/M240)", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_m240_usarmy_wd", "M1240 (O-GPK/M240)", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_m240_usmc_d", "M1240 (O-GPK/M240)", "m_atv_m1240a1"),
    ("rhsusf_m1240a1_m240_usmc_wd", "M1240 (O-GPK/M240)", "m_atv_m1240a1"),
    ("rhsusf_HEMTT_A4_base", "M977A4", "m977a4"),
    ("rhs_btr_base", "BTR-70", "btr_70"),
)

# Modded classes that stay open on the vehicle side, with the reason.
# A class whose chain passes StaticWeapon is an emplacement, not a vehicle:
# the same kind rule gen_vehicle_bindings.py applies ("a ground class is a
# LandVehicle that is not a StaticWeapon"). A catalogue of real vehicles is
# never scored against a tripod mount, a MANPADS post or a towed howitzer.
VEHICLE_EMPLACEMENT_CASES: tuple[str, ...] = (
    "rhs_m2staticmg_base",
    "RHS_M2StaticMG_MiniTripod_base",
    "RHS_MK19_TriPod_base",
    "RHS_Stinger_AA_pod_Base",
    "RHS_M119_base",
)

# The modded classes the inherited rung closes: the class, its display, the
# config chain from the class to the nearest ancestor the table maps by
# classname, and the entry that ancestor names. A closure here says the class
# IS that ancestor in the engine, and that its own text names what the
# ancestor's entry is. It does not say the mod's paint names another article.
INHERITED_VEHICLE_CASES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "CBRN_Offroad",
        "Offroad",
        ("Offroad_01_civil_base_F", "Offroad_01_unarmed_base_F"),
        "offroad_q7_l200_composite",
    ),
    (
        "LOP_Offroad_base",
        "Offroad",
        ("Offroad_01_civil_base_F", "Offroad_01_unarmed_base_F"),
        "offroad_q7_l200_composite",
    ),
    (
        "LOP_AA_Offroad",
        "ANA Offroad",
        ("LOP_Offroad_base", "Offroad_01_civil_base_F", "Offroad_01_unarmed_base_F"),
        "offroad_q7_l200_composite",
    ),
    (
        "LOP_AA_Offroad_Police",
        "ANP Offroad",
        ("LOP_Offroad_base", "Offroad_01_civil_base_F", "Offroad_01_unarmed_base_F"),
        "offroad_q7_l200_composite",
    ),
    (
        "LOP_Offroad_M2_base",
        "Offroad (M2)",
        ("Offroad_01_armed_base_F", "Offroad_01_military_base_F", "Offroad_01_base_F"),
        "offroad_q7_l200_composite",
    ),
    (
        "LOP_AA_Offroad_M2",
        "ANA Offroad (M2)",
        (
            "LOP_Offroad_M2_base",
            "Offroad_01_armed_base_F",
            "Offroad_01_military_base_F",
            "Offroad_01_base_F",
        ),
        "offroad_q7_l200_composite",
    ),
    (
        "LOP_AA_Offroad_M2_Police",
        "ANP Offroad (M2)",
        (
            "LOP_Offroad_M2_base",
            "Offroad_01_armed_base_F",
            "Offroad_01_military_base_F",
            "Offroad_01_base_F",
        ),
        "offroad_q7_l200_composite",
    ),
    # The ten Project OPFOR KAMAZ retextures. Their chain reaches the Zamak,
    # which the catalogue maps to the KamAZ-4310 on the wiki's own statement,
    # and their own text carries the maker word "kamaz", so the rung answers.
    ("LOP_KAMAZ_fuel_base", "KamAZ (fuel)", ("O_Truck_02_fuel_F",), "kamaz_4310"),
    (
        "LOP_UKR_KAMAZ_Fuel",
        "KAMAZ (fuel)",
        ("LOP_KAMAZ_fuel_base", "O_Truck_02_fuel_F"),
        "kamaz_4310",
    ),
    (
        "LOP_CDF_KAMAZ_Fuel",
        "KAMAZ (fuel)",
        ("LOP_KAMAZ_fuel_base", "O_Truck_02_fuel_F"),
        "kamaz_4310",
    ),
    (
        "LOP_IRAN_KAMAZ_Fuel",
        "KAMAZ (fuel)",
        ("LOP_KAMAZ_fuel_base", "O_Truck_02_fuel_F"),
        "kamaz_4310",
    ),
    (
        "LOP_SYR_KAMAZ_Fuel",
        "KAMAZ (fuel)",
        ("LOP_KAMAZ_fuel_base", "O_Truck_02_fuel_F"),
        "kamaz_4310",
    ),
    ("LOP_KAMAZ_cov_base", "KAMAZ (covered)", ("O_Truck_02_covered_F",), "kamaz_4310"),
    ("LOP_KAMAZ_trans_base", "KAMAZ (open)", ("O_Truck_02_transport_F",), "kamaz_4310"),
    ("LOP_KAMAZ_rep_base", "KAMAZ (repair)", ("O_Truck_02_box_F",), "kamaz_4310"),
    ("LOP_KAMAZ_med_base", "Kamaz Medical", ("O_Truck_02_medical_F",), "kamaz_4310"),
    ("LOP_KAMAZ_ammo_base", "KAMAZ (ammo)", ("O_Truck_02_Ammo_F",), "kamaz_4310"),
)

# The base-game Offroad classes are mapped classes, so the exact layer names
# them and the rung is never reached. They are locked here to prove the rule
# is about the ENGINE ancestry and not about who declares the class.
EXACT_BASE_CASES: tuple[tuple[str, str, str], ...] = (
    ("Offroad_01_repair_base_F", "Offroad (Repair)", "offroad_q7_l200_composite"),
    ("Offroad_01_AT_base_F", "Offroad (AT)", "offroad_q7_l200_composite"),
    ("C_Offroad_01_repair_F", "Offroad (Services)", "offroad_q7_l200_composite"),
)

# The chain the identity-only closure walks. It ends at the engine's own Car
# class, the nearest ancestor the table maps, so a lock can prove the closure
# is the class text and not the ancestry.
IDENTITY_ONLY_VEHICLE_CASES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "LOP_Nissan_PKM_base",
        "Nissan (PKM)",
        ("PO_Pickup_PK_base", "Car_F", "Car"),
        "nissan_pickup_technical",
    ),
)

# The modded classes that stay open, with the reason. Every one of them ties
# at a layer above the family rung, and a tie is final: the runtime returns an
# empty array, so the family rung is never reached.
_T72_TAIL = ("rhs_a3t72tank_base", "tank_f", "tank")
_T90_TAIL = (
    "rhs_t90a_tv",
    "rhs_t90_tv",
    "rhs_t72bd_tv",
    "rhs_a3t72tank_base",
    "tank_f",
    "tank",
)
_RG33_TAIL = ("rhsusf_RG33_base", "MRAP_01_base_F", "Car_F", "Car")

VEHICLE_OPEN_CASES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "rhs_t72bd_tv",
        "T-72B3 (obr. 2012g.)",
        _T72_TAIL,
        "the keyword layer ties on t72b3 against the T-72B obr. 1984g. entry, whose canonical name still derives t72b; the family rung cannot answer a tied query",
    ),
    (
        "rhs_t72be_tv",
        "T-72B3 (obr. 2016g.)",
        ("rhs_t72bd_tv", *_T72_TAIL),
        "the keyword layer ties on t72b3 against the T-72B obr. 1984g. entry, whose canonical name still derives t72b; the family rung cannot answer a tied query",
    ),
    (
        "rhs_t90saa_tv",
        "T-90SA (obr. 2004g.)",
        _T90_TAIL,
        "the keyword layer ties on t90s, which both the T-90SA and the T-90SM entries carry from their canonical names; the family owns t90 but cannot answer a tied query",
    ),
    (
        "rhs_t90sab_tv",
        "T-90SA (obr. 2016g.)",
        _T90_TAIL,
        "the keyword layer ties on t90s, which both the T-90SA and the T-90SM entries carry from their canonical names; the family owns t90 but cannot answer a tied query",
    ),
    (
        "rhsusf_RG33_base",
        "RG33 4X4 SOCOM",
        ("MRAP_01_base_F", "Car_F", "Car"),
        "the text names a configuration: 4x4 is a keyword of seven catalogue entries, so the keyword layer ties and the family rung is never reached",
    ),
)

# The modded classes the family rung and the family-word rule closed on
# 2026-10-20. A family entry owns its designation, so no mark row carries it:
# what used to tie now answers, and the family answers where no mark does.
FAMILY_CLOSED_VEHICLE_CASES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "LOP_LandRover_base_02",
        "Land Rover",
        ("PO_LandRover_base_W", "PO_LandRover_base", "Car_F", "Car"),
        "landrover_family",
    ),
    (
        "LOP_LandRover_mg_base",
        "Land Rover (M2)",
        ("PO_LandRover_Base_MG", "PO_LandRover_base", "Car_F", "Car"),
        "landrover_family",
    ),
    (
        "rhssaf_army_t72s",
        "T-72MS",
        ("rhs_t72bd_tv", *_T72_TAIL),
        "t_72ms",
    ),
    (
        "rhsusf_fmtv_base",
        "FMTV",
        ("Truck_01_base_F", "Truck_F", "Car_F", "Car"),
        "fmtv_family",
    ),
    (
        "rhsusf_RG33_CROWS_base",
        "M1238A1 ASV (CROWS/M2)",
        _RG33_TAIL,
        "bae_systems_rg_33_4x4_socom_m1238",
    ),
    (
        "rhsusf_RG33_CROWSMK19_base",
        "M1238A1 ASV (CROWS/Mk19)",
        ("rhsusf_RG33_CROWS_base", *_RG33_TAIL),
        "bae_systems_rg_33_4x4_socom_m1238",
    ),
    (
        "rhsusf_rg33_d",
        "RG-33",
        _RG33_TAIL,
        "rg33_family",
    ),
    (
        "rhsusf_rg33_m2_d",
        "RG-33 (M2)",
        ("rhsusf_RG33_CROWS_base", *_RG33_TAIL),
        "rg33_family",
    ),
)

# Modded aircraft classes that stay open, grouped by the reason they stay
# open. A tie at any layer above the family rung is final, so the family rung
# is never reached for them.
#
# The F/A-181 configurations name an Arma 3 fictional type and a weapon
# loadout: "10x GBU-12" is not a designation, and the type is nobody's real
# aircraft. The shared configuration words ("cas", "bomber", "heavy") are
# keywords of several catalogue entries, so the keyword layer ties.
AIRCRAFT_OPEN_CASES: tuple[tuple[str, str], ...] = (
    # Arma 3 fiction, and a loadout rather than a designation.
    (
        "B_Plane_Fighter_01_CASModule_HeavyBomber_2_F",
        "F/A-181 Black Wasp II (10x GBU-12)",
    ),
    ("B_Plane_Fighter_01_CASModule_HeavyBomber_F", "F/A-181 Black Wasp II (8x GBU-12)"),
    (
        "B_Plane_Fighter_01_CASModule_HeavyNapalm_2_F",
        "F/A-181 Black Wasp II (8x MK77 Napalm)",
    ),
    (
        "B_Plane_Fighter_01_CASModule_HeavyNapalm_F",
        "F/A-181 Black Wasp II (6x MK77 Napalm)",
    ),
    (
        "B_Plane_Fighter_01_CASModule_MediumBomber_2_F",
        "F/A-181 Black Wasp II (6x GBU-12)",
    ),
    (
        "B_Plane_Fighter_01_CASModule_MediumBomber_F",
        "F/A-181 Black Wasp II (4x GBU-12)",
    ),
    (
        "B_Plane_Fighter_01_CASModule_MediumNapalm_2_F",
        "F/A-181 Black Wasp II (4x MK77 Napalm)",
    ),
    (
        "B_Plane_Fighter_01_CASModule_MediumNapalm_F",
        "F/A-181 Black Wasp II (3x MK77 Napalm)",
    ),
    ("B_Plane_Fighter_01_CASModule_Napalm_F", "FA-181 Black Wasp II (2x MK77 Napalm)"),
    ("B_Plane_Fighter_01_Napalm_F", "FA-181 Black Wasp II - MK77"),
    # No published source designates a Crocus FPV drone, so a row would have
    # to invent a designation.
    ("ARMAFPV_Crocus_AP_Base", "Crocus AP"),
    ("ARMAFPV_Crocus_AT_Base", "Crocus AT"),
    ("B_Crocus_AP_TI", "Crocus AP TI"),
    ("B_Crocus_AT_TI", "Crocus AT TI"),
    ("I_Crocus_AP_TI", "Crocus AP TI"),
    ("I_Crocus_AT_TI", "Crocus AT TI"),
    ("O_Crocus_AP_TI", "Crocus AP TI"),
    ("O_Crocus_AT_TI", "Crocus AT TI"),
    # A shared name is a curated alias of two marks, so the alias layer ties
    # before any keyword is read: "falcon" names two F-16 marks, "hornet" two
    # F/A-18 marks, "merlin" two AW101 marks, "pavehawk" two H-60 marks and
    # "black hawk" two UH-60 marks.
    ("FIR_ECM_Dummy_1", "F-16C Fighting Falcon"),
    ("FIR_ECM_Dummy_2", "F/A-18F Super Hornet"),
    ("CBRN_Mohawk", "Merlin"),
    ("vtx_HH60", "HH-60G/M Pavehawk"),
    ("vtx_H60_base", "UH-60M Blackhawk"),
    # The AH-64 marks share "ah64", and "ah6" is a substring of every AH-64
    # query, so the keyword layer always ties. A family entry owning "ah64"
    # would leave only "ah6" and answer the AH-6 Little Bird, which is why no
    # AH-64 family entry exists.
    ("RHS_AH64_base", "AH-64"),
    ("RHS_AH64D", "AH-64D"),
    ("RHS_AH64D_AA", "AH-64D (AA)"),
    ("RHS_AH64D_CS", "AH-64D (Close-Support)"),
    ("RHS_AH64D_GS", "AH-64D (Ground-Suppression)"),
    ("RHS_AH64DGrey", "AH-64D (OIF Grey)"),
    ("fza_ah64d_b1", "AH-64D BLOCK I"),
    ("fza_ah64d_b2e", "DEPRECATED"),
    # The Mi-8MTV-3 mark is not held. "mi8" names the Mi-8T and Mi-8AMTSh,
    # and the Mi-17 entry derives "mi8m" from its published mi-8mt alias, so
    # the keyword layer ties. A Mi-8 family entry would leave "mi8m" alone
    # and answer the Mi-17 for a Mi-8MTV-3, which is the wrong airframe.
    ("rhs_mi8mtv3_base", "Mi-8MTV-3"),
    ("RHS_Mi8MTV3_vvs", "Mi-8MTV-3"),
    ("RHS_Mi8mtv3_Cargo_vvs", "Mi-8MTV-3 (Cargo)"),
    ("RHS_Mi8MTV3_FAB_vvs", "Mi-8MTV-3 (FAB)"),
    ("RHS_Mi8MTV3_UPK23_vvs", "Mi-8MTV-3 (UPK)"),
    ("rhs_mi8mtv3_heavy_base", "Mi-8MTV-3 (Heavy)"),
    # A role word is a keyword of several entries: "cas" of the A-10 and the
    # Su-25, "gunship" of the Ka-50, Mi-24P and Mi-28. The keyword layer ties.
    ("RHS_Mi24P_CAS_VVS_Base", "Mi-24P (CAS)"),
    ("RHS_Su25SM_CAS_vvs", "Su-25 (CAS)"),
    ("RHS_Su25SM_CAS_vvsc", "Su-25 (CAS)"),
    ("rhs_uh1h_hidf_gunship", "UH-1H Gunship"),
    # "mh60" is shared by four MH-60 marks, and "mh6" is a substring of
    # "mh60m", so a MH-60 family entry would answer the MH-6M.
    ("121_soar_hibyrd_slick", "[SOAR] Hibyrd's MH-60M"),
)

# The modded aircraft classes that resolve. The drone_base_F row is the base
# game's fictional quadcopter; the wiki names the Parrot AR.Drone 2.0 for it
# at grade "resemblance", which is enough for the keyword layer. The other
# forty-three closed by the family-word work: each names its own mark, and the
# family entry now owns the shared designation the marks used to compete for.
CLOSED_AIRCRAFT_CASES: tuple[tuple[str, str, str], ...] = (
    ("drone_base_F", "AR-2 Darter", "parrot_ar_drone_2"),
    ("RHS_AH1Z", "AH-1Z", "ah1z_viper"),
    ("RHS_AH1Z_CS", "AH-1Z (Close-Support)", "ah1z_viper"),
    ("RHS_AH1Z_GS", "AH-1Z (Ground-Suppression)", "ah1z_viper"),
    ("RHS_AH1Z_base", "AH-1Z", "ah1z_viper"),
    ("RHS_AH1Z_wd_CS", "AH-1Z (Close-Support)", "ah1z_viper"),
    ("RHS_AH1Z_wd_GS", "AH-1Z (Ground-Suppression)", "ah1z_viper"),
    ("RHS_CH_47F_base", "CH-47F", "ch47f_chinook"),
    ("RHS_CH_47F_cargo_base", "CH-47F (Cargo)", "ch47f_chinook"),
    ("RHS_CH_47F_light", "CH-47F (D)", "ch47f_chinook"),
    ("RHS_Mi24D_Base", "Mi-24D", "mi24d_hind_d"),
    ("RHS_Mi24D_Early_Base", "Mi-24D (early)", "mi24d_hind_d"),
    ("RHS_Mi24P_AT_VVS_Base", "Mi-24P (AT)", "mi24p_hind_f"),
    ("RHS_Mi24V_Base", "Mi-24V", "mi24v_hind_e"),
    ("RHS_Mi24_base", "Mi-24P", "mi24p_hind_f"),
    ("RHS_Su25SM_Cluster_vvs", "Su-25 (Cluster)", "su25sm_frogfoot"),
    ("RHS_Su25SM_Cluster_vvsc", "Su-25 (Cluster)", "su25sm_frogfoot"),
    ("RHS_Su25SM_KH29_vvs", "Su-25 (KH29)", "su25sm_frogfoot"),
    ("RHS_Su25SM_KH29_vvsc", "Su-25 (KH29)", "su25sm_frogfoot"),
    ("RHS_Su25SM_vvs", "Su-25", "su25sm_frogfoot"),
    ("RHS_UH1Y_FFAR", "UH-1Y", "uh1y_venom"),
    ("RHS_UH1Y_GS", "UH-1Y (Ground-Suppression)", "uh1y_venom"),
    ("RHS_UH1Y_UNARMED", "UH-1Y (Unarmed)", "uh1y_venom"),
    ("RHS_UH1Y_base", "UH-1Y (MG)", "uh1y_venom"),
    ("RHS_UH60M", "UH-60M", "uh60m_black_hawk"),
    ("RHS_UH60M2", "UH-60M (Unarmed)", "uh60m_black_hawk"),
    ("RHS_UH60M_ESSS", "UH-60M (ESSS)", "uh60m_black_hawk"),
    ("RHS_UH60M_ESSS2", "UH-60M (EWS)", "uh60m_black_hawk"),
    ("RHS_UH60M_MEV", "UH-60M MEV (ESSS)", "uh60m_black_hawk"),
    ("RHS_UH60M_MEV2", "UH-60M MEV", "uh60m_black_hawk"),
    ("RHS_UH60M_base", "UH-60", "uh60m_black_hawk"),
    ("rhs_mig29s_base", "MiG-29S", "mig29s_fulcrum_c"),
    ("rhs_mig29sm_base", "MiG-29SM", "mig29s_fulcrum_c"),
    ("rhs_uh1h_base", "UH1H", "uh1h_iroquois"),
    ("rhs_uh1h_hidf", "UH-1H", "uh1h_iroquois"),
    ("rhs_uh1h_hidf_unarmed", "UH-1H Unarmed", "uh1h_iroquois"),
    ("rhs_uh1h_idap", "UH-1H", "uh1h_iroquois"),
    ("rhs_uh1h_un", "UH-1H", "uh1h_iroquois"),
    ("rhsusf_CH53E_USMC", "CH-53E", "ch53e_super_stallion"),
    ("rhsusf_CH53E_USMC_GAU21", "CH-53E (GAU-21)", "ch53e_super_stallion"),
    ("rhsusf_CH53e_USMC_D_cargo", "CH-53E (Cargo)", "ch53e_super_stallion"),
    ("rhsusf_CH53e_USMC_cargo", "CH-53E (Cargo)", "ch53e_super_stallion"),
    ("vtx_UH60M_MEDEVAC", "HH-60M MEDEVAC", "uh60m_black_hawk"),
    ("vtx_UH60M_SLICK", "UH-60M Slick", "uh60m_black_hawk"),
)


def fold(text: str) -> str:
    """Fold an identity to its lookup key, as the runtime normalise does."""
    return "".join(char for char in text.lower() if char.isascii() and char.isalnum())


def ancestor_blob(row: dict[str, object]) -> str:
    """The identity text one entry is published under, folded."""
    parts = [
        str(row["id"]),
        *[str(x) for x in row["aliases"]],
        *[str(x) for x in row["keywords"]],
    ]
    return fold("|".join(parts))


def claims(row: dict[str, object], tokens: set[str]) -> bool:
    """True when a class token names something the entry is identified by."""
    blob = ancestor_blob(row)
    return any(len(token) >= SCAN_MIN and token in blob for token in tokens)


def named_ancestor(
    table: list[dict[str, object]], name: str
) -> dict[str, object] | None:
    """The one entry that maps this ancestor classname, or None.

    The mapped-class test only: a mod may rewrite any ancestor's displayName,
    so the classname is the evidence and the text is not.
    """
    key = fold(name)
    hit = [row for row in table if key in row["classes"]]
    return hit[0] if len(hit) == 1 else None


FAMILY_MARKER = "private _families = ["


def _tables(path: Path) -> tuple[str, str]:
    """Split a matcher file into its mark table text and its family text."""
    text = path.read_text(encoding="utf-8")
    if FAMILY_MARKER not in text:
        return text, ""
    head, _, rest = text.partition(FAMILY_MARKER)
    family, _, _ = rest.partition("\n];")
    return head, family


def _parse(text: str) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith('["'):
            continue
        parts = re.findall(r'"([^"]*)"', stripped)
        if len(parts) <= 6:
            continue
        out.append(
            {
                "id": parts[0],
                "classes": [x for x in parts[4].split("|") if x],
                "aliases": [x for x in parts[5].split("|") if x],
                "keywords": [x for x in parts[6].split("|") if x],
            }
        )
    return out


def rows(path: Path) -> list[dict[str, object]]:
    """Parse the mark table of one matcher file."""
    return _parse(_tables(path)[0])


def family_rows(path: Path) -> list[dict[str, object]]:
    """Parse the family table of one matcher file."""
    return _parse(_tables(path)[1])


def resolve(
    table: list[dict[str, object]],
    name: str,
    display: str = "",
    chain: tuple[str, ...] | None = None,
    families: list[dict[str, object]] | None = None,
) -> str | None:
    """Mirror the runtime ladder: exact, alias, keyword, closest, inherited,
    family.

    Layer one reads the CLASS alone, the later layers read the identity text
    the engine holds (class name, raw display name and its localisation). The
    inherited layer needs the engine class tree, so the caller passes the
    config chain, nearest ancestor first. Without a chain it cannot run. The
    family layer reads the separate family table, and exactly one match
    answers.
    """
    identity = name + " " + display
    key = fold(name)
    query = fold(identity)
    tokens = {fold(token) for token in re.split(r"[ _\-.]+", identity) if fold(token)}
    hit = [row for row in table if key in row["classes"]]
    if len(hit) == 1:
        return str(hit[0]["id"])
    if len(hit) > 1:
        return None
    hit = [row for row in table if tokens & set(row["aliases"])]
    if len(hit) == 1:
        return str(hit[0]["id"])
    if len(hit) > 1:
        return None
    hit = [
        row
        for row in table
        if any(len(word) >= SCAN_MIN and word in query for word in row["keywords"])
    ]
    if len(hit) == 1:
        return str(hit[0]["id"])
    if len(hit) > 1:
        return None
    best: dict[str, object] | None = None
    best_score = runner_up = best_count = best_name = 0
    tie = False
    for row in table:
        terms = row["aliases"] + row["keywords"]
        score = sum(
            len(word) * (2 if any(char.isdigit() for char in word) else 1)
            for word in terms
            if len(word) >= SCAN_MIN and word in query
        )
        if score < SCAN_MIN:
            continue
        count = len(terms)
        longest = max((len(word) for word in terms), default=0)
        if score > best_score:
            runner_up, best_score, best = best_score, score, row
            best_count, best_name, tie = count, longest, False
        elif score == best_score:
            if count < best_count:
                best, best_count, best_name, tie = row, count, longest, False
            elif count == best_count:
                if longest < best_name:
                    best, best_name, tie = row, longest, False
                elif longest == best_name:
                    tie = True
        if score < best_score:
            runner_up = max(runner_up, score)
    if best is not None and not tie and best_score > runner_up:
        return str(best["id"])
    if chain is not None:
        # Layer 6: inherited. The nearest ancestor the table names answers,
        # and only for a class whose own text names that entry. An ancestor
        # the text does not name is not walked past, and it is not an answer
        # either: the ladder continues to the family rung, as the runtime
        # does when the inherited row stays empty.
        tokens = {
            fold(token) for token in re.split(r"[ _\-.]+", identity) if fold(token)
        }
        for ancestor in chain:
            found = named_ancestor(table, ancestor)
            if found is None:
                continue
            if claims(found, tokens):
                return str(found["id"])
            break
    # Layer 7: family. A family row names a family and no mark, and exactly
    # one row matching a designation answers.
    hit = [
        row
        for row in (families or [])
        if any(len(word) >= SCAN_MIN and word in query for word in row["keywords"])
    ]
    return str(hit[0]["id"]) if len(hit) == 1 else None


class ClosedModdedVehicleTest(unittest.TestCase):
    """Every closed modded vehicle class resolves to the entry that names it."""

    table: list[dict[str, object]] = []
    families: list[dict[str, object]] = []

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = rows(VEHICLE_MATCH)
        cls.families = family_rows(VEHICLE_MATCH)

    def test_the_closed_modded_vehicle_class_count_is_fifty_two(self) -> None:
        # Twenty-two by the earlier work, thirty by the family-word work.
        self.assertEqual(52, len(CLOSED_VEHICLE_CASES))

    def test_the_family_work_closed_eight_more(self) -> None:
        self.assertEqual(8, len(FAMILY_CLOSED_VEHICLE_CASES))

    def test_each_family_closure_resolves_to_its_entry(self) -> None:
        for name, display, chain, want in FAMILY_CLOSED_VEHICLE_CASES:
            with self.subTest(game_class=name):
                self.assertEqual(
                    want, resolve(self.table, name, display, families=self.families)
                )
                # The chain is not the answer: these names come from the text.
                self.assertEqual(
                    want,
                    resolve(self.table, name, display, chain, families=self.families),
                )

    def test_each_closed_modded_vehicle_class_resolves(self) -> None:
        for name, display, want in CLOSED_VEHICLE_CASES:
            with self.subTest(game_class=name):
                self.assertEqual(want, resolve(self.table, name, display))

    def test_the_closed_modded_vehicle_class_count_is_sixty_nine(self) -> None:
        # Fifty-two by their own text and seventeen by engine ancestry.
        self.assertEqual(
            52 + 17, len(CLOSED_VEHICLE_CASES) + len(INHERITED_VEHICLE_CASES)
        )

    def test_each_inherited_class_is_a_descendant_of_the_ancestor_that_answers(
        self,
    ) -> None:
        # The chain is the claim. Its head is the class, its tail the nearest
        # ancestor the table names, and the entry is that ancestor's.
        for name, display, chain, want in INHERITED_VEHICLE_CASES:
            with self.subTest(game_class=name):
                self.assertGreater(len(chain), 0)
                self.assertEqual(want, resolve(self.table, name, display, chain))
                self.assertNotEqual(
                    want,
                    resolve(self.table, name, display),
                    "the class must have no identity of its own",
                )

    def test_a_mapped_base_class_is_named_by_the_exact_layer(self) -> None:
        for name, display, want in EXACT_BASE_CASES:
            with self.subTest(game_class=name):
                self.assertEqual(want, resolve(self.table, name, display))

    def test_an_inherited_class_needs_its_chain(self) -> None:
        for name, display, _chain, _want in INHERITED_VEHICLE_CASES:
            with self.subTest(game_class=name):
                self.assertIsNone(resolve(self.table, name, display))

    def test_ancestry_alone_names_nothing(self) -> None:
        # A class descended from a mapped class, whose own text names that
        # entry nowhere, is a different article. The rung refuses it, so a
        # short chain can never become a guess.
        self.assertIsNone(
            resolve(
                self.table,
                "Mod_Anonymous_Body",
                "",
                ("Offroad_01_base_F",),
            )
        )

    def test_the_rg33l_plus_alias_names_one_entry(self) -> None:
        # M1237 is the uparmoured RG-33L "Plus" designation the held WarWheels
        # index states, so it must index one entry and no other.
        owners = [row["id"] for row in self.table if "m1237" in row["aliases"]]
        self.assertEqual(["bae_systems_rg_33l_6x6"], owners)

    def test_the_m1239_alias_names_one_entry(self) -> None:
        owners = [row["id"] for row in self.table if "m1239" in row["aliases"]]
        self.assertEqual(
            ["bae_systems_rg_33l_socom_armored_utility_vehicle_auv"], owners
        )

    def test_the_tahoe_alias_names_one_entry(self) -> None:
        owners = [row["id"] for row in self.table if "tahoe" in row["aliases"]]
        self.assertEqual(["chevrolet_tahoe_gmt900"], owners)


class OpenModdedVehicleTest(unittest.TestCase):
    """Every open modded vehicle class stays open, for a stated reason."""

    table: list[dict[str, object]] = []
    families: list[dict[str, object]] = []

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = rows(VEHICLE_MATCH)
        cls.families = family_rows(VEHICLE_MATCH)

    def test_a_static_weapon_emplacement_is_never_named_as_a_vehicle(self) -> None:
        for name in VEHICLE_EMPLACEMENT_CASES:
            with self.subTest(game_class=name):
                self.assertIsNone(resolve(self.table, name))

    def gap_classes(self) -> dict:
        body = (REPO / "data/coverage/modded_gaps_vehicles.txt").read_text(
            encoding="utf-8"
        )
        out = {}
        for line in body.splitlines():
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            out[fields[0]] = fields[1]
        return out

    def test_every_class_in_the_gap_list_is_open(self) -> None:
        # The gap list is the measured worklist. If the matcher can name a
        # class the list calls open, the list is lying about the engine.
        for name, display in self.gap_classes().items():
            with self.subTest(game_class=name):
                self.assertIsNone(
                    resolve(self.table, name, display, families=self.families)
                )

    def test_every_documented_open_case_is_in_the_gap_list(self) -> None:
        listed = self.gap_classes()
        for name, display, _chain, _reason in VEHICLE_OPEN_CASES:
            with self.subTest(game_class=name):
                self.assertIn(name, listed)
                self.assertEqual(display, listed[name])

    def test_every_open_class_states_a_one_line_reason(self) -> None:
        for name, _display, _chain, reason in VEHICLE_OPEN_CASES:
            with self.subTest(game_class=name):
                self.assertTrue(reason.strip())
                self.assertNotIn("\n", reason)

    def test_an_open_class_is_refused_with_and_without_its_chain(self) -> None:
        # Open means the rung looked and refused, not that the chain is short:
        # these classes have a nearest named ancestor, and it is another
        # article.
        for name, display, chain, _reason in VEHICLE_OPEN_CASES:
            with self.subTest(game_class=name):
                self.assertIsNone(
                    resolve(self.table, name, display, families=self.families)
                )
                self.assertIsNone(
                    resolve(self.table, name, display, chain, families=self.families)
                )


class IdentityOnlyVehicleEntryTest(unittest.TestCase):
    """The two identity-only entries name a vehicle and hold no figure.

    Both exist because the class text names an article the ancestry does not.
    The Nissan closes on the maker alias. The FMTV entry names the family but
    advertises no match term, because every term that would reach its class
    also reaches another one, so that class stays open. The lock holds the
    entry shape as well as both outcomes: no figure, no invented model
    designation, no M-number, and no term that captures a class which already
    resolves elsewhere.
    """

    table: list[dict[str, object]] = []

    # The four M-number classes whose own name carries "fmtv". They resolved
    # to their own entries before the family entry existed, and they must
    # still do so after it.
    M_NUMBER_CASES: tuple[tuple[str, str, str], ...] = (
        (
            "rhsusf_M1078A1R_SOV_M2_D_fmtv_socom",
            "M1078A1R SOV (M2)",
            "m1078a1r_socom_sov",
        ),
        (
            "rhsusf_M1078A1R_SOV_M2_WD_fmtv_socom",
            "M1078A1R SOV (M2)",
            "m1078a1r_socom_sov",
        ),
        (
            "rhsusf_M1084A1R_SOV_M2_D_fmtv_socom",
            "M1084A1R SOV (M2)",
            "m1084a1r_socom_sov",
        ),
        (
            "rhsusf_M1084A1R_SOV_M2_WD_fmtv_socom",
            "M1084A1R SOV (M2)",
            "m1084a1r_socom_sov",
        ),
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = rows(VEHICLE_MATCH)

    def entry(self, name: str) -> dict[str, object]:
        capture = json.loads(
            (REPO / "data/vehicle/catalogue" / name).read_text(encoding="utf-8")
        )
        self.assertEqual(1, len(capture["entries"]))
        return capture["entries"][0]

    def test_each_entry_is_identity_only_and_holds_no_figure(self) -> None:
        for name in ("nissan_pickup_technical.json", "fmtv_family.json"):
            with self.subTest(capture=name):
                entry = self.entry(name)
                self.assertIs(True, entry["identity_only"])
                self.assertEqual({}, entry["values"])
                self.assertIs(False, entry["runtime_ready"])
                self.assertEqual("", entry["class_token"])

    def test_the_nissan_entry_asserts_the_maker_and_no_model(self) -> None:
        entry = self.entry("nissan_pickup_technical.json")
        self.assertEqual("Nissan", entry["maker"])
        self.assertEqual(["nissan"], entry["aliases"])
        self.assertNotIn("pkm", entry["aliases"])
        identity = fold(
            " ".join(str(entry[key]) for key in ("canonical_name", "model", "variant"))
        )
        for invented in ("d21", "navara", "hardbody"):
            self.assertNotIn(invented, identity)

    def test_the_nissan_class_resolves_from_its_own_text(self) -> None:
        name, display, _chain, want = IDENTITY_ONLY_VEHICLE_CASES[0]
        self.assertEqual(want, resolve(self.table, name, display))
        self.assertNotEqual(
            "honda_civic_6gen_sedan", resolve(self.table, name, display)
        )

    def test_the_family_entry_claims_no_m_number(self) -> None:
        entry = self.entry("fmtv_family.json")
        identity = fold(
            " ".join(
                [str(entry[key]) for key in ("canonical_name", "model", "variant")]
                + [str(x) for x in entry["aliases"]]
                + [str(x) for x in entry["keywords"]]
            )
        )
        self.assertIsNone(re.search(r"m10\d\d", identity))

    def test_the_family_entry_sits_in_the_family_table_alone(self) -> None:
        # A family row names the family and no mark, so it is separated from
        # the mark table. There it would tie the four SOV classes; here it
        # answers the base class and touches nothing else.
        self.assertNotIn("fmtv_family", [r["id"] for r in self.table])
        family = [r for r in family_rows(VEHICLE_MATCH) if r["id"] == "fmtv_family"]
        self.assertEqual(1, len(family))
        self.assertEqual(["fmtv"], family[0]["keywords"])
        self.assertEqual([], family[0]["aliases"])
        self.assertEqual([], family[0]["classes"])
        self.assertEqual(
            "fmtv_family",
            resolve(
                self.table,
                "rhsusf_fmtv_base",
                "FMTV",
                families=family_rows(VEHICLE_MATCH),
            ),
        )

    def test_each_m_number_class_still_resolves_to_its_own_entry(self) -> None:
        for name, display, want in self.M_NUMBER_CASES:
            with self.subTest(game_class=name):
                self.assertEqual(want, resolve(self.table, name, display))

    def test_the_family_alias_would_capture_the_m_number_classes(self) -> None:
        # An alias is matched by equality, so fmtv as an alias of a family
        # row in the MARK table answers the classes whose own name carries
        # the token and ties the rest, which the strict mirror reads as no
        # answer. That is why the family row must stay out of the mark table.
        entry = self.entry("fmtv_family.json")
        fixed = [dict(r) for r in self.table]
        fixed.append(
            {
                "id": entry["catalogue_id"],
                "classes": [],
                "aliases": ["fmtv"],
                "keywords": [],
            }
        )
        for name, display, want in self.M_NUMBER_CASES:
            with self.subTest(game_class=name):
                self.assertNotEqual(want, resolve(fixed, name, display))
        self.assertIsNone(resolve(fixed, "rhsusf_M1078A1P2_fmtv_usarmy", "M1078A1P2"))

    def test_the_family_keyword_would_tie_the_sov_classes(self) -> None:
        # A keyword is matched by substring, so fmtv in the MARK table meets
        # the SOV classes' own keyword and the layer yields two candidates.
        # The runtime returns nothing from a tied layer, so they stop
        # resolving. The separate family table avoids that.
        entry = self.entry("fmtv_family.json")
        fixed = [dict(r) for r in self.table]
        fixed.append(
            {
                "id": entry["catalogue_id"],
                "classes": [],
                "aliases": [],
                "keywords": ["fmtv"],
            }
        )
        for name, display, _want in self.M_NUMBER_CASES:
            with self.subTest(game_class=name):
                self.assertIsNone(resolve(fixed, name, display))


class Kamaz4310EntryTest(unittest.TestCase):
    """The KamAZ-4310 entry publishes the truck and binds the Zamak classes.

    The wiki states the relation: "Zamak is simply Kamaz spelt backwards ...
    the real-life "KamAZ-4310" family of trucks that the Zamak is based on".
    That statement carries the Arma 3 Zamak classes to the entry, and through
    the Zamak it carries the Project OPFOR KAMAZ retextures, because they are
    that body in another paint. It does not carry them by text: no retexture
    states the model, and a "kamaz" alias would also capture the RHS
    KamAZ-5350 classes, which is a false answer, so the maker word stays out
    of the entry's terms and the chain is what answers.
    """

    table: list[dict[str, object]] = []

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = rows(VEHICLE_MATCH)

    def test_the_entry_holds_only_sourced_values(self) -> None:
        capture = json.loads(
            (REPO / "data/vehicle/catalogue/kamaz_4310.json").read_text(
                encoding="utf-8"
            )
        )
        entries = [e for e in capture["entries"] if e["catalogue_id"] == "kamaz_4310"]
        self.assertEqual(1, len(entries))
        values = entries[0]["values"]
        self.assertTrue(values)
        for field, held in values.items():
            with self.subTest(field=field):
                for key in ("unit", "source", "locator", "state", "grade"):
                    self.assertTrue(held.get(key))

    def test_the_entry_advertises_the_model_and_not_the_maker(self) -> None:
        row = [r for r in self.table if r["id"] == "kamaz_4310"]
        self.assertEqual(1, len(row))
        terms = set(row[0]["aliases"]) | set(row[0]["keywords"])
        self.assertIn("kamaz4310", terms)
        self.assertNotIn("kamaz", terms)
        self.assertNotIn("4310", terms)

    def test_every_kamaz_retexture_reaches_the_entry_only_through_its_chain(
        self,
    ) -> None:
        # The retextures descend from the Zamak in config, and the catalogue
        # maps the Zamak to the KamAZ-4310 on the wiki's statement. The chain
        # is the evidence: no class text carries a model, so the text layers
        # never answer, and the maker word alone would also capture the
        # KamAZ-5350, a different truck.
        seen = 0
        for name, display, chain, want in INHERITED_VEHICLE_CASES:
            if "KAMAZ" not in name.upper():
                continue
            seen += 1
            with self.subTest(game_class=name):
                self.assertEqual("kamaz_4310", want)
                self.assertEqual(
                    "kamaz_4310", resolve(self.table, name, display, chain)
                )
                self.assertIsNone(resolve(self.table, name, display))
        self.assertEqual(10, seen)

    def test_the_rhs_kamaz_5350_still_resolves_to_the_5350(self) -> None:
        self.assertEqual(
            "kamaz_5350_mustang",
            resolve(self.table, "rhs_kamaz5350", "KamAZ-5350 Mustang"),
        )


class OpenModdedAircraftTest(unittest.TestCase):
    """The modded aircraft gaps stay open and the closed set is locked."""

    table: list[dict[str, object]] = []
    families: list[dict[str, object]] = []

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = rows(AIRCRAFT_MATCH)
        cls.families = family_rows(AIRCRAFT_MATCH)

    def test_the_closed_modded_aircraft_class_count_is_forty_four(self) -> None:
        # One by the earlier resemblance research, forty-three by the
        # family-word work of 2026-10-20.
        self.assertEqual(44, len(CLOSED_AIRCRAFT_CASES))

    def test_each_closed_modded_aircraft_class_resolves(self) -> None:
        for name, display, want in CLOSED_AIRCRAFT_CASES:
            with self.subTest(game_class=name):
                self.assertEqual(
                    want, resolve(self.table, name, display, families=self.families)
                )

    def test_every_modded_aircraft_gap_stays_open(self) -> None:
        for name, display in AIRCRAFT_OPEN_CASES:
            with self.subTest(game_class=name):
                self.assertIsNone(
                    resolve(self.table, name, display, families=self.families)
                )

    def test_the_modded_aircraft_gap_count_is_forty_two(self) -> None:
        # Ten F/A-181 loadout configurations, eight Crocus drones, and
        # twenty-four that tie at a layer above the family rung.
        self.assertEqual(42, len(AIRCRAFT_OPEN_CASES))

    def test_no_mark_row_carries_a_family_designation(self) -> None:
        # The family owns its designation. While a mark carried it, every
        # query naming the family tied at the keyword layer and no mark could
        # answer, so the suppression is what makes the closures possible.
        family_words = {str(word) for row in self.families for word in row["keywords"]}
        self.assertTrue(family_words)
        for row in self.table:
            with self.subTest(entry=row["id"]):
                self.assertEqual([], sorted(family_words & set(row["keywords"])))
                self.assertEqual([], sorted(family_words & set(row["aliases"])))

    def test_each_aircraft_family_row_is_identity_only(self) -> None:
        self.assertEqual(9, len(self.families))
        for row in self.families:
            with self.subTest(entry=row["id"]):
                self.assertTrue(str(row["id"]).endswith("_family"))
                self.assertEqual([], row["classes"])
                self.assertEqual([], row["aliases"])
                self.assertGreaterEqual(len(row["keywords"]), 1)
                for word in row["keywords"]:
                    self.assertTrue(
                        word.isalnum() and len(word) >= SCAN_MIN,
                        f"{row['id']} keyword {word} must be a folded designation",
                    )


# A synthetic family row, in the nine-column shape the generator emits: it
# names a family and no mark, so the class, alias and source columns are
# empty and only the keyword column carries a designation.
def family_row(cid: str, keyword: str) -> tuple[object, ...]:
    return (cid, cid, "tracked", "", "", "", keyword, "", [0, 0, 0, 0, 0, "", ""])


def family_table(cid: str, keyword: str) -> dict[str, object]:
    return {"id": cid, "classes": [], "aliases": [], "keywords": [keyword]}


T72_FAMILY_ROW = family_row("t72_family", "t72")


class FamilyRungTest(unittest.TestCase):
    """The family rung: last, exactly one, and never a mark's answer.

    A family entry names a family and no mark. The runtime keeps it in a
    separate `_families` table, so no rung above can reach it, and reads it
    at confidence 7. The two Python mirrors must follow the same rule,
    including the exactly-one test, because the generator harness and the
    coverage measurement are what say a class resolves.
    """

    def test_every_matcher_carries_a_separate_family_table(self) -> None:
        for path in (VEHICLE_MATCH, AIRCRAFT_MATCH, MUNITION_MATCH):
            with self.subTest(matcher=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("private _families = [", text)
                self.assertGreater(
                    text.index("private _families = ["),
                    text.index("private _table = ["),
                )
                self.assertIn("} forEach _families;", text)

    def test_the_family_rung_is_last_and_carries_confidence_seven(self) -> None:
        for path, previous in (
            (VEHICLE_MATCH, '6, "inherited"'),
            (AIRCRAFT_MATCH, '5, "closest"'),
            (MUNITION_MATCH, '4, "closest"'),
        ):
            with self.subTest(matcher=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn('7, "family"] call _result', text)
                self.assertGreater(
                    text.index('7, "family"] call _result'),
                    text.index(previous),
                )

    def test_no_mark_row_carries_a_family_designation(self) -> None:
        # The standing rule: a family word is never an alias or a keyword of
        # one specific mark. The family entry owns it, and the family rung is
        # the only layer that reads it.
        family = family_rows(VEHICLE_MATCH)
        self.assertTrue(family)
        words = {word for row in family for word in row["keywords"]}
        for row in rows(VEHICLE_MATCH):
            with self.subTest(entry=row["id"]):
                self.assertFalse(words & (set(row["aliases"]) | set(row["keywords"])))

        loaded = vehicle_catalogue.load(REPO / "data/vehicle")
        for word in words:
            self.assertNotIn(word, loaded.alias_index)

    def test_the_generator_and_both_mirrors_agree_on_a_family(self) -> None:
        name, display = "rhs_t72bd_tv", "T-72B3 (obr. 2012g.)"
        generated = gen_vehicle_data.match_row(
            [], name, display, families=[T72_FAMILY_ROW]
        )
        self.assertIsNotNone(generated)
        assert generated is not None
        self.assertEqual("t72_family", generated[0])
        self.assertEqual(7, generated[3])
        self.assertEqual("family", generated[4])

        measured = report.matcher([], families=[family_table("t72_family", "t72")])(
            name, display
        )
        self.assertIsNotNone(measured)
        assert measured is not None
        self.assertEqual("t72_family", measured["id"])

        resolved = resolve(
            [], name, display, families=[family_table("t72_family", "t72")]
        )
        self.assertEqual("t72_family", resolved)

    def test_two_families_in_one_query_answer_nothing(self) -> None:
        name = "rg33_t72_test"
        families = [
            family_table("t72_family", "t72"),
            family_table("rg33_family", "rg33"),
        ]
        self.assertIsNone(
            gen_vehicle_data.match_row(
                [],
                name,
                "",
                families=[
                    family_row("t72_family", "t72"),
                    family_row("rg33_family", "rg33"),
                ],
            )
        )
        self.assertIsNone(report.matcher([], families=families)(name, ""))
        self.assertIsNone(resolve([], name, "", families=families))

    def test_no_family_answers_when_none_names_the_class(self) -> None:
        name, display = "rhs_t90saa_tv", "T-90SA (obr. 2004g.)"
        self.assertIsNone(
            gen_vehicle_data.match_row([], name, display, families=[T72_FAMILY_ROW])
        )
        self.assertIsNone(
            report.matcher([], families=[family_table("t72_family", "t72")])(
                name, display
            )
        )
        self.assertIsNone(
            resolve([], name, display, families=[family_table("t72_family", "t72")])
        )

    def test_a_family_never_wins_over_a_mark(self) -> None:
        mark_row = (
            "t72b3",
            "t72b3",
            "tracked",
            "",
            "",
            "",
            "t72b3",
            "",
            [44000, 0, 0, 0, 0, "", ""],
        )
        mark = {"id": "t72b3", "classes": [], "aliases": [], "keywords": ["t72b3"]}
        names = (("rhs_t72bd_tv", "T-72B3 (obr. 2012g.)"),)

        for name, display in names:
            with self.subTest(game_class=name):
                generated = gen_vehicle_data.match_row(
                    [mark_row], name, display, families=[T72_FAMILY_ROW]
                )
                self.assertIsNotNone(generated)
                assert generated is not None
                self.assertEqual("t72b3", generated[0])
                self.assertNotEqual("family", generated[4])

                measured = report.matcher(
                    [mark], families=[family_table("t72_family", "t72")]
                )(name, display)
                self.assertIsNotNone(measured)
                assert measured is not None
                self.assertEqual("t72b3", measured["id"])

                self.assertEqual(
                    "t72b3",
                    resolve(
                        [mark],
                        name,
                        display,
                        families=[family_table("t72_family", "t72")],
                    ),
                )

    def test_a_designation_shorter_than_the_scan_is_ignored(self) -> None:
        self.assertIsNone(
            gen_vehicle_data.match_row(
                [], "rhs_t7_thing", "", families=[family_row("t7_family", "t7")]
            )
        )
        self.assertIsNone(
            report.matcher([], families=[family_table("t7_family", "t7")])(
                "rhs_t7_thing", ""
            )
        )

    def test_the_generator_separates_family_records_from_mark_records(self) -> None:
        record: dict[str, object] = {
            "catalogue_id": "x_family",
            "variant_id": "x_family",
            "canonical_name": "T-72 family",
            "variant": "family designation, no mark claimed",
            "vehicle_type": "tracked",
            "aliases": [],
            "keywords": ["T-72"],
            "values": {},
            "family": True,
        }
        row = gen_vehicle_data.build_family_row(record)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual("t72", row[6])
        self.assertEqual("", row[4])
        self.assertEqual("", row[5])
        self.assertEqual("", row[7])
        self.assertEqual([], [r[0] for r in gen_vehicle_data.build_rows([record])])
        self.assertEqual(
            ["x_family"],
            [r[0] for r in gen_vehicle_data.build_family_rows([record])],
        )
        self.assertIsNone(
            gen_vehicle_data.build_family_row({**record, "family": False})
        )

    def test_the_validator_requires_a_family_to_name_the_family_alone(self) -> None:
        base: dict[str, object] = {
            "catalogue_id": "x_family",
            "canonical_name": "T-72 family",
            "variant": "family designation, no mark claimed",
            "identity_only": True,
            "runtime_ready": False,
            "values": {},
            "aliases": [],
            "keywords": ["t72"],
            "class_token": "",
        }
        errors: list[str] = []
        validate_vehicle_data.validate_family_shape("x_family", base, errors)
        self.assertEqual([], errors)
        for field, bad in (
            ("aliases", ["t72"]),
            ("values", {"operating_weight_kg": {"value": 1}}),
            ("canonical_name", "T-72B3"),
            ("canonical_name", "T-72B3 family"),
            ("canonical_name", "T-72B3 obr. 2012g. family"),
            ("keywords", []),
            ("identity_only", False),
            ("class_token", "Tank_F"),
            ("variant", "obr. 2012g."),
        ):
            with self.subTest(field=field, value=bad):
                errors = []
                validate_vehicle_data.validate_family_shape(
                    "x_family", {**base, field: bad}, errors
                )
                self.assertTrue(errors)

    def test_the_aircraft_validator_applies_the_same_family_rule(self) -> None:
        # The asset is one rule, not one rule per corpus: the aircraft
        # validator calls the shared shape check, so a family entry that would
        # answer for a mark is refused here too.
        entry: dict[str, object] = {
            "catalogue_id": "uh60_family",
            "canonical_name": "UH-60 family",
            "maker": "Sikorsky",
            "model": "UH-60",
            "variant": "family designation, no member claimed",
            "variant_id": "uh60_family",
            "vehicle_type": "rotary_wing",
            "class_token": "",
            "country": "US",
            "era": "modern",
            "aliases": [],
            "keywords": ["uh60"],
            "runtime_ready": False,
            "identity_only": True,
            "family": True,
            "values": {},
        }
        self.assertEqual([], validate_aircraft_data.validate_catalogue([entry], {}))
        for field, bad in (
            ("canonical_name", "UH-60M family"),
            ("keywords", []),
            ("aliases", ["uh60"]),
            ("identity_only", False),
            ("values", {"operating_weight_kg": {"value": 1}}),
            ("variant", "M"),
        ):
            with self.subTest(field=field, value=bad):
                self.assertTrue(
                    validate_aircraft_data.validate_catalogue(
                        [{**entry, field: bad}], {}
                    )
                )
        self.assertTrue(
            validate_aircraft_data.validate_catalogue([{**entry, "family": "yes"}], {})
        )

    def test_the_aircraft_family_entries_pass_the_validator(self) -> None:
        loaded = vehicle_catalogue.load(
            REPO / "data/aircraft", profile=vehicle_catalogue.AIRCRAFT_PROFILE
        )
        families = [entry.to_mapping() for entry in loaded.entries if entry.family]
        self.assertEqual(9, len(families))
        self.assertEqual([], validate_aircraft_data.validate_catalogue(families, {}))
        # A family designation is never one mark's alias: the family owns it,
        # and the family rung alone reads it. A mark's variant id is a variant
        # selector, not a matcher alias, so it is not tested here.
        words = {word for entry in families for word in entry["keywords"]}
        for entry in loaded.entries:
            if entry.family:
                continue
            with self.subTest(entry=entry.catalogue_id):
                self.assertEqual([], sorted(words & set(entry.aliases)))


if __name__ == "__main__":
    unittest.main()
