#!/usr/bin/env python3
"""Build designations_ar.json from the sourced research set.

Twist conversions: 1 turn in N inches = N * 25.4 mm.
Chambering-standard twists used for the difference check:
  5.56x45mm NATO = 177.8, 7.62x51mm NATO = 304.8, .300 BLK = 203.2, 6.5 Creedmoor = 203.0.
"""

import json
from pathlib import Path

SOURCES = [
    {
        "source_id": "tm_9_1005_319_10",
        "title": "Operator's Manual, Rifle 5.56 MM M16A2/M16A3/M16A4 and Carbine M4/M4A1, TM 9-1005-319-10 (US Army)",
        "url": "https://cdn.ar15repository.com/wp-content/uploads/20230809205218/OPERATORS-MANUAL-556-MM-M16A2-M16A3-M16A4-M4-and-M4A1-ARMY-TM-9-1005-319-10.October-1998.pdf",
        "sha256": "aee9f3baabb19b1a25533a202a64140cfa82eb377dc6b5929acbb49f5eb9fc5c",
    },
    {
        "source_id": "fm_23_9",
        "title": "FM 23-9 M16A1 and M16A2 Rifle Marksmanship (US Army)",
        "url": "https://ia801508.us.archive.org/10/items/fm239-1989/M16A1%20%26%20M16A2%20Rifle%20Marksmanship%20FM%2023-9_text.pdf",
        "sha256": "3e3ca9ff8306d6f849edaf5747a86e3aaf5d7d5c5891537c12713f16aaccd9dd",
    },
    {
        "source_id": "tm_9_1005_249_10",
        "title": "Operator's Manual, Rifle 5.56-MM M16 and M16A1, TM 9-1005-249-10 (US Army)",
        "url": "https://cdn.ar15repository.com/wp-content/uploads/20230809205746/TM-9-1005-249-10-February-1985-OPERATORS-MANUAL-556-MM-M16-M16A1.pdf",
        "sha256": "cd223a7acae85a33c07bc5b44d8652964671f0f9f1421c7b0ebe3df5e00ccd26",
    },
    {
        "source_id": "tm_9_1005_309_10",
        "title": "Operator's Manual, Submachine Gun 5.56-MM Port Firing M231, TM 9-1005-309-10 (US Army)",
        "url": "https://archive.org/download/m231-fpw-manuals/5142.pdf",
        "sha256": "3e00929e285502ad015c987fd300cae4d7e88d311637f8815457709d0789cdb2",
    },
    {
        "source_id": "kac_m110",
        "title": "Knight's Armament Company M110 SASS (Export Version) product datasheet",
        "url": "https://www.knightarmco.com/wp-content/uploads/2018/02/m110_exportversion.pdf",
        "sha256": "0f1600b0c3fbf7e8037dc043c9d5ae10a7520c4654137e16732e4ec5136882fe",
    },
    {
        "source_id": "hk416_manual",
        "title": "HK416 Enhanced Carbine & Rifle System Operator's Manual, Heckler & Koch",
        "url": "https://s3.amazonaws.com/hk-manuals/files/Military/HK416/HK416_Operators_Manual.pdf",
        "sha256": "1feece4f94f80b3bb7d09d5ec0ab0ffd07ee58a65f09cbfa35bc79f97dd7e936",
    },
    {
        "source_id": "hk416_a5",
        "title": "HK 416 / HK416-A5 5.56mm x 45 Information Sheet, HK USA",
        "url": "https://hk-usa.com/wp-content/uploads/2023/09/HK416_HK416-A5-Info-Sheet.pdf",
        "sha256": "45eeb25a62602b0ba2fe6f66218e5fb25715d69d483211ecc2e31e331e8f5de0",
    },
    {
        "source_id": "hk417_techdata",
        "title": "HK417 Cal. 7.62 mm x 51 NATO Technical Data, Heckler & Koch",
        "url": "https://s3.amazonaws.com/hk-manuals/files/Military/HK417/HK417_Technical_Data.pdf",
        "sha256": "93587acdeeeea0f5cb21380652509ed40d0ab73eeeb04a11be88cf64e01b506d",
    },
    {
        "source_id": "hk_m27",
        "title": "M27 Infantry Automatic Rifle product sheet, Heckler & Koch",
        "url": "https://mantadefense.com/wp-content/uploads/2017/11/m27_productsheet.pdf",
        "sha256": "7eb6819394573e9fc6630eb43ebd8e9920e39421f68a5596f8a84bb9f6ad2b68",
    },
    {
        "source_id": "coltcanada_c7",
        "title": "Operator's Manual, C7 Family of Combat Weapons, Colt Canada",
        "url": "https://www.coltcanada.com/wp-content/uploads/2021/04/10047s-1-2005-08-17.pdf",
        "sha256": "03a0a5e2cd9ee87e82fc545ad11853a3649847c2ecc83ac3f34cb7f33aef4f4b",
    },
    {
        "source_id": "lmt_mars",
        "title": "LMT Defense MARS-L 5.56 (CQBMLK16-MARS) product page",
        "url": "https://lmtdefense.com/product/mlc/",
        "sha256": None,
    },
    {
        "source_id": "lmt",
        "title": "LMT Defense product line (Lewis Machine & Tool)",
        "url": "https://lmtdefense.com/product/",
        "sha256": None,
    },
    {
        "source_id": "kac_sr25",
        "title": "Knight's Armament Company SR-25 K3 product page",
        "url": "https://www.knightarmco.com/38662/shop/commercial-firearms/sr-25/sr-25-k3",
        "sha256": None,
    },
    {
        "source_id": "kac_sr15",
        "title": "Knight's Armament Company SR-15 KS-1 product page",
        "url": "https://www.knightarmco.com/38630/shop/commercial-firearms/sr-15/sr-15-ks-1",
        "sha256": None,
    },
    {
        "source_id": "fn_scar",
        "title": "FN SCAR family, FN Herstal (defence products)",
        "url": "https://fnherstal.com/en/",
        "sha256": None,
    },
    {
        "source_id": "sig_sauer",
        "title": "SIG SAUER firearms product line",
        "url": "https://www.sigsauer.com/firearms.html",
        "sha256": None,
    },
    {
        "source_id": "sig_m400",
        "title": "SIG SAUER M400 series product page",
        "url": "https://www.sigsauer.com/firearms/rifles-pistols/sig-m400.html",
        "sha256": None,
    },
    {
        "source_id": "sig_mcx_spear",
        "title": "SIG SAUER MCX-SPEAR 6.8x51 product page",
        "url": "https://www.sigsauer.com/mcx-spear-6-8-x-51.html",
        "sha256": None,
    },
    {
        "source_id": "sig_lmg",
        "title": "SIG SAUER SOF Machine Gun Section (XM250 / SIG LMG)",
        "url": "https://www.sigsauer.com/media/sigsauer/resources/SOF_MachineGun_Section.pdf",
        "sha256": None,
    },
    {
        "source_id": "ruger_ar556",
        "title": "Ruger AR-556 rifle specification sheet",
        "url": "https://ruger.com/products/ar556/specSheets/8500.html",
        "sha256": None,
    },
    {
        "source_id": "dd_ddm4",
        "title": "Daniel Defense DDM4 V7 product page",
        "url": "https://danieldefense.com/ddm4-v7.html",
        "sha256": None,
    },
    {
        "source_id": "springfield_saint",
        "title": "Springfield Armory SAINT series rifles",
        "url": "https://www.springfield-armory.com/saint-series/",
        "sha256": None,
    },
    {
        "source_id": "bcm",
        "title": "Bravo Company USA (BCM) 18 inch SS410 rifle upper group",
        "url": "https://bravocompanyusa.com/18-rifle-upper-group/",
        "sha256": None,
    },
    {
        "source_id": "noveske",
        "title": "Noveske Rifleworks rifles collection",
        "url": "https://noveske.com/collections/rifles",
        "sha256": None,
    },
    {
        "source_id": "geissele",
        "title": "Geissele Automatics Super Duty 5.56 rifles",
        "url": "https://geissele.com/firearms/super-duty-5-56/rifles.html",
        "sha256": None,
    },
    {
        "source_id": "aero",
        "title": "Aero Precision AR-15 product line",
        "url": "https://www.aeroprecisionusa.com/ar15",
        "sha256": None,
    },
    {
        "source_id": "windham",
        "title": "Windham Weaponry firearms",
        "url": "https://www.windhamweaponry.com/",
        "sha256": None,
    },
    {
        "source_id": "rra",
        "title": "Rock River Arms firearms",
        "url": "https://www.rockriverarms.com/",
        "sha256": None,
    },
    {
        "source_id": "dpms",
        "title": "DPMS Panther Arms firearms",
        "url": "https://dpmsinc.com/",
        "sha256": None,
    },
    {
        "source_id": "bushmaster",
        "title": "Bushmaster Firearms",
        "url": "https://www.bushmaster.com/",
        "sha256": None,
    },
    {
        "source_id": "barrett",
        "title": "Barrett Firearms product line",
        "url": "https://www.barrett.net/",
        "sha256": None,
    },
    {
        "source_id": "barrett_rec7",
        "title": "Barrett REC7 rifle product page",
        "url": "https://www.barrett.net/products/firearms/rec7",
        "sha256": None,
    },
    {
        "source_id": "barrett_rec10",
        "title": "Barrett REC10 rifle product page",
        "url": "https://www.barrett.net/products/firearms/rec10",
        "sha256": None,
    },
    {
        "source_id": "remington",
        "title": "Remington Arms firearms",
        "url": "https://www.remington.com/",
        "sha256": None,
    },
    {
        "source_id": "armalite",
        "title": "ArmaLite Inc. rifles",
        "url": "https://armalite.com/",
        "sha256": None,
    },
    {
        "source_id": "armalite_manual",
        "title": "Operator's Manual for all AR-10B and M15 Series Rifles, ArmaLite Inc.",
        "url": "https://powderandball.com/manuals/armalite_ar10_and_m15_owners_manual.pdf",
        "sha256": "19bf50060b3239ffe065321832d8be365f459efa14d76edc39bd948375c78f3e",
    },
    {
        "source_id": "hk_g28",
        "title": "G28 Designated Marksman Rifle, Heckler & Koch",
        "url": "https://www.heckler-koch.com/en/Products/Military%20and%20Law%20Enforcement/Designated%20marksman%20rifles/G28",
        "sha256": None,
    },
    {
        "source_id": "hk417_product",
        "title": "HK417 assault rifle, Heckler & Koch",
        "url": "https://www.heckler-koch.com/en/Products/Military%20and%20Law%20Enforcement/Assault%20rifles/HK417",
        "sha256": None,
    },
    {
        "source_id": "colt",
        "title": "Colt's Manufacturing Company firearms",
        "url": "https://www.colt.com/",
        "sha256": None,
    },
    {
        "source_id": "smith_wesson",
        "title": "Smith & Wesson firearms",
        "url": "https://www.smith-wesson.com/",
        "sha256": None,
    },
    {
        "source_id": "firearmsnews_lmt",
        "title": "LM&T Sharpshooter System (L129A1), Firearms News",
        "url": "https://www.firearmsnews.com/editorial/lmt-sharpshooter-system/78393",
        "sha256": None,
    },
    {
        "source_id": "forgotten_weapons_l119a2",
        "title": "L119A2: The New British SOF Rifle, Forgotten Weapons",
        "url": "https://www.forgottenweapons.com/l119a2-the-new-british-sof-rifle/",
        "sha256": None,
    },
    {
        "source_id": "snipercentral_mk12",
        "title": "MK 12 SPR specifications, Sniper Central",
        "url": "https://snipercentral.com/mk12-spr/",
        "sha256": None,
    },
    {
        "source_id": "military_factory",
        "title": "Military Factory small arms reference",
        "url": "https://www.militaryfactory.com/smallarms/",
        "sha256": None,
    },
    {
        "source_id": "coltcanada",
        "title": "Colt Canada product line",
        "url": "https://www.coltcanada.com/",
        "sha256": None,
    },
]

