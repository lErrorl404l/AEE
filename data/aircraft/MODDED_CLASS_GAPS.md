# Modded class gaps: the aircraft that stay unnamed

This record lists every modded aircraft class that the identity ladder cannot
name, with the reason it stays open and the evidence for that reason. The
coverage measurement reads the list. The lock that fails when a class moves is
`tools/tests/test_mod_class_resolution.py`.

## How the split is measured

A class is base game when the PBO that declares it sits in the game's own
`Addons` directory (196 PBOs). Every other declaring PBO is modded. The
inheritance chain is read from the full scan, so a modded class keeps a base
game parent, and only a class declared by a modded PBO is scored. The method
is stated in `data/coverage/README.md`.

The 2026-10-20 scan of the installed content scores 223 modded aircraft
classes. The catalogue names 181. Forty-two stay open. The base game scores
40 of 43.

| Group | Classes | Why the group stays open |
|---|---|---|
| Arma 3 fiction and a loadout | 10 | The F/A-181 Black Wasp II is Arma 3's own fictional fighter, and its text names a weapon loadout ("10x GBU-12"), not a designation. The shared configuration words ("cas", "bomber", "heavy") are keywords of several catalogue entries, so the keyword layer ties. |
| No published designation | 8 | The ArmaFPV Crocus drones carry no designation any published source holds, so a row would invent one. The same reason is recorded in `data/vehicle/MODDED_CLASS_GAPS.md`. |
| A shared name held as an alias of two marks | 5 | `FIR_ECM_Dummy_1` ties on `falcon` (two F-16 marks), `FIR_ECM_Dummy_2` on `hornet` (two F/A-18 marks), `CBRN_Mohawk` on `merlin` (two AW101 marks), `vtx_HH60` on `pavehawk` (two H-60 marks) and `vtx_H60_base` on `black hawk` (two UH-60 marks). The alias layer runs before any keyword, and a tie there is final. |
| AH-64 mark against mark | 8 | Three catalogue marks carry `ah64`, and `ah6` is a substring of every AH-64 query, so the keyword layer always ties. A family entry owning `ah64` would leave `ah6` as the only candidate and answer the AH-6 Little Bird for a class displaying `AH-64`; it is refused for that reason. |
| The Mi-8MTV-3 mark is not held | 6 | `mi8` names the Mi-8T and the Mi-8AMTSh, and the Mi-17 entry derives `mi8m` from its published `mi-8mt` alias. A Mi-8 family entry owning `mi8` would leave `mi8m` alone and answer the Mi-17 for a Mi-8MTV-3, which is a different airframe. |
| A role word several entries carry | 4 | `cas` is a keyword of the A-10 and the Su-25, and `gunship` of the Ka-50, the Mi-24P and the Mi-28. The keyword layer ties on the role word and the family rung is never reached. |
| The MH-60 designation | 1 | `121_soar_hibyrd_slick` displays `[SOAR] Hibyrd's MH-60M`. `mh60` is shared by four MH-60 marks, and `mh6` is a substring of `mh60m`, so a MH-60 family entry would answer the MH-6M. |

## The family rung of 2026-10-20

The family rung answers a class whose text names a family and no mark. It runs
last, at confidence 7, over a separate `_families` table that no higher rung
reads: a family entry is identity-only, names the family and no mark,
publishes the family designation as its keyword, and answers only when it is
the single family row that matches.

Nine entries carry the aircraft corpus: `uh1_family`, `uh60_family`,
`hh60_family`, `ah1_family`, `mi24_family`, `su25_family`, `ch53_family`,
`ch47_family` and `mig29_family`. Each names the designation its member
entries publish in their canonical names, and no mark.

A designation a family entry owns is dropped from every mark row, and the
same word is removed from a mark's curated alias where one held it: `uh60`
left the UH-60A, `su25` the Su-25 and `ch47` the CH-47D. That is what lets
the ladder answer at all. While the AH-1Z mark carried the derived keyword
`ah1`, every query that named the AH-1 family tied at that layer and no mark
could answer.

