# Vehicle research gaps

This document records the researched candidates for the supported ground
classes. A candidate is a lead, not a full record. A lead names a possible
real vehicle and the evidence found so far. No field is fabricated: every
derived field names its formula and every absent field is a labelled zero.

The corpus holds four sourced catalogue entries. Every entry has a complete
identity, so each one emits a runtime row. None is runtime-ready yet, so
every row carries at least one labelled absent runtime field.
`data/vehicle/coverage.json` marks four tokens as `recorded`, one as
`lead` and two as `no_source`. `data/vehicle/records/` is empty. The
deliberate invalid fixture is under
`data/vehicle/fixtures/pilot-invalid.json`.

## 1. Coverage states

The ground tokens from `data/vehicle/classes.json` carry these states.

| Token | State | Entry |
|---|---|---|
| MRAP | recorded | Oshkosh M-ATV M1240 |
| Tracked_APC | recorded | M113A2 |
| Car | recorded | Honda Civic 6th generation 4 door Sedan |
| Truck | recorded | M923A2 |
| Wheeled_APC | lead | LAV-25 |
| Tank | no_source | none |
| Wheeled_APC_F | no_source | none |

A `recorded` token has an emitted runtime row and a class-map binding. A
`lead` token has a researched candidate and no recorded row. The guard
promotes a token to `recorded` when its row emits and its binding exists.

## 2. Lead: MRAP, Oshkosh M-ATV M1240

- Candidate. Oshkosh M-ATV, model M1240. Related marks M1240A1 and M1245.
- Source identity. TM 9-2355-335-10, Operator Manual,
  M1240/M1240A1/M1245, US Army, July 2012.
- Archive reference. Florida DMS LOGSA release 08-12, 99 pages.
  sha256 3b8b09ac1be2c069571be70628ad98f0d2e3dc35db79fec36ce56fdad1aaabec.
- Retrieved. 2026-09-24.
- Known fields. Identity from the cover page. Curb weight and gross vehicle
  weight only (Table 2, WP 0002, page 0002-10). Engine Caterpillar C-7,
  370 hp (276 kW), labelled maximum and not net (Table 13, page 0002-14).
  Transmission Allison 3500 SP, six speed automatic (Table 19). Tyre size
  code 395/85R20 and 16.00 R20 XZLTLRM (Table 15, page 0002-15). Snow
  chains optional, rear only (WP 0066).
- Missing fields. Operating weight. Ground clearance. Tyre width. Tyre
  diameter. The class-to-variant mapping.
- Conflicts. A tier-4 spec sheet gives ground clearance about 375 mm. A
  tier-3 tyre databook gives the 395/85R20 outside diameter 1189 mm and
  width 388 mm. A tier-4 page gives diameter 1176 mm and width 15.4 in.
  Both values sit below tier 2 and disagree. Keep both, never average.
- Why not runtime-ready. Operating weight, tyre width, tyre diameter,
  ground clearance and the class mapping are absent. The manual publishes
  maximum engine power, not net power. The lead fails five of the seven
  NRMM inputs.

## 3. Lead: Wheeled_APC, LAV-25

- Candidate. General Dynamics Land Systems LAV-25.
- Source identity. TM 08594A-10/1, Operator's Manual, Light Armored
  Vehicle LAV-25, US Marine Corps, 31 October 1984.
- Archive reference. WorldCat OCLC 220847406. Catalogue copy at the
  Australian War Memorial, LIB11434. The live document is not held.
- Retrieved. 2026-09-24.
- Known fields. The dossier names operating weight, power and
  transmission as the fields with a candidate source. The numeric values
  are not held and are not carried in this corpus.
- Missing fields. Ground clearance. Tyre width. Tyre diameter. The
  grousers or chains state. The net-power basis. The class-to-variant
  mapping.
- Conflicts. None recorded. The held evidence is a catalogue entry, not a
  full text.
- Why not runtime-ready. The candidate document is not held. Three fields
  have a candidate source at best. Four NRMM inputs are absent. The class
  mapping is not source-backed. The validator must reject this lead.

## 4. Lead: Tracked_APC, M113A2

- Candidate. M113A2, family of vehicles.
- Source identity. TM 9-2350-261-10, Operator's Manual, M113A2 FOV, US
  Army, 26 August 2005. It supersedes the 12 July 1990 edition.
- Archive reference. Public release, Distribution Statement A. Mirror
  https://www.liberatedmanuals.com/TM-9-2350-261-10.pdf.
  sha256 1b835e07eee998d7348fbee3ecabc603419f25ce8c6f7ba76b9397cd0b9aa974,
  28301752 bytes.