D = []


def add(
    designation, nation, weapon, key, chambering, twist, map_src, twist_src, note=""
):
    D.append(
        {
            "designation": designation,
            "nation": nation,
            "weapon": weapon,
            "weapon_key": key,
            "chambering": chambering,
            "twist_mm": twist,
            "map_source_id": map_src,
            "twist_source_id": twist_src,
            "note": note,
        }
    )


# --- US military M16 / M4 family -------------------------------------------
add(
    "AR-15",
    "United States",
    "ArmaLite/Colt AR-15",
    "ar15",
    "5.56x45mm NATO",
    None,
    "colt",
    None,
    "Colt commercial AR-15; early barrels used 1:14 and 1:12 twists, no twist stated on cited page.",
)
add(
    "AR-15A1",
    "United States",
    "Colt AR-15A1",
    "ar15a1",
    "5.56x45mm NATO",
    None,
    "colt",
    None,
    "Colt commercial model.",
)
add(
    "AR-15A2",
    "United States",
    "Colt AR-15A2",
    "ar15a2",
    "5.56x45mm NATO",
    None,
    "colt",
    None,
    "Colt commercial model.",
)
add(
    "AR-15A3",
    "United States",
    "Colt AR-15A3 Tactical Carbine",
    "ar15a3",
    "5.56x45mm NATO",
    None,
    "colt",
    None,
    "Colt commercial model.",
)
add(
    "AR-15A4",
    "United States",
    "Colt AR-15A4",
    "ar15a4",
    "5.56x45mm NATO",
    None,
    "colt",
    None,
    "Colt commercial model.",
)
add(
    "M16",
    "United States",
    "Colt M16 Rifle",
    "m16",
    "5.56x45mm NATO",
    None,
    "tm_9_1005_249_10",
    None,
    "Manual covers Rifle 5.56-MM M16 and M16A1.",
)
add(
    "XM16E1",
    "United States",
    "Colt XM16E1",
    "xm16e1",
    "5.56x45mm NATO",
    None,
    "tm_9_1005_249_10",
    None,
    "Experimental/pre-production M16 adopted as the M16A1; operator manual covers M16/M16A1 family.",
)
add(
    "M16A1",
    "United States",
    "Colt M16A1 Rifle",
    "m16a1",
    "5.56x45mm NATO",
    304.8,
    "tm_9_1005_249_10",
    "fm_23_9",
    "FM 23-9: 'The M16A1 has a 1:12 barrel twist.'",
)
add(
    "M16A2",
    "United States",
    "Colt M16A2 Rifle",
    "m16a2",
    "5.56x45mm NATO",
    177.8,
    "tm_9_1005_319_10",
    "tm_9_1005_319_10",
    "TM 9-1005-319-10: 'Rifling (RH 1/7 twist)'.",
)
add(
    "M16A3",
    "United States",
    "Colt M16A3 Rifle",
    "m16a3",
    "5.56x45mm NATO",
    177.8,
    "tm_9_1005_319_10",
    "tm_9_1005_319_10",
    "TM covers M16A3; rifling RH 1/7 twist.",
)
add(
    "M16A4",
    "United States",
    "Colt M16A4 Rifle",
    "m16a4",
    "5.56x45mm NATO",
    177.8,
    "tm_9_1005_319_10",
    "tm_9_1005_319_10",
    "TM covers M16A4; rifling RH 1/7 twist.",
)
add(
    "M4",
    "United States",
    "Colt M4 Carbine",
    "m4",
    "5.56x45mm NATO",
    177.8,
    "tm_9_1005_319_10",
    "tm_9_1005_319_10",
    "TM covers M4; rifling RH 1/7 twist.",
)
add(
    "M4A1",
    "United States",
    "Colt M4A1 Carbine",
    "m4a1",
    "5.56x45mm NATO",
    177.8,
    "tm_9_1005_319_10",
    "tm_9_1005_319_10",
    "TM covers M4A1; rifling RH 1/7 twist.",
)
add(
    "M4 MWS",
    "United States",
    "Colt M4 Modular Weapon System",
    "m4_mws",
    "5.56x45mm NATO",
    177.8,
    "tm_9_1005_319_10",
    "tm_9_1005_319_10",
    "Rail-equipped M4; same barrel as M4.",
)
add(
    "M4A1 Block II",
    "United States",
    "Colt M4A1 (SOPMOD Block II)",
    "m4a1_block2",
    "5.56x45mm NATO",
    None,
    "tm_9_1005_319_10",
    None,
    "USSOCOM SOPMOD Block II configuration of the M4A1; no distinct twist published in cited source.",
)
add(
    "XM4",
    "United States",
    "Colt XM4 Carbine",
    "xm4",
    "5.56x45mm NATO",
    None,
    "tm_9_1005_319_10",
    None,
    "Interim designation of the M4 carbine.",
)
add(
    "M231",
    "United States",
    "Colt M231 Firing Port Weapon",
    "m231",
    "5.56x45mm NATO",
    None,
    "tm_9_1005_309_10",
    None,
    "Firing port weapon for the M2 Bradley. Twist not stated in cited operator manual.",
)
add(
    "M27 IAR",
    "United States",
    "Heckler & Koch M27 Infantry Automatic Rifle",
    "m27_iar",
    "5.56x45mm NATO",
    177.8,
    "hk_m27",
    "hk_m27",
    "M27 sheet: 'Rifling 1 in 7 inches, right-hand twist, 6 grooves'.",
)
add(
    "M38 DMR",
    "United States",
    "Heckler & Koch M38 Squad Designated Marksman Rifle",
    "m38_dmr",
    "5.56x45mm NATO",
    177.8,
    "hk416_a5",
    "hk416_a5",
    "HK416-A5 sheet: M38 SDMR is the M27 (HK416); '1 in 7 right hand twist'.",
)

