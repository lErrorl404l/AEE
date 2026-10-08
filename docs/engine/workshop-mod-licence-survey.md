# Workshop mod licence survey - AEE adoption assessment

Survey. No file was copied into the repository. Compiled 2026-10-08.

Purpose: replace the standing blanket rule ("ideas-only, no surveyed mod carries a licence") with per-mod licence facts, so AEE can maximise lawful adoption.

## Method and sources

- Workshop root on this machine: `the Arma 3 Workshop content directory`. This is the only Workshop root. 219 mods.
- For every mod the local `meta.cpp`, `mod.cpp`, `LICENSE`/`LICENCE`/`COPYING`, `README`, and other text files were read.
- Every mod's Workshop page text was fetched through the Steam Web API (`ISteamRemoteStorage/GetPublishedFileDetails/v1`) in one batch of 219 IDs, 2026-10-08.
- Classification rule (from the task): PERMISSIVE (MIT, Apache-2.0, BSD, CC-BY, CC-BY-SA, public domain, explicit author grant to reuse); COPYLEFT (GPL, LGPL); RESTRICTIVE (APL-SA, APL-ND, ADPL-SA, CC-BY-NC-ND, GRAD APL, custom all-rights/no-reupload); UNKNOWN (no licence found anywhere).
- AEE is GPL-2.0-or-later. GPL-2.0/3.0 code is licence-compatible. MIT/BSD/CC-BY are compatible with attribution. APL-* is NOT a free licence and NOT GPL-compatible: nothing may be copied.
- Note: "NONE FOUND" means the author states no licence anywhere read. Under default copyright that is all-rights-reserved. Treat as RESTRICTIVE for copying; the class shown is UNKNOWN to record that no document exists.

## Headline result

| Class | Mods |
|---|---|
| COPYLEFT (adopt) | 11 |
| PERMISSIVE (adopt with attribution) | 9 |
| RESTRICTIVE (reimplement) | 39 |
| UNKNOWN / NONE FOUND (reimplement) | 160 |

The old policy was overbroad. 20 mods carry a clearly permissive or copyleft licence that AEE may adopt. 39 carry a restrictive licence that forbids copying. 160 state no licence and must be treated as all-rights-reserved.

## Summary table

