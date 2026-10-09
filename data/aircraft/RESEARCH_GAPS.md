# Aircraft corpus research gaps

This file lists what the corpus does not yet hold and the next source to try.
It is written by hand and it names a concrete next source for every gap. The
generated reports `SOURCE_GAPS.md` and `CLASS_MAPPING_GAPS.md` carry the same
gaps in table form.

## Dropped or unresolved class mappings

- `I_Plane_Fighter_04_F` (Saab JAS 39C Gripen, Jets DLC) is bound to
  `jas39c_gripen` from the Armed Assault Wiki identity lead. The class is a
  Jets DLC class, so the vanilla air config check is still pending. Next
  source: verify the class with `hemtt utils config derapify` on the
  `Air_F_Exp` or DLC addon.
- `O_Heli_Transport_02_F` (Mil Mi-26 Halo analogue) is not present in the
  deployed air config. The CSAT heavy transport classes that do exist are
  `O_Heli_Transport_04_F` and `O_Heli_Transport_04_covered_F`. Next source:
  confirm the Mi-290 Taru class name from the Helicopters DLC config and decide
  whether it maps to `mi26_halo` or needs its own entry.
- `Air` and `UAV` are token-level only. No concrete class binding names a real
  aircraft. Next source: a vanilla `Air` or `UAV` class that carries a real
  analogue.

## Wiki identity conflicts

The Armed Assault Wiki disagrees with three existing bindings. Both values are
kept in `data/aircraft/conflicts.json`. No binding changes until a tier 2 or
tier 3 source names the engine aircraft.

- `O_Plane_CAS_02_F`: corpus `su25_frogfoot`; the wiki names the To-199
  Neophron as the Yak-130.
- `C_Plane_Civil_01_F`: corpus `cessna_172_skyhawk`; the wiki names the Caesar
  BTT as the Cessna TTx.
- `O_Heli_Light_02_F`: corpus `light_utility_rotary` (Mil Mi-2); the wiki names
  the PO-30 Orca as the Ka-60 Kasatka.

## Entries that are leads

A lead holds no held runtime value and projects a labelled zero for every
runtime field. Ten entries are runtime-ready. The held-source ceiling is these
two:

- The held UH-60A operator's manual `TM 1-1520-237-10` states the rotor
  diameter and the maximum weight but no shaft horsepower, so
  `uh60a_black_hawk` stays a lead. Next source: a held engine document or a
  tier 4 manufacturer datasheet that states the T700-GE-700 rating.
- The held DTIC case history `ADA378729` states the engine model and the empty
  weight but no shaft power and no rotor diameter, so `rah66_comanche` stays a
  lead. Next source: a held rotorcraft datasheet that states the T800 rating
  and the rotor diameter.

The remaining first-slice leads are `a10a_thunderbolt_ii`, `su25_frogfoot`,
`l159_alca`, `su57_felon`, `ch47_chinook` and `aw159_wildcat`.

- Modern set: nineteen entries, one runtime-ready (`aw101_merlin`). Next source
  class: a US Army OPFOR/ODIN guide or a manufacturer datasheet that states the
  empty weight, the power and, for a rotor, the rotor diameter.
- Historical set: all sixteen entries are leads. Next source class: a US
  military flight manual (TO/TM), an FAA type certificate data sheet, or a
  public-domain DTIC report.

## Fixed-wing expansion leads

The fixed-wing expansion capture `data/aircraft/catalogue/fixed_wing_fw.json`
records the real fixed-wing types the roster's plane families represent, one
entry per real variant. Every entry is an identity lead: it holds no value, so
it names its next source here. The next source is named per group.

- US post-war and modern types (`f16a_block10`, `f16c_block52`, `f15a_eagle`,
  `f15e_strike_eagle`, `f14b_tomcat`, `fa18a_hornet`, `fa18c_hornet`,
  `fa18f_super_hornet`, `f4c_phantom_ii`, `f4j_phantom_ii`, `f5e_tiger_ii`,
  `f104g_starfighter`, `f105d_thunderchief`, `f100d_super_sabre`,
  `f86d_sabre`, `f84f_thunderstreak`, `f80c_shooting_star`, `a7d_corsair_ii`,
  `f8e_crusader`, `a1h_skyraider`, `a6a_intruder`, `a4e_skyhawk`, `t38a_talon`,
  `f111a_ardvark`, `b52h_stratofortress`). Next source: a US military flight
  manual such as `TO 1F-16C-1` for the F-16 or `TO 1F-15A-1` for the F-15, or
  an FAA type certificate data sheet.
- Soviet and Russian types (`mig17f_fresco`, `mig19s_farmer`, `mig21bis`,
  `mig21f13`, `mig23m_flogger`, `mig23ml_flogger`, `mig25_foxbat`,
  `mig27_flogger_d`, `mig29a_fulcrum`, `mig35_fulcrum_f`, `su7b_fitter`,
  `su17_fitter_c`, `su22_fitter_f`, `su24_fencer`, `su25sm_frogfoot`,
  `su25t_frogfoot`, `su27sk_flanker_b`, `su30mki_flanker_h`, `su33_flanker_d`,
  `su34_fullback`, `yak130_mitten`, `yak38_forger`, `mig31b_foxhound`). Next
  source: a Russian flight manual or an export operator's handbook, for example
  the Su-27SK flight manual.