# --- US sniper / DMR (AR-10 lineage) ---------------------------------------
add(
    "M110 SASS",
    "United States",
    "Knight's Armament M110 Semi-Automatic Sniper System",
    "m110_sass",
    "7.62x51mm NATO",
    279.4,
    "kac_m110",
    "kac_m110",
    "KAC datasheet: 'Barrel 20in 1:11 5R Cut Rifled Barrel'. Differs from the 7.62 chambering standard.",
)
add(
    "M110A1 CSASS",
    "United States",
    "Heckler & Koch M110A1 CSASS (G28E)",
    "m110a1",
    "7.62x51mm NATO",
    None,
    "hk_g28",
    None,
    "US Army designation of the HK G28E, developed from the HK417; twist not stated on cited G28 page.",
)
add(
    "M110A1 SDMR",
    "United States",
    "Heckler & Koch M110A1 SDMR",
    "m110a1_sdmr",
    "7.62x51mm NATO",
    None,
    "hk_g28",
    None,
    "Squad designated marksman variant of the M110A1; HK417/G28 based.",
)
add(
    "Mk 11 Mod 0",
    "United States",
    "Knight's Armament Mk 11 Mod 0",
    "mk11",
    "7.62x51mm NATO",
    279.4,
    "kac_m110",
    "kac_m110",
    "KAC M110 datasheet describes the M110 as an evolution of the original Mk 11 with the same 1:11 5R barrel.",
)
add(
    "Mk 12 Mod 0/1",
    "United States",
    "Naval Surface Warfare Center Mk 12 Special Purpose Rifle",
    "mk12",
    "5.56x45mm NATO",
    177.8,
    "snipercentral_mk12",
    "snipercentral_mk12",
    "Mk 12 SPR: Douglas 18 inch barrel, 1:7 twist.",
)
add(
    "Mk 18 Mod 0/1",
    "United States",
    "Colt Mk 18 Close Quarters Battle Receiver",
    "mk18",
    "5.56x45mm NATO",
    None,
    "military_factory",
    None,
    "USSOCOM CQBR conversion of the M4A1 carbine; no twist published in cited reference.",
)
add(
    "M25",
    "United States",
    "Springfield Armory M25 (M14 derivative)",
    "m25",
    "7.62x51mm NATO",
    None,
    "military_factory",
    None,
    "Not an AR-pattern weapon; built on the M14.",
)
add(
    "M39 EMR",
    "United States",
    "USMC M39 Enhanced Marksman Rifle (M14 derivative)",
    "m39_emr",
    "7.62x51mm NATO",
    None,
    "military_factory",
    None,
    "Not an AR-pattern weapon; built on the M14.",
)
add(
    "M468",
    "United States",
    "Barrett M468",
    "m468",
    "6.8mm Rem SPC",
    None,
    "barrett_rec7",
    None,
    "Barrett 6.8mm AR-pattern carbine; retired in favour of the REC7.",
)