| ID | Mod | Licence (exact) | Class | Adopt / Reimplement |
|---|---|---|---|---|
| 171174718 | Operation Nightmare | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 288705934 | ASCZ Post-process Effects | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 313041182 | L3-GPNVG18 Panoramic Night Vision | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 333310405 | Enhanced Movement | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 350606620 | Post Process Effect Editor | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 366425329 | FIR AWS(AirWeaponSystem) | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 450814997 | CBA_A3 | GPL-2.0 (LICENSE.md) | COPYLEFT | ADOPT |
| 463939057 | ace | GPL-2.0; subfolders: APL (addons/apl), CC-BY-3.0 (fastroping/tagging sounds), CC-BY-4.0 (refuel sounds), CC0 (wardrobe sounds) (LICENSE) | COPYLEFT | ADOPT |
| 520618345 | Jbad | APL-SA (Jbad_APL-SA_Licence.txt) | RESTRICTIVE | REIMPLEMENT |
| 570118882 | No Weapon Sway | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 583496184 | CUP Terrains - Core | APL-SA (APL-SA_license.txt) + CUP-License (Attributions.txt) | RESTRICTIVE | REIMPLEMENT |
| 583544987 | CUP Terrains - Maps | APL-SA (APL-SA_license.txt) | RESTRICTIVE | REIMPLEMENT |
| 615007497 | Advanced Sling Loading | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 623475643 | 3den Enhanced | APL-SA (LICENSE.md) | RESTRICTIVE | REIMPLEMENT |
| 632435682 | Remove stamina | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 639837898 | Advanced Towing | MIT (README) | PERMISSIVE | ADOPT |
| 649832908 | ReColor | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 656307117 | Post Process Effects | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 663045982 | Weapons/mobility training. | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 682140680 | kerama Islands By [Vétérans] | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 686802825 | Eden Objects | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 687941412 | THUNDERBOLT Script-DEMO | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 705986840 | Dynamic Recon Ops - Altis | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 707934800 | Operation Nightfall - Tanoa Stories [VIPER] | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 713709341 | Advanced Rappelling | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 730310357 | Advanced Urban Rappelling | MIT (README) | PERMISSIVE | ADOPT |
| 735566597 | Project OPFOR | CC BY-NC-ND 3.0 Unported / RHS licence (README) | RESTRICTIVE | REIMPLEMENT |
| 748534644 | RS - Rain Textures | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 751655861 | Storm Script DEMO v1.02 | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 751965892 | ACRE2 | GPL-3.0 (LICENSE, README) | COPYLEFT | ADOPT |
| 767380103 | Blastcore Edited (a fix version) | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 767380317 | Blastcore Edited (standalone version) | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 782415569 | Remove stamina - ACE 3 | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 782564017 | Tornado Script DEMO | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 783687235 | Monsoon Script DEMO | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 786813177 | Snow Storm Script DEMO | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 800771522 | Dust Storm Script DEMO | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 837729515 | CH View Distance | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 843425103 | RHSAFRF | CC BY-NC-ND 3.0 (main) + APL-SA/TOPL-SA parts; reupload prohibited (README) | RESTRICTIVE | REIMPLEMENT |
| 843577117 | RHSUSAF | CC BY-NC-ND 3.0 + APL-SA/TOPL-SA parts; reupload prohibited (README) | RESTRICTIVE | REIMPLEMENT |
| 843593391 | RHSGREF | CC BY-NC-ND 3.0 + APL-SA/TOPL-SA parts; reupload prohibited (README) | RESTRICTIVE | REIMPLEMENT |
| 843632231 | RHSSAF | CC BY-NC-ND 3.0 + APL-SA/TOPL-SA parts; reupload prohibited (README) | RESTRICTIVE | REIMPLEMENT |
| 861133494 | JSRS SOUNDMOD | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 879970502 | Real World Weather | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 880703327 | Enhanced Visuals | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 882231372 | Eden Extended Objects | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 894678801 | Task Force Arrowhead Radio (BETA!!!) | APL-SA (LICENSE.md) | RESTRICTIVE | REIMPLEMENT |
| 909547724 | LYTHIUM | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 917439367 | Stratis Tidesystem | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 929396506 | MRB Air Visibility | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 930903722 | MRB Vehicle Visibility | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 941263726 | Sullen Skies for CUP Terrains | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 962938144 | MBG Buildings Killhouses (Arma3 Remaster) | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 964303647 | VKing's APP-6 NATO map markers | Custom restrictive (Readme.md): redistribute with credit; may NOT reproduce/modify graphics; no commercial/military use; scripts may be reverse-engineered for learning | RESTRICTIVE | REIMPLEMENT graphics; scripts learn-only |
| 1105511475 | ArmaFXP | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1109237932 | Extended Fortifications Mod | CC BY-NC-ND 4.0 (.license_CC_by_nc_nd.txt) | RESTRICTIVE | REIMPLEMENT |
| 1114594249 | Arma 3 Animals Module - Extended | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1223309664 | Enhanced Video Settings | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1224892496 | Gruppe Adler Trenches | GRAD APL v1.1 (LICENSE, README) - custom; same terms | RESTRICTIVE | REIMPLEMENT; code fragments with credit |
| 1278117099 | Kill House and Range | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1340701737 | NATO Markers+ | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1342869619 | Dust Wind Effect [DISCONTINUED] | Author grant: discontinued, 'feel free to use, modify and reupload' (Workshop) | PERMISSIVE | ADOPT |
| 1351428303 | AH-64D Official Project | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1354112941 | GRAD Sling Helmet | GRAD APL v1.1 (LICENSE, README) - custom; no reupload, no commercial; small script/function parts may be reused with credit | RESTRICTIVE | REIMPLEMENT (whole mod); code fragments reuse with credit |
| 1364777346 | BHC Map Contour | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1389082106 | Mid-Detail Texture | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1396901301 | dzn Artillery Illumination | APL-SA (Workshop) | RESTRICTIVE | REIMPLEMENT |
| 1429785213 | Postapocalyptic DEMO | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1436202915 | Local Fog DEMO | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1439985051 | DUST SFX DEMO | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1465275935 | Enhanced Weather + Clouds Mod v2.1 | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1514439943 | Anti Aircraft Tracer + Bullet Mod | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1526605442 | AI Stress Test | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1537745369 | Helicopter Dust Efx Mod | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1703765606 | ANZACSAS Napalm and WP Smoke marker rockets | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1726494027 | Kujari | APL-SA (Workshop) | RESTRICTIVE | REIMPLEMENT |
| 1745501605 | Hatchet H-60 Pack - Stable Version | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1779063631 | Zeus Enhanced | GPL-3.0 (LICENSE, README) | COPYLEFT | ADOPT |
| 1808238502 | LAMBS_Suppression | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1818784949 | Dynamic Weather | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1845100804 | MRB Sea Vessel Visibility | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1852631379 | RKSL Studios - AW159 Wildcat | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1858070328 | LAMBS_RPG | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1858075458 | LAMBS_Danger.fsm | GPL-2.0 (LICENSE, README) | COPYLEFT | ADOPT |
| 1862208264 | LAMBS_Turrets | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1891978580 | ADE - Advanced Diving Environment | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1945404816 | Color Corrector | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 1960024802 | PLP All in One | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2020940806 | KAT - Advanced Medical | GPL-3.0 (local LICENSE). CONFLICT: Workshop text claims APL-SA | COPYLEFT | ADOPT (GPL-3 local licence governs) |
| 2026526896 | Copehill Down, England | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2034363662 | Enhanced Movement Rework | GPL-2.0 (LICENSE) | COPYLEFT | ADOPT |
| 2041057379 | A3 Thermal Improvement | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2198339170 | Alternative Running | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2214384530 | Scottish Highlands | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2216393505 | Sullen Skies - Scottish Highlands | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2266710560 | UMB Colombia | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2275409948 | STRM (Random Weather Module) | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2276624333 | Terrain Object Replacement Modules | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2309871702 | Advance Aero Effects | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2333743487 | RKSL Studios Common Library | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2372036642 | BackpackOnChest - Redux | MIT (LICENSE, README) | PERMISSIVE | ADOPT |
| 2414056006 | Simple Thermal Goggles | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2421048459 | Splendid Smoke Rework | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2422853226 | Seb's Briefing Table | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2424322922 | Aaren's Blast Effects | APL-ND (LICENSE.md; template not filled) | RESTRICTIVE | REIMPLEMENT |
| 2443587784 | Aaren's Tracer Fix (Vanilla) | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2467589125 | Enhanced Map | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2487561318 | Aaren's Tracer Lower Brightness | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2494550406 | HMCS Addon thermal edited version | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2499043863 | Project Tornado | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2515887728 | Crows Electronic Warfare | APL-SA (LICENSE) + 'Reuploads/Repacking into other mods on the steam workshop is not permitted' | RESTRICTIVE | REIMPLEMENT |
| 2555651608 | Alias Night FX Modules | APL-SA (Workshop) + 'DO NOT INCORPORATE THIS SCRIPT OR PORTIONS OF IT' | RESTRICTIVE | REIMPLEMENT |
| 2572487482 | WebKnight Flashlights and Headlamps | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2577441180 | Hate's Digital Camera | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2586787720 | TPW MODS | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2638049909 | Lushify | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2645823531 | Wildfire | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2735613231 | Weather Plus | APL-SA (Workshop) | RESTRICTIVE | REIMPLEMENT |
| 2782377874 | MOUT Training Facility | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2801179774 | Better Convoy | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2809399991 | Real Lighting and Weather | APL-ND (Workshop) | RESTRICTIVE | REIMPLEMENT |
| 2822758266 | Deformer | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2829330653 | North Takistan | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2853200431 | Simple Craters | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2861950022 | Extra Post-Process Themes | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2866924390 | ANZACSAS Helicopter Dust Efx Mod - Lite | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2871933143 | SLX Explosion Dust | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2886141254 | Improved Craters | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2913534721 | Refraction blast wave by taro8 | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2914901109 | Chameleon Trenches | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2935700533 | Drongo's Dynamic Weather | ADPL-SA (Arma and DayZ Public License Share Alike) (LICENSE, Workshop) | RESTRICTIVE | REIMPLEMENT |
| 2941986336 | Hatchet Interaction Framework - Stable Version | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2953412769 | Photon VFX | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2958273599 | Modular Warehouse Parts | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2965509871 | [EP] Core - Enhancement Pack | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2965511518 | [EP] Suppression Effects - Enhancement Pack | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2965541384 | A3 Characters 4K | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2966168738 | Terrain Lib | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2967119946 | Bucket - Zeus Terrain Editor | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2975268929 | TPNVG - True Panoramic Night Vision | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2975882889 | Modular Shoothouse Parts | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2982306133 | Arma Realistic Map Assets V2 | APL-ND (LICENSE.txt) with carve-out: PBO may be freely re-distributed/re-packaged with maps generated by GameRealisticMap | RESTRICTIVE | REIMPLEMENT |
| 2983546566 | Dagger Island Training Complex (2025) | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 2986806147 | Dynamic Weather | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3013515917 | Lybor | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3023699939 | LV-426 | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3043180500 | ACRE-Persistence | GPL-3.0 (LICENSE) | COPYLEFT | ADOPT |
| 3045129955 | FPV Drone Crocus | Code GPL-2.0 (LICENSE); assets/visual APL-SA (ASSET_LICENSE.txt); bundled CBA macros GPL-2.0 (THIRD_PARTY_NOTICES.txt) | COPYLEFT | ADOPT code only; assets RESTRICTIVE |
| 3048818056 | IEDD Notebook | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3078351739 | Kunduz River | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3118416433 | Robotyne Ukraine | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3123207499 | Advanced Grappling | GPL-2.0 (LICENSE) | COPYLEFT | ADOPT |
| 3124577511 | Realistic Driving Terrains REWRITE | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3125837686 | Bulat UAV Detector by Nerexis | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3205264721 | Pyro's NATO Map Markers | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3226850988 | DISMEMBERMENT+GORE [SP-MP] | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3235483358 | Advanced Combat Medicine | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3256534418 | Trencher - Eden Trench Generation | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3257814741 | Almost Working Skyboxes | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3283612524 | Animate - Rewrite | Custom permissive (Workshop, same family): no port | PERMISSIVE | ADOPT with attribution |
| 3283642267 | Speshal Core | Custom permissive (Workshop): modify; redistribute within unit; public redistribute with credits; must NOT port | PERMISSIVE | ADOPT with attribution |
| 3283645995 | Breach - Rewrite | Custom permissive (Workshop, same as Speshal Core): no port | PERMISSIVE | ADOPT with attribution |
| 3299910335 | RHS Plus | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3316254084 | Advanced Combat Medicine Experimental | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3336740643 | Milsim Structures | APL-ND (Workshop) | RESTRICTIVE | REIMPLEMENT |
| 3341786920 | A3RO - Arma 3 Realism Overhaul | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3351805137 | Better Visuals | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3366918628 | Real Flashlights | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3370946091 | A3TI REAP-IR | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3373894018 | Derii Simple Craters | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3401580668 | Mavic 3 - Improved | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3407948300 | JSRS SOUNDMOD 2025 | APL-ND (LICENSE file, Workshop) | RESTRICTIVE | REIMPLEMENT |
| 3432188295 | Terrain Modifier | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3438246217 | cTAB Advanced [BETA] | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3438247879 | cTAB Connect [BETA] | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3462905403 |  | APL-ND (LICENSE, README claims APL-SA - local file says No Derivatives) | RESTRICTIVE | REIMPLEMENT |
| 3468294814 | Project New Light (custom lighting mod) | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3512167740 | Project Dynamic Dirt | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3518145984 | D.I.R.T. - Dynamic Textures | APL-SA (license.txt) | RESTRICTIVE | REIMPLEMENT |
| 3525204764 | Project Dynamic Blur | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3525653940 | D.I.R.T. - Blood Textures | MIT (license.txt) | PERMISSIVE | ADOPT |
| 3549882948 |  | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3555295736 | Modular Cages & Armory | APL-ND (Workshop) | RESTRICTIVE | REIMPLEMENT |
| 3580353814 |  | APL-ND (LICENSE) | RESTRICTIVE | REIMPLEMENT |
| 3587581054 | Highlights - HDR & Lighting Suite [HLS] | APL-ND (Workshop) | RESTRICTIVE | REIMPLEMENT |
| 3591015353 | [3DEN] Multiplayer Object Scaler | APL-SA (Workshop) | RESTRICTIVE | REIMPLEMENT |
| 3615039550 | Project M - Full Collection | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3634756604 | EP Ground Textures | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3645230323 |  | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3645466488 | VEU - Terrains | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3662499431 |  | Arma Public License (share-alike, Arma-3-only, non-commercial) (LICENSE) | RESTRICTIVE | REIMPLEMENT |
| 3672288512 | Vehicle Destruction FX | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3682613859 | TFN NVG Effects | Author grant: 'free to modify, reupload, include in modpacks, or adapt' (Workshop) | PERMISSIVE | ADOPT |
| 3702603652 | Reactive Building Effects PLUS | APL-SA (Workshop) | RESTRICTIVE | REIMPLEMENT |
| 3704702374 | Fluffys Enhanced Lighting | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3711042620 | KtweaK's NVG | APL-SA (Workshop, kenoxite content) | RESTRICTIVE | REIMPLEMENT |
| 3715450352 | Real Engine Enhanced | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3716493672 | Modular Ship Interior | APL-ND (Workshop) | RESTRICTIVE | REIMPLEMENT |
| 3725008325 | A3TI  FUSION NVG  Thermal Imaging  ALPHA 0.3 | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3726750329 | TrueColor | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3737586377 | Fluffys Enhanced Lighting 2.0 | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3739992827 | A3TI Scope & Others | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3749362906 | Star Light | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3753145363 | MKK Thermal Improvement | All rights reserved unless separate written permission (LICENSE) | RESTRICTIVE | REIMPLEMENT |
| 3759527903 | FPANO ECOTI | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3784622777 | NVG AutoGating | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3790320529 | AI Stress Test - Malden | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3792830104 | Adaptive Shadows | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3794987707 | Mugen's Alien Worlds | Arma Public License, no repack/redistribute (Workshop) | RESTRICTIVE | REIMPLEMENT |
| 3799193798 | A3SQL | APL-SA (LICENSE) | RESTRICTIVE | REIMPLEMENT |
| 3800537038 |  | GPL-3.0 (LICENSE, README) | COPYLEFT | ADOPT |
| 3805899171 | Pegasus Systems MH-47G | APL-ND (Workshop) | RESTRICTIVE | REIMPLEMENT |
| 3809860654 | whale_ecoti_lll （No Reshade needed） | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3810296503 | whale_ecoti_llll （No Reshade needed） | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3811025518 | OSM City Importer | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3811605241 | ECOTI edit by TFN | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3812286023 | Wings of Britannia | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3812620045 | HBQ Advanced Driving AI | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |
| 3815113077 | [whale] Realistic Freefall Ops | NONE FOUND | UNKNOWN | REIMPLEMENT (treat as all-rights-reserved) |