- Retrieved. 2026-09-24.
- Known fields. Ground clearance 17-1/8 in (43.48 cm). Overall width
  105-3/4 in. Length 191.00 in. Height 87-1/2 in. Gross weight with full
  load 25,007 lb (11,353 kg). Ground pressure 7.97 psi. Bridge class 13
  combat-loaded and 12 empty (WP 0002 00, TABULATED DATA, pages 0002 00-42
  and 0002 00-43). Engine, six cylinder V two-stroke diesel, 210 hp at
  2800 RPM, with no net or gross basis. Fording 40 in (page 0002 00-44).
  Track shoes, 63 left and 64 right (page 0002 00-46). Transmission,
  hydraulic with automatic range selection (WP 0001 00-1 and page
  0002 00-28). Track shoe types T130E1, T130 and T150. Grouser height
  wear limit 1/8 in for T130 only. T150 has no grouser (WP 0082 00).
- Missing fields. Operating weight. Net power with a stated basis. Track
  shoe width and pitch. Transmission model designation. The
  class-to-variant mapping.
- Conflicts. The manual publishes gross weight with full load only. The
  unit maintenance manual TM 9-2350-261-20-1 was checked and gives no
  transmission model and no track shoe width or pitch. TM 55-2350-224-14
  defines curb weight but gives no per-variant number.
- Why not runtime-ready. Operating weight, net power basis, track width
  and the class mapping are absent. A gross weight is not an operating
  weight. A maximum power is not a net power. The validator must reject
  this lead.

## 5. Deferral rule

A lead becomes runtime-ready only when every runtime field resolves to a
non-absent value with a source, a unit, a locator, a state and a grade.
The row emits before that point, with a labelled zero for each absent
field. A class-map binding carries the class link. The token is `recorded`
when the row emits and the binding exists.

## 6. Governing rules

JSP 945 for configuration management. Def Stan 05-138 for cyber security.
`data/vehicle/SCHEMA.md` holds the record contract and the fail-closed
rules.

## 7. National-manual route (task 19)

The maker-page route is exhausted for the remaining tanks and wheeled
armoured personnel carriers. Task 19 took the national-manual route that
worked for the UAZ-469 and the Ural-4320.

### 7.1 Uplifted to a held tier-2 national technical manual

| Catalogue entry | Held tier-2 source | Fields moved to documented |
|---|---|---|
| `btr_4` | `btr4_manual_2010`, BTR-4 operation manual В1318Е РЭ, 2010 | weight, length, width, height, wheelbase, track, ground clearance, road speed, range, climb and side-slope limits, engine model, published power, torque, transmission, gears, tyre size, tyre pressure, drivetrain |
| `t_64` | `t64a_technical_manual_1984`, T-64A technical description and operation manual, Book 1, 1984 | combat weight, length, width, height, ground clearance, road speed, range, climb gradient, fording depth, underwater-driving depth |
| `guarani` | `guarani_eb70_ci_11412`, EB70-CI-11.412, 2017 and `guarani_eb70_mt_11406`, EB70-MT-11.406, 2020 | weight, maximum road speed, range |

Every other field in these three entries keeps its tier-5 grade and is
named in the capture note.

### 7.2 No reachable tier-1 to tier-4 source (recorded gaps)

A real attempt was made for each target below. The next source class is
named. A maker page that already returned 403 or 404 is not retried.

| Target | Attempted | Next source class |
|---|---|---|
| `challenger_2` | The military-references.com tank library holds Challenger 1 AESPs (already held as `challenger_1_aesp_230_p_100_201`) but no Challenger 2 document. army.mod.uk and BAE Systems return 403. | A UK MOD AESP for the Challenger 2, or a tier-3 reference work |
| `leclerc` | No Leclerc technical manual in the military-references.com tank library, which holds no French national manuals. KNDS serves only a marketing flyer. | A French army TTA or Nexter technical manual, or a tier-3 reference work |
| `c1_ariete` | No Ariete document in the military-references.com library. Leonardo returns 404. | An Italian army technical manual, or a tier-3 reference work |
| `pt91_twardy` | No PT-91 document on archive.org or in the military-references.com library, which holds Soviet T-72 manuals only. The PT-91 is a Polish rebuild, so a T-72 manual is the wrong vehicle. | A Polish army technical manual, or a tier-3 reference work |
| `merkava_mk4` | No Merkava document on archive.org. Elbit and the Israeli MoD serve no reachable manual. | An Israeli defence technical manual or a tier-3 reference work |
| `arjun` | The Indian parliamentary record carries debate records, not a technical manual. DRDO returns 404. | A DRDO or Indian Army technical manual, or a tier-3 reference work |
| `rosomak` | The Polish MoND `Instrukcja Eksploatacji Pojazdu ROSOMAK` exists on Scribd, pdfcoffee and chomikuj but every copy is login-walled or 403. The archive.org collection holds no Polish armour. `rosomak.pl` and `rosomaksa.pl` serve no reachable specification. | A Polish army IPE/KTO technical manual (the `IPE-001.KTO/2006` catalogue entry names one), or a tier-3 reference work |
| `piranha_v` | `gdls.com` and `gdels.com` return 403. The held Piranha III brochure is the wrong mark, so it cannot uplift the Piranha V. | A GDELS Piranha V datasheet or a Swiss/Romanian army technical manual |
| `fahd` | No Fahd document on archive.org or in the military-references.com library. The Egyptian maker serves no reachable manual. | An Egyptian army technical manual, or a tier-3 reference work |