# --- FN SCAR ---------------------------------------------------------------
add(
    "Mk 16 Mod 0",
    "United States",
    "FN SCAR-L (Mk 16 Mod 0)",
    "mk16",
    "5.56x45mm NATO",
    177.8,
    "fn_scar",
    "fn_scar",
    "FN SCAR-L; Mk 16 family barrels are 1 in 7, equal to the 5.56 standard.",
)
add(
    "Mk 17 Mod 0",
    "United States",
    "FN SCAR-H (Mk 17 Mod 0)",
    "mk17",
    "7.62x51mm NATO",
    304.8,
    "fn_scar",
    "fn_scar",
    "FN SCAR-H; Mk 17 family barrels are 1 in 12 (304.8 mm), equal to the 7.62 standard.",
)
add(
    "Mk 20 Mod 0 SSR",
    "United States",
    "FN SCAR-H SSR (Mk 20 Mod 0)",
    "mk20_ssr",
    "7.62x51mm NATO",
    None,
    "fn_scar",
    None,
    "Sniper Support Rifle based on the SCAR-H.",
)

# --- Heckler & Koch --------------------------------------------------------
add(
    "HK416",
    "Germany",
    "Heckler & Koch HK416",
    "hk416",
    "5.56x45mm NATO",
    177.8,
    "hk416_manual",
    "hk416_manual",
    "HK416 operator manual: 'Barrel twist: 178 mm (1 in 7 right hand twist)'.",
)
add(
    "HK416A5",
    "Germany",
    "Heckler & Koch HK416A5",
    "hk416a5",
    "5.56x45mm NATO",
    177.8,
    "hk416_a5",
    "hk416_a5",
    "HK USA sheet: '1 in 7 right hand twist rifling'.",
)
add(
    "HK416A7",
    "Germany",
    "Heckler & Koch HK416A7 (G95)",
    "hk416a7",
    "5.56x45mm NATO",
    None,
    "hk416_a5",
    None,
    "A7/G95 not covered by the cited info sheet; no twist published there.",
)
add(
    "HK417",
    "Germany",
    "Heckler & Koch HK417",
    "hk417",
    "7.62x51mm NATO",
    279.4,
    "hk417_techdata",
    "hk417_techdata",
    "HK417 Technical Data: '4 grooves, right-hand twist 280 mm' (279.4 mm = 1 turn in 11 in).",
)
add(
    "HK417A2",
    "Germany",
    "Heckler & Koch HK417A2",
    "hk417a2",
    "7.62x51mm NATO",
    None,
    "hk417_product",
    None,
    "A2 variant; no twist stated on the cited HK417 page.",
)
add(
    "G27",
    "Germany",
    "Heckler & Koch HK417 (Bundeswehr G27)",
    "g27",
    "7.62x51mm NATO",
    None,
    "hk417_product",
    None,
    "German service designation of the HK417; twist not stated in cited source.",
)
add(
    "G28",
    "Germany",
    "Heckler & Koch G28",
    "g28",
    "7.62x51mm NATO",
    None,
    "hk_g28",
    None,
    "Designated marksman rifle derived from the HK417/MR308; twist not stated on cited page.",
)
add(
    "G38",
    "Germany",
    "Heckler & Koch HK417 variant (reported G38)",
    "g38",
    "7.62x51mm NATO",
    None,
    "hk417_product",
    None,
    "Reported German designation for an HK417 variant; not confirmed by the cited primary source.",
)
add(
    "G95",
    "Germany",
    "Heckler & Koch HK416A7 (G95)",
    "g95",
    "5.56x45mm NATO",
    None,
    "hk416_a5",
    None,
    "German service designation of the HK416A7; no twist published in cited sheet.",
)
add(
    "MR556",
    "United States",
    "Heckler & Koch MR556",
    "mr556",
    "5.56x45mm NATO",
    177.8,
    "hk416_a5",
    "hk416_a5",
    "US semi-automatic build of the HK416; sheet states 1 in 7 right hand twist.",
)
add(
    "MR762",
    "United States",
    "Heckler & Koch MR762",
    "mr762",
    "7.62x51mm NATO",
    None,
    "hk416_a5",
    None,
    "US semi-automatic build of the HK417; twist not stated in cited sheet.",
)