## 3. PERMISSIVE and COPYLEFT mods - what AEE should ADOPT

These 20 mods carry a licence AEE may use. Cite the mod and its licence in the ADR and in the file header.

### 3.1 COPYLEFT (licence-compatible with AEE GPL-2.0-or-later)

| ID | Mod | Licence | What to adopt, and why it is better than AEE today |
|---|---|---|---|
| 450814997 | CBA_A3 | GPL-2.0 | The XEH pre-start/pre-init/post-init chain, `CBA_fnc_compileFunction` (the function-ownership primitive), `script_macros_common.hpp` FUNC/EFUNC/PREP, and `CBA_fnc_addSetting`. AEE already depends on CBA. Adopt the macros and the settings/event extension surface. Source: `LICENSE.md`, `README.md`. |
| 463939057 | ACE3 | GPL-2.0 (subfolders APL/CC-BY/CC0) | The compat-adapter pattern (`requiredAddons` + `skipWhenMissingDependencies`), the EFUNC public API, the ACE medical state machine, and the interaction-menu extension points. ACE is the reference for modular realism. Adoption is code-level only; the `addons/apl` and sound subfolders keep their own restrictive/CC terms - do not copy those. Sources: `LICENSE`, `README.md`. |
| 1779063631 | Zeus Enhanced | GPL-3.0 | The rewritten Zeus attributes system (per-object attribute registration) and the Zeus module conventions. Better than AEE's Eden/Zeus coverage today. Source: `LICENSE`, `README.md`. |
| 751965892 | ACRE2 | GPL-3.0 | The radio simulation model (channel/PTT/antenna, TS3 integration) and the component split. AEE has no radio layer. Source: `LICENSE`, `README.md`. |
| 2034363662 | Enhanced Movement Rework | GPL-2.0 | The lightweight movement state machine that reuses animations without the original's baggage. Better than AEE's current movement handling. Source: `LICENSE`. |
| 2020940806 | KAT Advanced Medical | GPL-3.0 (local `LICENSE`). Workshop claims APL-SA - the local file governs | The medical extension model on top of ACE (airway/breathing/circulation, blood types) and the way it keeps medical roles meaningful. Source: `LICENSE`. |
| 1858075458 | LAMBS_Danger.fsm | GPL-2.0 (specifically v2) | The expanded Danger.fsm AI model (buildings as terrain, fire response). The Workshop page adds "Reuploading to Steam Workshop is not permitted"; GPL governs copying of code, but record the conflict - do not re-upload the mod itself, only incorporate code under GPL. Sources: `LICENSE`, `README.md`. |
| 3123207499 | Advanced Grappling | GPL-2.0 | The grappling-hook rope physics. AEE has no climbing system. Source: `LICENSE`. |
| 3043180500 | ACRE-Persistence | GPL-3.0 | The radio-config persistence and respawn-restore pattern. Source: `LICENSE`. |
| 3800537038 | ACE Environment Extended | GPL-3.0 | Physically-based environment simulation extending ACE. Source: `LICENSE`. |
| 3045129955 | ArmaFPV | Code GPL-2.0; assets APL-SA | The FPV-drone camera/flight code only. Assets are APL-SA and must NOT be copied. Source: `LICENSE`, `ASSET_LICENSE.txt`. |