- European types (`mirage_iii_e`, `mirage_2000c`, `mirage_f1_cr`,
  `sepecat_jaguar_gr1`, `panavia_tornado_gr4`, `harrier_gr9`, `bae_hawk_t1`,
  `folland_gnat`, `alphajet_e`, `saab_37_viggen`, `saab_35_draken`,
  `saab_105`, `aermacchi_mb339`, `amx_gibli`). Next source: a manufacturer
  datasheet from Dassault, Saab, BAE Systems, Leonardo or Panavia.
- Chinese types (`chengdu_j7_ii`, `shenyang_j8_ii`, `chengdu_j10a`). Next
  source: a manufacturer datasheet or an export operator's flight manual.
- Historical types (`hawker_hurricane_mk_i`, `hawker_typhoon_mk_ib`,
  `dehavilland_mosquito_b`, `avro_lancaster_b1`, `messerschmitt_bf109e`,
  `junkers_ju87d_stuka`, `focke_wulf_fw190d`, `messerschmitt_me262a`,
  `mitsubishi_a6m2_zero`, `p38j_lightning`, `p40e_warhawk`,
  `p61b_black_widow`, `b24j_liberator`, `b29_superfortress`, `f4u4_corsair`,
  `f6f5_hellcat`). Next source: a period flight manual or an FAA type
  certificate data sheet.

## Fields with no obtainable source

- The fixed-wing `drag_area_m2` is rarely published. It is optional, so the
  kernel default of 0.7 m2 stands. Next source: a NASA NTRS or DTIC
  wind-tunnel report that states the drag coefficient and the wing area.
- The `rated_power_w` of a jet needs a reference speed. The held A-10 and Su-57
  documents state thrust only. Next source: a held manual that states a cruise
  or maximum speed alongside the thrust.
- The `rotor_disc_area_m2` of the AW159 needs a held rotor diameter. Next
  source: the Leonardo AW159 datasheet.

## Rotary-wing expansion leads

The rotary-wing expansion capture `data/aircraft/catalogue/rotary_wing_rw.json`
records the real rotary types the roster helicopter and rotary UCAV families
represent, one entry per real variant. Five entries hold real values from the
held OPFOR Worldwide Equipment Guide and resolve their runtime fields. Every
other entry is an identity lead. It holds no value, so it names its next source
here.

- Real-value entries (`mi8_hip`, `mi17_hip`, `mi24p_hind_f`, `ka50_hokum`,
  `sa341_gazelle`). The held OPFOR Worldwide Equipment Guide states the empty
  weight, the shaft horsepower per engine and the main rotor diameter. Each
  entry therefore resolves `operating_weight_kg`, `rated_power_w` and
  `rotor_disc_area_m2`.
- US types (`uh1h_v`, `uh1n_twin_huey`, `uh1y_venom`, `oh58a_kiowa`,
  `oh58c_kiowa`, `oh58d_kiowa_warrior`, `ah64a_apache`,
  `ah64e_apache_guardian`, `ah1j_seacobra`, `ah1s_cobra`, `ah1w_super_cobra`,
  `ah1z_viper`, `ah6_little_bird`, `mh6m_mission_enhanced`, `uh60l_black_hawk`,
  `mh60r_seahawk`, `mh60g_pave_hawk`, `hh60g_pave_hawk`, `mh60s_knighthawk`,
  `sh60b_seahawk`, `ch47a_chinook`, `ch47b_chinook`, `ch47c_chinook`,
  `mh47g_chinook`, `ch53d_sea_stallion`, `ch53e_super_stallion`,
  `mh53e_sea_dragon`, `ch53k_king_stallion`, `uh72a_lakota`, `th67_creek`,
  `ch46_sea_knight`, `oh6a_cayuse`). Next source: a US Army operator's manual
  such as TM 1-1520-237-10, an FAA type certificate data sheet, or a maker
  datasheet.
- Soviet and Russian types (`mi35m_hind_e`, `mi171_hip_h`, `mi6_hook`,
  `mi14_haze`, `mi38_halo`, `mi24a_hind_a`, `ka27_helix`, `ka29_helix_b`,
  `ka32_helix_c`, `ka60_kasatka`, `mi4_hound`, `mi10_harke`). Next source: the
  held ODIN Worldwide Equipment Guide 2025, or a Russian flight manual.
- European types (`sa342_gazelle`, `sa330_puma`, `as332_super_puma`,
  `as532_cougar`, `as350_ecureuil`, `as355_twinstar`, `as365_dauphin`, `ec135`,
  `ec145`, `ec155`, `ec225_super_puma`, `sa321_super_frelon`, `nh90_nfh`,
  `ec665_tiger`, `lynx_has3`, `wg13_lynx`, `aw139`, `aw149`, `aw101_hm2`,
  `bo105`, `bk117`, `w3_sokol`). Next source: an EASA type certificate data
  sheet or a maker datasheet. The held EASA.R.013 already covers the AW101.
- Chinese and other types (`z8_haoyang`, `z9_haitun`, `z10_thunderbolt`,
  `z19_thunderbolt`, `z20_black_eagle`, `bell412`, `bell412ep`, `bell212`,
  `bell205`, `bell206b_jetranger`, `bell407`, `bell429`, `bell525`, `s76`,
  `s92`, `md902_explorer`, `mq8_fire_scout`, `mq8c_fire_scout`,
  `rq8_fire_scout`, `camcopter_s100`). Next source: a maker datasheet or an
  export operator's handbook.