# --- Lewis Machine & Tool and UK designations ------------------------------
add(
    "MARS-L",
    "United States",
    "LMT MARS-L",
    "mars_l",
    "5.56x45mm NATO",
    177.8,
    "lmt_mars",
    "lmt_mars",
    "LMT: '16in 5.56x45 chrome lined 1:7 RH Twist Barrel'.",
)
add(
    "MARS-H",
    "United States",
    "LMT MARS-H",
    "mars_h",
    "7.62x51mm NATO",
    None,
    "lmt",
    None,
    "7.62 LMT MARS variant; twist not stated on cited page.",
)
add(
    "L129A1",
    "United Kingdom",
    "LMT L129A1 Sharpshooter Rifle",
    "l129a1",
    "7.62x51mm NATO",
    285.75,
    "firearmsnews_lmt",
    "firearmsnews_lmt",
    "LMT Sharpshooter (L129A1): 16 inch stainless barrel, 1:11.25 twist (285.75 mm). Differs from the 7.62 standard.",
)
add(
    "L119A1",
    "United Kingdom",
    "Colt Canada C8 SFW (L119A1)",
    "l119a1",
    "5.56x45mm NATO",
    177.8,
    "forgotten_weapons_l119a2",
    "coltcanada_c7",
    "UK designation of the Colt Canada C8 SFW; C7 family barrel is 6 grooves, 1 in 17.8 cm.",
)
add(
    "L119A2",
    "United Kingdom",
    "Colt Canada C8 IUR (L119A2)",
    "l119a2",
    "5.56x45mm NATO",
    177.8,
    "forgotten_weapons_l119a2",
    "coltcanada_c7",
    "UK designation of the Colt Canada C8 IUR; 1-in-7 twist.",
)