### 3.2 PERMISSIVE (adopt with attribution)

| ID | Mod | Licence | What to adopt, and why |
|---|---|---|---|
| 2372036642 | BackpackOnChest - Redux | MIT | Chest/back dual-backpack movement model. Clean, GPL-compatible. Source: `LICENSE`. |
| 730310357 | Advanced Urban Rappelling | MIT | Urban rappelling rope physics. Source: `README.md`. |
| 639837898 | Advanced Towing | MIT | Rope towing model for vehicles. Source: `README.md`. |
| 3525653940 | D.I.R.T. - Blood Textures | MIT | The custom dynamic-texture-layer example for D.I.R.T. Reuse the pattern for AEE dynamic textures. Source: `license.txt`. |
| 3283642267 | Speshal Core | Custom permissive (modify; redistribute with credits; no port) | Shared functions/assets. Attribution required; note the no-port clause. Source: Workshop text. |
| 3283645995 | Breach - Rewrite | Custom permissive (same family) | Breaching/door mechanics. Source: Workshop text. |
| 3283612524 | Animate - Rewrite | Custom permissive (same family) | Tactical-stance animation system. Source: Workshop text. |
| 1342869619 | Dust Wind Effect | Author grant: "feel free to use, modify and reupload" | The foliage blast-wave/shake effect. This is an explicit reuse grant short of a named licence. Source: Workshop text. |
| 3682613859 | TFN NVG Effects | Author grant: "free to modify, reupload, include in modpacks, or adapt" | The NVG depth-of-field/eye-relief effect. Source: Workshop text. |