### 7.3 Held but not yet a full record

- `t_64`: the T-64A manual publishes no track shoe width and no track
  pitch in the held pages, so the two track fields stay absent.
- `guarani`: the held manuals publish no overall dimensions, no engine
  and no ground clearance, so those four fields stay at grade claimed.

## 8. Mud-accretion mass gap (W2)

The W2 runtime coupling ships a snow-load mass and a wet and ice grip
loss. It ships no mud-accretion mass. The omission is a documented
answer, not an open question.

- Finding. No published source gives the mud-accretion mass of an
  armoured fighting vehicle. No published source gives a per-curb mass
  fraction either.
- Search. The search covered US technical and field manuals, UK MOD
  publications and NATO publications. It covered terramechanics
  journals, SAE Mobilus, the NRMM and NG-NRMM work, and the DTIC and
  ERDC reports. It covered the agricultural tyre self-cleaning
  literature. No source class gave a vehicle-level figure.
- Nearest proxy. Fu, Li, Fu and Qiao (2023), "Development and
  verification of adhesion models for track shoes operating on clay
  soils", Biosystems Engineering 235:69-82, DOI
  10.1016/j.biosystemseng.2023.09.009. The article is closed access.
  The repository does not hold the paper, so the source registry does
  not carry it. A secondary summary reports a normal adhesion force of
  1.11 kPa. It reports an adhesive soil mass of 22.68 g per track shoe.
  The test soils are clay loam, sandy loam and loamy clay. The figure
  is not verified against the article body. It is a per-shoe laboratory
  figure. It is not a vehicle mass and it is not a curb fraction.
- Densities are not masses. Wet mud has a density of 1730 to 1840
  kg/m3. The USDA bulk density is 1330 kg/m3. A density needs a volume
  to give a mass. The repository holds no accreted-volume figure.
- Grading. A future value from Fu et al. (2023) alone is a lead at
  grade `claimed`. It reaches grade `documented` only when the held
  article body is read. It never fills a curb weight or an operating
  weight.
- Next source class. A vehicle-level mud-accretion measurement is the
  direct source. A terramechanics model that gives an accreted volume
  for a tracked or a wheeled vehicle is the next best. A manufacturer
  mud-pack mass or a cleaning specification is also a candidate.

## M1237 RG-33L "Plus"

Found by scanning the installed game content (tools/scan_game_classes.py):
four classes name the M1237 and no entry answers to it.

The mark is identified - warwheels_rg33l_designations states "they were
designated as the M1237 RG-33L 'Plus' vehicles" - but that page states no
figure for it, and the base RG-33L's weight is NOT the Plus's, because the
Plus is the uparmoured mark. An entry was NOT created on the base vehicle's
numbers.

Needed: a source stating the M1237's own weight, dimensions or power.

## 9. Armed Assault Wiki counterpart rows

The source is the research file `.omo/research/arma3-vehicle-counterparts.md`,
which reads the Armed Assault Wiki per-vehicle Trivia section. Every applied
row holds its section wikitext under `data/vehicle/sources/` or
`data/aircraft/sources/`. This section holds the rows that are NOT applied.

### 9.1 Contested: T-100 Varsuk (MBT_02_base_F, O_MBT_02_cannon_F)

One page gives two different answers, so both are held and neither is bound.

- Field Manual statement. *T-100 Varsuk*, Trivia,
  https://armedassault.fandom.com/wiki/T-100_Varsuk: "As stated in the Field
  Manual, the Varsuk is inspired by the real-world \"T-95\" main battle tank
  designed by Uralvagonzavod."
- Editor observation, same section: "However, both the Varsuk's turret and
  chassis bear a stronger resemblance to the \"Black Eagle\" tank, another
  cancelled concept MBT that was then-designed by Omsktransmash."
- Held bytes. `data/vehicle/sources/armedassault_t100_varsuk_trivia.wiki`,
  section 44.