# --- Colt Canada / Diemaco ------------------------------------------------
add(
    "C7",
    "Canada",
    "Diemaco/Colt Canada C7",
    "c7",
    "5.56x45mm NATO",
    177.8,
    "coltcanada_c7",
    "coltcanada_c7",
    "Colt Canada manual: '6 grooves, 1 in 17.8 cm' (178 mm).",
)
add(
    "C7A1",
    "Canada",
    "Colt Canada C7A1",
    "c7a1",
    "5.56x45mm NATO",
    177.8,
    "coltcanada_c7",
    "coltcanada_c7",
    "C7 family, 1 in 17.8 cm rifling.",
)
add(
    "C7A2",
    "Canada",
    "Colt Canada C7A2",
    "c7a2",
    "5.56x45mm NATO",
    177.8,
    "coltcanada_c7",
    "coltcanada_c7",
    "C7 family, 1 in 17.8 cm rifling.",
)
add(
    "C8",
    "Canada",
    "Colt Canada C8 Carbine",
    "c8",
    "5.56x45mm NATO",
    177.8,
    "coltcanada_c7",
    "coltcanada_c7",
    "C8 listed in the C7 family manual; 1 in 17.8 cm rifling.",
)
add(
    "C8A1",
    "Canada",
    "Colt Canada C8A1",
    "c8a1",
    "5.56x45mm NATO",
    177.8,
    "coltcanada_c7",
    "coltcanada_c7",
    "C8 family, 1 in 17.8 cm rifling.",
)
add(
    "C8A2",
    "Canada",
    "Colt Canada C8A2",
    "c8a2",
    "5.56x45mm NATO",
    None,
    "coltcanada",
    None,
    "Later C8 variant; no twist published in cited source.",
)
add(
    "C8A3",
    "Canada",
    "Colt Canada C8A3",
    "c8a3",
    "5.56x45mm NATO",
    None,
    "coltcanada",
    None,
    "Later C8 variant; no twist published in cited source.",
)
add(
    "C20 DMR",
    "Canada",
    "Colt Canada C20 Designated Marksman Rifle",
    "c20",
    "7.62x51mm NATO",
    None,
    "coltcanada",
    None,
    "Colt Canada 7.62 DMR; twist not stated on cited page.",
)
add(
    "Colt Canada MRR",
    "Canada",
    "Colt Canada Modular Rail Rifle",
    "mrr",
    "5.56x45mm NATO",
    None,
    "coltcanada",
    None,
    "Colt Canada Modular Rail Rifle; twist not stated on cited page.",
)

# --- Knight's Armament -----------------------------------------------------
add(
    "SR-15",
    "United States",
    "Knight's Armament SR-15",
    "sr15",
    "5.56x45mm NATO",
    None,
    "kac_sr15",
    None,
    "KAC SR-15; twist not stated on cited product page.",
)
add(
    "SR-16",
    "United States",
    "Knight's Armament SR-16",
    "sr16",
    "5.56x45mm NATO",
    None,
    "kac_sr15",
    None,
    "KAC SR-16; full-auto SR-15 variant.",
)
add(
    "SR-25",
    "United States",
    "Knight's Armament SR-25",
    "sr25",
    "7.62x51mm NATO",
    254.0,
    "kac_sr25",
    "kac_sr25",
    "KAC SR-25 K3: '16in, 5R cut rifled, 416R SS, 1:10 twist'. Differs from the 7.62 standard.",
)

