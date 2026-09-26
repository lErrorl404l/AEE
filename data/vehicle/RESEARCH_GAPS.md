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