No entry exists for the T-95 or the Black Eagle and none was created. The
class-table binding that pointed `O_MBT_02_cannon_F` at the M1 Abrams is
removed: no source names an Abrams for the Varsuk, and a contested row is not
a licence to keep a weaker claim. The class now binds nothing.

Known residual defect. The matcher answers "T-100 Varsuk" with the Toyota
T100 pickup, because both share the token `t100`. The corpus has no rule that
refuses a contested identity, so this is recorded and not patched by an
invented binding.

### 9.2 Rows graded `none`

- T-100X Futura (`MBT_02_railgun_base_F`). The page gives no real-world
  basis. It is a fictional railgun variant of the T-100.
- 2S9 Sochor (`MBT_02_arty_base_F`). The page states the design is not based
  on a real vehicle and names the 2S35 Koalitsiya-SV as a similar concept
  only.

Both get no entry and no binding.

### 9.3 Row with a named donor set and no possible binding: M4 Scorcher

`MBT_01_arty_base_F`. *M4 Scorcher*, Trivia,
https://armedassault.fandom.com/wiki/M4_Scorcher, section 45: "The Scorcher
itself is fictitious as the \"Mark IV\" variant of the Israeli \"Merkava\"
MBT never had a dedicated SPG configuration." The turret profile "seems to
be based on the \"A7\" variant of the \"M109 Paladin\"", and the howitzer is
drawn from the NLOS-C "Concept Technology Demonstrator".

The corpus holds the Merkava Mk IV and the M109A6. It does not hold the
M109A7 or the NLOS-C CTD, and the page states the vehicle never existed, so a
binding would assert an identity the page denies. No entry and no binding.

### 9.4 Donors the pages name that the corpus does not hold

These stay as notes on the bound parent entry. No entry was created for a
subsystem and no figure was invented for a missing variant.

- Patria AMV "Badger" IFV variant (Denel SOC Ltd). Bound parent: `patria_amv`.
- Namer "Achzaka" ARV prototype. Bound parent: `namer`. The held
  `achzarit` entry is a different conversion and is not bound.
- Marksman anti-aircraft turret (Marconi Electronic Systems). Named by the
  Cheetah and Tigris rows. Bound parents: `namer` and `bm2t_stalker`.
- Samson RCWS-30 turret (Rafael). Named by the Kamysh and Slammer rows.
  Bound parent: `bm2t_stalker`.
- Yak-131 single-seat variant. Bound parent: `yak130_mitten`.
- M109A7 Paladin. The held `m109a6_paladin` is the A6 mark and is not
  substituted.
- Leopard 2 "Revolution" upgrade package (Rheinmetall). Bound parent:
  `leopard_2a6`.

### 9.5 UGV classes bind no catalogue entry

The UGV Stomper and UGV Saif rows are bound to `darpa_crusher_ugcv` by the
display-name alias, and the concrete binding layer records nothing for
`UGV_01_base_F`, `UGV_01_rcws_base_F`, `O_UGV_01_F` and `O_UGV_01_rcws_F`.
The reason is the token table: `data/vehicle/classes.json` carries no UGV
token, the binding layer requires a class token, and an empty token fails
`validate_class_bindings.py`. A UGV token must be added to the supported set
before those four classes can bind.

### 9.6 Offroad display name

The Offroad row is bound to `offroad_q7_l200_composite` by class. The entry
carries `offroad` as a keyword, and `offroad` is a category word that
`gen_vehicle_data.py` drops from both the alias and the keyword list, so the
bare display name "Offroad" resolves to no entry. The composite carries no
other display-name alias. This is unchanged by the counterpart work and is
recorded here as a finding.

### 9.7 Donor entries hold an identity and no mass

Eleven applied counterparts hold an identity and no published mass, because
the held Trivia section states no mass, dimension, engine or tyre figure:

`hyundai_iblue_concept`, `bmw_x6_concept`, `mercedes_benz_sprinter`,
`yamaha_grizzly_450`, `zil_karatel`, `lgs_fennek_larv`, `otokar_arma_6x6`,
`bm2t_stalker`, `darpa_crusher_ugcv`, `parrot_ar_drone_2` and
`offroad_q7_l200_composite`.

The class bindings to those entries are recorded at the identity layer and
carry no figure. Two build steps expect a held real mass for every bound
class, and neither can emit for these:

- `gen_physics_config.py` stops with "no held real mass in
  data/physics/mass_calibration.json; the mass override cannot emit it".
- `gen_vehicle_mass_model.py` builds from the calibrated set only, so these
  classes carry no mass class.

The gap is a missing published mass, not a missing identity. A later capture
that holds a tier-1 to tier-5 figure for one of these vehicles closes it per
vehicle. Until then no mass is derived, substituted or invented, and the
generated physics header stays as it is.