| Classes | Entry that answers | Layer |
|---|---|---|
| `RHS_AH1Z`, `RHS_AH1Z_CS`, `RHS_AH1Z_GS`, `RHS_AH1Z_base`, `RHS_AH1Z_wd_CS`, `RHS_AH1Z_wd_GS` | `ah1z_viper` | keyword, on `ah1z` after `ah1` left the mark rows |
| `RHS_CH_47F_base`, `RHS_CH_47F_cargo_base`, `RHS_CH_47F_light` | `ch47f_chinook` | keyword, on `ch47f` |
| `RHS_Mi24_base`, `RHS_Mi24D_Base`, `RHS_Mi24D_Early_Base`, `RHS_Mi24P_AT_VVS_Base`, `RHS_Mi24V_Base` | `mi24p_hind_f`, `mi24d_hind_d`, `mi24v_hind_e` | keyword, on the mark's own `mi24p`, `mi24d` or `mi24v` |
| `RHS_Su25SM_Cluster_vvs`, `RHS_Su25SM_Cluster_vvsc`, `RHS_Su25SM_KH29_vvs`, `RHS_Su25SM_KH29_vvsc`, `RHS_Su25SM_vvs` | `su25sm_frogfoot` | keyword, on `su25sm`, which the class name carries |
| `RHS_UH1Y_base`, `RHS_UH1Y_FFAR`, `RHS_UH1Y_GS`, `RHS_UH1Y_UNARMED` | `uh1y_venom` | keyword, on `uh1y` |
| `RHS_UH60M`, `RHS_UH60M2`, `RHS_UH60M_ESSS`, `RHS_UH60M_ESSS2`, `RHS_UH60M_MEV`, `RHS_UH60M_MEV2`, `RHS_UH60M_base`, `vtx_UH60M_SLICK`, `vtx_UH60M_MEDEVAC` | `uh60m_black_hawk` | keyword, on `uh60m` |
| `rhs_mig29s_base`, `rhs_mig29sm_base` | `mig29s_fulcrum_c` | keyword, on `mig29s` |
| `rhs_uh1h_base`, `rhs_uh1h_hidf`, `rhs_uh1h_hidf_unarmed`, `rhs_uh1h_idap`, `rhs_uh1h_un` | `uh1h_iroquois` | keyword, on `uh1h` |
| `rhsusf_CH53E_USMC`, `rhsusf_CH53E_USMC_GAU21`, `rhsusf_CH53e_USMC_D_cargo`, `rhsusf_CH53e_USMC_cargo` | `ch53e_super_stallion` | keyword, on `ch53e` |

Forty-three classes closed and none stopped resolving. The check compared
`(class, source) -> entry` for all 1,344 scored classes before and after, so
the vehicle closures and every base-game class are unchanged with it.

Every closure answers at the keyword layer, and none at the family rung. The
mod class text names the mark even where its display name states the family:
`vtx_UH60M_MEDEVAC` displays `HH-60M MEDEVAC` and its class name states
UH-60M. The family entries are still what make the closures possible, because
the designation they own is what left the mark rows. No class in the table
needs the rung's own answer, and the rung is the only layer that would read a
family row if one did.

## What is refused, and why

- No AH-64, Mi-8, MH-60, F-16, F/A-18 or AW101 family entry. The measurement
  shows each would close a class to the wrong airframe: AH-6 for AH-64,
  Mi-17 for Mi-8MTV-3, MH-6M for MH-60M. The alias ties on F-16, F/A-18 and
  AW101 sit above the family rung, which a family entry cannot reach.
- No new mark entry. A Mi-8MTV-3 or an HH-60M row would publish a figure the
  corpus does not hold, and this work adds no figure.
- No change to the ladder, the tie rule or the scan rule. The runtime matcher
  is the specification.