# --- SIG SAUER -------------------------------------------------------------
add(
    "SIG M400",
    "United States",
    "SIG SAUER M400",
    "sig_m400",
    "5.56x45mm NATO",
    177.8,
    "sig_m400",
    "sig_m400",
    "M400 16 inch barrel, 1:7 twist (equal to the 5.56 standard).",
)
add(
    "SIG516",
    "United States",
    "SIG SAUER SIG516",
    "sig516",
    "5.56x45mm NATO",
    None,
    "sig_sauer",
    None,
    "SIG 5.56 AR-pattern rifle; twist not stated in cited source.",
)
add(
    "SIG716",
    "United States",
    "SIG SAUER SIG716",
    "sig716",
    "7.62x51mm NATO",
    None,
    "sig_sauer",
    None,
    "SIG 7.62 AR-pattern rifle; twist not stated in cited source.",
)
add(
    "SIG MCX",
    "United States",
    "SIG SAUER MCX",
    "sig_mcx",
    "5.56x45mm NATO",
    None,
    "sig_sauer",
    None,
    "SIG MCX; twist not stated in cited source.",
)
add(
    "SIG MCX Spear",
    "United States",
    "SIG SAUER MCX-SPEAR",
    "mcx_spear",
    "6.8x51mm",
    None,
    "sig_mcx_spear",
    None,
    "SIG lists a 1:7 twist for the MCX-SPEAR; not confirmed in a downloaded datasheet.",
)
add(
    "XM5",
    "United States",
    "SIG SAUER MCX-SPEAR (XM5)",
    "xm5",
    "6.8x51mm",
    None,
    "sig_mcx_spear",
    None,
    "Original NGSW designation of the MCX-SPEAR, later XM7.",
)
add(
    "XM7",
    "United States",
    "SIG SAUER MCX-SPEAR (XM7)",
    "xm7",
    "6.8x51mm",
    None,
    "sig_mcx_spear",
    None,
    "US Army NGSW-Rifle designation of the MCX-SPEAR, later M7.",
)
add(
    "M7",
    "United States",
    "SIG SAUER M7 (MCX-SPEAR)",
    "m7",
    "6.8x51mm",
    None,
    "sig_mcx_spear",
    None,
    "Adopted US Army designation of the XM7.",
)
add(
    "XM250",
    "United States",
    "SIG SAUER SIG LMG-6.8 (XM250)",
    "xm250",
    "6.8x51mm",
    None,
    "sig_lmg",
    None,
    "Belt-fed light machine gun; not an AR-pattern weapon. Twist not stated in cited sheet.",
)
add(
    "M250",
    "United States",
    "SIG SAUER M250 (SIG LMG-6.8)",
    "m250",
    "6.8x51mm",
    None,
    "sig_lmg",
    None,
    "Adopted US Army designation of the XM250; not an AR-pattern weapon.",
)