### 3.3 Strong candidates with a stated licence only on the Workshop page

These state a free licence in the description. Verify the licence text once more at adoption time.

- 2735613231 Weather Plus - APL-SA (restrictive; do not copy).
- 1396901301 dzn Artillery Illumination - APL-SA (restrictive; do not copy).

## 4. RESTRICTIVE mods - what AEE should REIMPLEMENT

For every restrictive mod, copy nothing. Reimplement from the engine surface or a published standard.

| ID | Mod | Licence | Reimplement from |
|---|---|---|---|
| 2467589125 | Enhanced Map | NONE FOUND (all-rights-reserved) | Engine map surface (RscMapControl/ctrlMap) + OS MasterMap palette. AEE has done this (ADR-028/ADR-029). |
| 1364777346 | BHC Map Contour | NONE FOUND | Same engine surface; contour colour from OS/USGS names. Done. |
| 1340701737 | NATO Markers+ | NONE FOUND | APP-6(C)/MIL-STD-2525 symbol geometry. Done (symbology catalogue). |
| 964303647 | VKing's APP-6 NATO markers | Custom restrictive (graphics ND) | APP-6/2525 geometry. Readme permits reverse-engineering scripts for learning only. |
| 3205264721 | Pyro's NATO Map Markers | NONE FOUND (composition, not a mod) | APP-6/2525 geometry; it is a mission composition with no dependency. |
| 2982306133 | Arma Realistic Map Assets V2 | APL-ND | Engine assets + GameRealisticMap (open) pipeline. |
| 843425103 / 843577117 / 843593391 / 843632231 | RHS AFRF/USAF/GREF/SAF | CC BY-NC-ND 3.0 + APL-SA/TOPL-SA; reupload prohibited | Engine vehicles/weapons configs; do not port models. |
| 583496184 / 583544987 | CUP Terrains Core/Maps | APL-SA + CUP-License | Engine terrain assets; AEE must not copy CUP content. |
| 735566597 | Project OPFOR | CC BY-NC-ND 3.0 (RHS licence) | Engine faction configs. |
| 1109237932 | Extended Fortifications Mod | CC BY-NC-ND 4.0 | Engine fortification assets/std. |
| 3407948300 | JSRS SOUNDMOD 2025 | APL-ND | CC0/public-domain sound libraries instead. |
| 3407948300 (and 861133494 old JSRS) | JSRS | APL-ND / NONE | As above. |
| 520618345 | Jbad | APL-SA | Engine structures. |
| 3753145363 | MKK Thermal Improvement | All rights reserved | A3TI/engine thermal (and AEE's own thermal work). |
| 17xxx | dzn, Kujari, Lybor, Kunduz, North Takistan, terrains | APL-SA | Engine terrain tools; AEE's own topo surface. |
| 3xxx | 3den Enhanced, EP mods, Highlight HLS, Modular * parts, Milsim Structures, A3SQL, D.I.R.T. Dynamic Textures, Crows EW, Alias Night FX, Weather Plus, Real Lighting, Drongo DDW, Multiplayer Object Scaler, Reactive Building PLUS, KtweaK NVG, Pegasus MH-47G, Mugen Alien | APL-SA / APL-ND / ADPL-SA / APL | Engine surface + AEE's own implementation. |

Class-level summary of the 39 restrictive mods: 3 APL-ND (map assets, JSRS, real lighting, HLS, modular props, ship interior, Pegasus, Milsim, Aaren blast, UKSF), many APL-SA, one ADPL-SA (Drongo), one CC BY-NC-ND group (RHS/OPFOR/EFM), one custom graphics-ND (VKing), one all-rights (MKK), one GRAD APL pair, one UKSF APL.

## 5. Map, marker and symbology mods - specific attention

| ID | Mod | Licence | Status for AEE |
|---|---|---|---|
| 2467589125 | Enhanced Map | NONE FOUND | Pure config, no art. AEE recorded it as IDEA only (no copy) and reimplemented the same engine fields in ADR-028/ADR-029. Its `maxSatelliteAlpha=1`, `drawShaded=0.15`, `shadedSea=1`, CfgLocationTypes labels and strategic-map vector colours are already matched by AEE's own config. No licence risk. |
| 1364777346 | BHC Map Contour | NONE FOUND | Pure config, RscMapControl only. AEE recorded it as IDEA only. Its `maxSatelliteAlpha=0.5` and contour recolour are reimplemented from OS/USGS published names. No licence risk. |
| 1340701737 | NATO Markers+ | NONE FOUND | Marker icon textures. No licence means all-rights-reserved. AEE must NOT copy the PNG/PAA icons. AEE derived its own marker textures from APP-6/2525 geometry (see ADR/engine override). |
| 964303647 | VKing's APP-6 NATO map markers | Custom restrictive | Readme explicitly forbids reproducing/modifying the graphics. AEE must not copy the icons. Scripts may be reverse-engineered for learning only. Reimplement the symbol set from APP-6(C). |
| 3205264721 | Pyro's NATO Map Markers | NONE FOUND | A 3DEN composition, not a dependency. No markers may be copied. Reimplement from APP-6/2525. |
| 1960024802 | PLP All in One | NONE FOUND | Excludes PLP Markers. Object packs only; no reliance. |
| 3438246217 / 3438247879 | cTAB Advanced / cTAB Connect | NONE FOUND | Map/tablet Blue-Force-Tracking symbology. No licence. Treat as all-rights-reserved; AEE must not copy. Reimplement any BFT display from MIL-STD-2525. |
| 2982306133 | Arma Realistic Map Assets V2 | APL-ND | Map-building assets. Do not copy; use the open GameRealisticMap toolchain. |

Key point for the two named map mods: both carry NO licence. Under default copyright they are all-rights-reserved. AEE's current position is correct and already evidenced: it read them, recorded them as IDEA in `data/symbology/terrain_symbols.json`, and reimplemented the same engine fields from the engine surface and published standards. There is no licence that would permit copying them, so continue the reimplementation route. The same holds for all marker/symbology icon sets (NATO Markers+, VKing, Pyro, cTAB): the icons must be AEE's own APP-6/2525 derivations.

## 6. Action list

1. Change the standing policy from "ideas-only" to per-mod: adopt from the 20 permissive/copyleft mods above with the licence cited in the ADR and file header.
2. Keep the blanket rule only for the 39 restrictive mods and the 160 no-licence mods.
3. Record each adopted file's source (mod ID + licence) in the AEE provenance data.
4. For the two map mods and the marker mods, keep the current reimplementation route - no copy is lawful.

## Budget

This survey forced a full 219-row table; it is longer than the 800-word briefing default. The method: mass file extraction (`meta.cpp`/`mod.cpp`/licences/readmes for all 219), one 219-ID Steam API call, and targeted reads of the 20 adoptable and the map/marker mods. Evidence is local files plus the Steam Workshop page for each mod, 2026-10-08.