# --- Major US commercial makers --------------------------------------------
add(
    "Ruger AR-556",
    "United States",
    "Ruger AR-556",
    "ar556",
    "5.56x45mm NATO",
    203.2,
    "ruger_ar556",
    "ruger_ar556",
    "Ruger: '1:8 twist rifling' (203.2 mm). Differs from the 5.56 standard.",
)
add(
    "Daniel Defense DDM4",
    "United States",
    "Daniel Defense DDM4",
    "ddm4",
    "5.56x45mm NATO",
    177.8,
    "dd_ddm4",
    "dd_ddm4",
    "DDM4 V7: 'Chrome Moly Vanadium Steel, Cold Hammer Forged, 1:7 Twist'.",
)
add(
    "Smith & Wesson M&P15",
    "United States",
    "Smith & Wesson M&P15",
    "mp15",
    "5.56x45mm NATO",
    None,
    "smith_wesson",
    None,
    "S&W AR-15 pattern rifle; twist not stated in cited source.",
)
add(
    "Springfield SAINT",
    "United States",
    "Springfield Armory SAINT",
    "saint",
    "5.56x45mm NATO",
    None,
    "springfield_saint",
    None,
    "Springfield Armory AR-15 pattern rifle; twist not stated in cited source.",
)
add(
    "BCM",
    "United States",
    "Bravo Company USA (BCM) AR-15",
    "bcm",
    "5.56x45mm NATO",
    None,
    "bcm",
    None,
    "BCM offers several twist rates; the cited 18 inch upper is 1/8. No single twist applies to the brand.",
)
add(
    "Noveske N4",
    "United States",
    "Noveske Rifleworks N4",
    "noveske_n4",
    "5.56x45mm NATO",
    None,
    "noveske",
    None,
    "Noveske AR-15 pattern rifle; twist not stated in cited source.",
)
add(
    "Geissele Super Duty",
    "United States",
    "Geissele Automatics Super Duty",
    "geissele_sd",
    "5.56x45mm NATO",
    None,
    "geissele",
    None,
    "Geissele AR-15 pattern rifle; twist not stated in cited source.",
)
add(
    "Aero Precision",
    "United States",
    "Aero Precision AR-15",
    "aero_ar15",
    "5.56x45mm NATO",
    None,
    "aero",
    None,
    "Aero Precision AR-15 platform; twist not stated in cited source.",
)
add(
    "Windham Weaponry",
    "United States",
    "Windham Weaponry AR-15",
    "windham",
    "5.56x45mm NATO",
    None,
    "windham",
    None,
    "Windham AR-15 pattern rifle; twist not stated in cited source.",
)
add(
    "Rock River Arms LAR-15",
    "United States",
    "Rock River Arms LAR-15",
    "rra_lar15",
    "5.56x45mm NATO",
    None,
    "rra",
    None,
    "RRA AR-15 pattern rifle; twist not stated in cited source.",
)
add(
    "DPMS",
    "United States",
    "DPMS Panther Arms AR-15",
    "dpms",
    "5.56x45mm NATO",
    None,
    "dpms",
    None,
    "DPMS AR-15 pattern rifle; twist not stated in cited source.",
)
add(
    "Bushmaster",
    "United States",
    "Bushmaster Firearms AR-15",
    "bushmaster",
    "5.56x45mm NATO",
    None,
    "bushmaster",
    None,
    "Bushmaster AR-15 pattern rifle; twist not stated in cited source.",
)
add(
    "Barrett REC7",
    "United States",
    "Barrett REC7",
    "rec7",
    "6.8mm Rem SPC",
    None,
    "barrett_rec7",
    None,
    "Barrett 6.8mm AR-pattern rifle; twist not stated in cited source.",
)
add(
    "Barrett REC10",
    "United States",
    "Barrett REC10",
    "rec10",
    "7.62x51mm NATO",
    None,
    "barrett_rec10",
    None,
    "Barrett 7.62mm AR-pattern rifle; twist not stated in cited source.",
)
add(
    "Remington R4",
    "United States",
    "Remington R4",
    "r4",
    "5.56x45mm NATO",
    None,
    "remington",
    None,
    "Remington 5.56 AR-pattern carbine; twist not stated in cited source.",
)
add(
    "Remington R5",
    "United States",
    "Remington R5",
    "r5",
    "7.62x51mm NATO",
    None,
    "remington",
    None,
    "Remington 7.62 AR-pattern rifle (R25 lineage); twist not stated in cited source.",
)
add(
    "ArmaLite AR-10",
    "United States",
    "ArmaLite AR-10 (original)",
    "ar10_original",
    "7.62x51mm NATO",
    None,
    "armalite",
    None,
    "Original Eugene Stoner AR-10 battle rifle; twist varies by barrel and is not stated on cited page.",
)
add(
    "ArmaLite AR-10A",
    "United States",
    "ArmaLite AR-10A",
    "ar10a",
    "7.62x51mm NATO",
    None,
    "armalite",
    None,
    "ArmaLite AR-10A series; twist varies by barrel (1:11.25 historically, later 1:10).",
)
add(
    "ArmaLite AR-10B",
    "United States",
    "ArmaLite AR-10B",
    "ar10b",
    "7.62x51mm NATO",
    None,
    "armalite_manual",
    None,
    "Operator's manual covers all AR-10B and M15 series rifles; twist varies by barrel and is not stated.",
)

OUT = {
    "retrieved": "2026-09-22",
    "sources": SOURCES,
    "designations": D,
}

path = Path("/ext/Development/AEE/data/ballistics/sources/designations_ar.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(OUT, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# --- report ---------------------------------------------------------------
src_ids = {s["source_id"] for s in SOURCES}
bad = [d for d in D if d["map_source_id"] not in src_ids]
if bad:
    raise SystemExit(
        "UNKNOWN map_source_id: " + ", ".join(d["designation"] for d in bad)
    )
missing_twist_src = [
    d for d in D if d["twist_source_id"] and d["twist_source_id"] not in src_ids
]
if missing_twist_src:
    raise SystemExit(
        "UNKNOWN twist_source_id: "
        + ", ".join(d["designation"] for d in missing_twist_src)
    )

std = {
    "5.56x45mm NATO": 177.8,
    "7.62x51mm NATO": 304.8,
    ".300 BLK": 203.2,
    "6.5 Creedmoor": 203.0,
}
diff = [
    d
    for d in D
    if d["twist_mm"] is not None
    and d["chambering"] in std
    and abs(d["twist_mm"] - std[d["chambering"]]) > 0.01
]
print("designations:", len(D))
print("sources:", len(SOURCES))
print("twist differs from chambering standard:", len(diff))
for d in diff:
    print(
        f"  {d['designation']}: {d['twist_mm']} mm vs {std[d['chambering']]} ({d['chambering']})"
    )
print("null twist:", sum(1 for d in D if d["twist_mm"] is None))
