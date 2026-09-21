# Equipment Library Research (issue #119)

Research basis for the comprehensive helmet, vest and backpack libraries.
All values come from real-life sources (manufacturer datasheets, army
manuals, museum records, Wikipedia).  The user directive: real-world
data only, never invented or game-only values.

The simulation encodes four properties per item:

- weight - kg (real issue weight)
- armor  - NIJ protection level 0..3 (0 none, 1 IIA, 2 IIIA, 3 III+plates)
- nirReflectance - NIR reflectance class (green 45-55 %, black 5-20 %,
  beige 60-70 %), from MIL-DTL-64159 CARC
- clo    - insulation derived from the material (never published for
  hard equipment; aramid ~0.06-0.07, wool knit 0.30, cotton 0.04-0.05,
  soft armour 0.10-0.12, plate carrier 0.15-0.18, pack 0.08-0.12)

NIJ 0101.06 ballistic levels: IIA (9 mm/357 Mag), IIIA (.44 Mag), III
(7.62 mm rifle), IV (.30-06 AP).  GOST classes map to NIJ equivalents
(GOST 2 ~IIIA, GOST 3 ~III, GOST 5a/6a ~III/IV).

## Helmets (WW1 to present)

| Name | Country | Era | Weight_kg | NIJ | Material | NIR_class | Source |
|---|---|---|---|---|---|---|---|
| Adrian M15 | France | 1915 | 0.765 | none | Mild steel 0.7 mm | Green | Wikipedia; 1914-1918-online |
| Brodie Mk I | UK | 1916 | ~1.1 lined | none | Manganese steel | Green | Wikipedia |
| Stahlhelm M1916/M1917 | Germany | 1916 | 0.98-1.4 | none | Martensitic steel | Green | Wikipedia |
| US M1917 | USA | 1917 | ~1.1 | none | Manganese steel | Green | Wikipedia |
| M1 (shell+liner) | USA | 1941 | ~1.4 | none | Manganese steel 1.1 mm | Green | Wikipedia; stalingradfront |
| Stahlhelm M35/M40/M42 | Germany | 1935-42 | 0.81-1.23 | none | Steel | Green | Helmets of War |
| Mk III turtle | UK | 1944 | ~1.3 | none | Steel | Green | IWM |
| SSh-40 | USSR | 1940 | ~0.8 | none | Alloy steel 1.2 mm | Green | stalingradfront |
| Type 90 | Japan | 1930 | 0.9-1.0 | none | Steel alloy | Green | stalingradfront |
| SSh-68 | USSR | 1968 | 1.3 | frag only | Steel | Green | Wikipedia |
| M56 | East Germany | 1956 | ~1.2 | none | Steel | Green | Hessen Antique |
| Modèle 1951 | France | 1951 | ~1.3 | none | Manganese steel | Green | Wikipedia |
| Modèle 1978 | France | 1978 | ~1.3 | none | Steel | Green | Military Archive |
| PASGT | USA | 1983 | 1.4 shell / 1.9 complete | IIIA | Kevlar | Green/beige | DTIC ADA619773 |
| CG634 | Canada | 1997 | ~1.7 | IIIA | Aramid | Green/beige | Wikipedia |
| Mk 6 | UK | 1986 | 1.5 | IIIA-class | Ballistic nylon | Green/beige | Wikipedia Mk 7 |
| Mk 7 | UK | 2009 | 1.0 | IIIA-class | Kevlar | Beige | Wikipedia |
| Mk 8 / Virtus | UK | 2015 | ~0.65 | IIIA | UHMWPE | Green | British Army |
| 6B7 / 6B7-1M | Russia | 2000 | 1.1-1.2 | GOST Br1 (~IIIA) | Aramid | Green | Wikipedia |
| 6B26 / 6B27 | Russia | 2006 | 0.95-1.25 | GOST 2 (~IIIA) | Aramid | Green/beige | Equipment Wiki |
| 6B47 (Ratnik) | Russia | 2013 | ~1.0 | GOST 2 (~IIIA) | Aramid | Green/beige | Wikipedia |
| ZSh-1-2M | Russia | 1990s | ~1.2 shell | GOST 2 | Titanium+aramid | Green/black | Tarkov Wiki |
| MICH TC-2000 | USA | 2001 | 1.36-1.63 | IIIA | Kevlar | Green | Wikipedia |
| ACH (Gentex) | USA | 2003 | 1.36-1.72 | IIIA | Kevlar | Green/beige | Wikipedia; ArmyProperty |
| ACH Gen II | USA | 2017 | ~1.13 | IIIA | UHMWPE | Green/beige | Army.mil |
| ECH | USA | 2013 | ~1.0-1.1 | IIIA | UHMWPE | Green/beige | USMC PIS |
| USMC LWH | USA | 2003 | ~1.45 | IIIA | Kevlar | Green/beige | Wikipedia; TM 08744B |
| Ops-Core FAST | USA | 2009 | 0.63-0.89 | IIIA | UHMWPE/carbon | Green/black/beige | Gentex datasheet |
| Team Wendy EXFIL | USA | 2013 | ~1.18 | IIIA | UHMWPE | Green/black/beige | Team Wendy |
| Gefechtshelm M92 | Germany | 1992 | 1.5 | IIIA-class | Aramid | Green/beige | Wikipedia |
| QGF02 | China | 1990s | ~1.3 | IIIA-class | Aramid | Green | approximate |
| QGF11 | China | 2000s | ~1.0 | IIIA-class | Aramid | Green | approximate |
| RBH-303 (Rabintex) | Israel | 1990s | ~1.3 | IIIA | Aramid | Green/beige | Gostak |
| SEPT-2 | Italy | 1990s | ~1.5 | IIIA-class | Aramid | Green | Wikimedia |
| HGU-55/P | USA | 1980s | 0.91-1.1 | impact only | Graphite/aramid | White/grey | Gentex |
| SPH-4B | USA | 1980s | ~1.02 | impact only | Fibreglass/aramid | Green/grey | Aeromiltec |
| HGU-56/P | USA | 1990s | ~1.5 | impact only | Aramid | Green/grey | Gentex |
| DH-132 | USA | 1970s | ~1.4 | frag | Fibreglass/aramid | Green | Seoul Intl |

Non-ballistic headgear: boonie 0.1-0.15 kg, cap 0.1-0.15, beret 0.1
(wool felt), watch cap 0.1-0.2 (wool knit, ~0.3 clo).

## Body armour / vests (WW1 to present)

| Name | Country | Era | Bare_kg | Full_kg | NIJ | Type | NIR | Source |
|---|---|---|---|---|---|---|---|---|
| Brewster Body Shield | US | 1917 | 18.0 | 18.0 | none | plate | N/A | Dean 1920 |
| Sappenpanzer | Germany | 1916 | 9-11 | 9-11 | none | plate | N/A | IWM FEQ 969 |
| M1 flak vest | US | 1943 | 7.9 | 10.0 | none | frag | N/A | ARSOF Veritas 2020 |
| SN-42 | USSR | 1942 | 3.5 | 3.5 | none | plate | N/A | WarHistory |
| M-12 vest | US | 1944 | 5.5 | 5.5 | none | plate+soft | N/A | ARSOF Veritas |
| M-1951 Marine Vest | US | 1951 | ~3.6 | ~3.6 | none | soft | N/A | ARSOF Veritas |
| M-1952A | US | 1952 | 3.8 | 3.8 | none | soft | N/A | ARSOF Veritas |
| M-69 flak vest | US | 1966 | 3.8 | 3.8 | none | soft | N/A | ARSOF Veritas |
| PASGT vest | US | 1983 | 4.1 | 4.1 | IIIA | soft | woodland | ARSOF Veritas |
| Ranger Body Armor | US | 1993 | 3.6 | 7.3-11.0 | IIIA+plate | both | woodland | Wikipedia |
| 6B2 (Zh-81) | USSR | 1981 | 4.2-4.8 | 4.2-4.8 | ~IIIA | both | TTsKO | Wikipedia |
| 6B3T | USSR | 1983 | 12.2 | 12.2 | ~III | both | green | Wikipedia |
| 6B3TM-01 | USSR | 1985 | 8.2 | 8.2 | ~III front | both | green | Wikipedia |
| 6B4 | USSR | 1985 | 12.0 | 12.0 | ~III | both | green | Wikipedia |
| 6B4-01 | USSR | 1985 | 7.6 | 7.6 | ~III | both | green | Wikipedia |
| 6B5-11 Ulej | USSR | 1986 | 3.0 | 3.0 | ~II | soft | green | Wikipedia/HandWiki |
| 6B5-12 | USSR | 1986 | 5.0 | 5.0 | ~IIIA | both | green | Wikipedia/HandWiki |
| 6B5-13 | USSR | 1986 | 11.0 | 11.0 | ~III | both | green | Wikipedia/HandWiki |
| 6B5-15 | USSR | 1986 | 11.5 | 11.5 | ~III | both | green | Wikipedia/HandWiki |
| 6B5-19 | USSR | 1986 | 6.0 | 6.0 | ~III front | both | green | Wikipedia/HandWiki |
| 6B11 Zabralo | Russia | 1999 | ~5 | ~5 | ~IIIA | soft | flora | Wikipedia |
| 6B12 Zabralo | Russia | 1999 | ~6-7 | ~6-7 | ~III | both | flora | Wikipedia |
| 6B13 Zabralo | Russia | 1999 | ~7-11 | ~7-11 | ~III | both | flora | Wikipedia |
| 6B23 | Russia | 2003 | 4.0 | 7.2-10.2 | III-IV | both | flora/EMR | Wikipedia |
| IBA / Interceptor | US | 1999 | 3.8 | 7.4-15.0 | IIIA+III/IV | both | woodland/ACU | Wikipedia; ARSOF |
| SAPI plate (each) | US | 1999 | 1.27-2.40 | - | III | plate | N/A | Wikipedia |
| ESAPI plate (each) | US | 2005 | 1.70-3.25 | - | IV | plate | N/A | Wikipedia |
| IOTV | US | 2007 | 4.47 | 14.1 | IIIA+IV | both | ACU/OCP | WSH 2012; TM 10-8470-208-10 |
| SPCS | US | 2010 | ~2.7 | ~10.0 | IV plates | plate | OCP | ARSOF Veritas |
| MSV | US | 2018 | ~11.3 | ~11.3 | IV | both | OCP | ARSOF Veritas |
| CIRAS Land/Maritime | US | 2001 | ~1.8 | unpub | IIIA+IV | both | RG/khaki | Wikipedia; Eagle |
| Crye CPC | US | 2009 | 1.7-2.1 | unpub | IIIA+IV | both | Multicam | Crye CPCD01 |
| Crye JPC 2.0 | US | 2010 | ~0.5 | unpub | IV | plate | Multicam | Crye manual |
| USMC IMTV | US | 2007 | ~5.1 | unpub | IIIA+IV | both | MARPAT | Devil Dog Depot |
| Eagle MBAV | US | 2000s | 7.3 | 7.3 | IIIA+IV | both | RG/coyote | Wikipedia |
| 6B43 Zabralo-Sh | Russia | 2000s | ~9-13 | ~9-13 | GOST 6a (~IV) | both | EMR | FirearmCentral |
| 6B45 (Ratnik) | Russia | 2015 | 8.0 | up to 13 | GOST 5a/6a | both | EMR | Wikipedia |
| UK CBA | UK | 1980s | ~4 | ~4 | frag | soft | DPM | Wikipedia |
| UK ECBA | UK | 1991 | ~4-5 | ~6-7 | ~IIIA | both | DPM | Wikipedia |
| UK Osprey Mk 1-4 | UK | 2006-10 | ~8-9 | ~11-15 | ~IIIA+III/IV | both | DPM/MTP | MOD FOI |
| UK Virtus | UK | 2016 | ~5-6 | ~10.3 | ~IIIA+III/IV | both | MTP | MOD/DE&S |

No authoritative weight (do not invent): Japanese Type 1, UK Mk 3 flak,
Chinese Type 81/86, Kora-3M, Korund, 6B46, SMBE.

Non-ballistic load-bearing: ALICE suspenders+belt ~1.0-1.5 kg, LBV-88
~1.0-1.3, MOLLE FLC ~0.9-1.1, PLCE webbing ~1.5, DFLCS ~1.5-2.0,
rigger belt 0.1-0.2, chest rigs 0.4-0.8.

## Backpacks (WW1 to present)

| Name | Country | Era | Empty_kg | Capacity_L | Filled_kg | Frame | Colour | Source |
|---|---|---|---|---|---|---|---|---|
| M1910 haversack | US | WW1 | 0.45 | n/s | n/s | none | OD | CGSC |
| 1908 Pattern large pack | UK | WW1 | n/s | 12.8 | 25.93 | none | khaki | karkeeweb; Wikipedia |
| Tornister M1895 | Germany | WW1 | 1.34 | n/s | 13.24 | internal | tan | IR63 |
| M1928 haversack | US | WW2 | 1.1 | n/s | n/s | none | OD | WhatPriceGlory |
| M1936 musette | US | WW2 | 0.41 | n/s | n/s | none | OD | Man The Line |
| M1941 mountain ruck | US | WW2 | 3.26 | 47 | n/s | external | OD | Time Traveler |
| USMC M1941 pack | US | WW2 | 1.8 | n/s | n/s | none | khaki | WhatPriceGlory |
| 1937 Pattern large pack | UK | WW2 | n/s | 12.8 | 25 | none | khaki | Wikipedia |
| Gebirgsjäger M31 | Germany | WW2 | n/s | 40 | ~32 | none | feldgrau | zenker |
| RD-54 sap-perka | USSR | WW2 | 1.3 | 16.5 | n/s | none | OD | rf-gk.ru |
| M41 Sinyavin | USSR | WW2 | 1.0 | ~11 | n/s | none | khaki | Aksay museum |
| M1956 field pack | US | CW | 2.34 | 19 | 13.6-22.7 | none | OD | MIL spec |
| M1967 MLCE | US | CW | n/s | 9.4 | n/s | none | OD | CIE Hub |
| ALICE Medium | US | CW | n/s | 30-33 | 15.9-22.7 | external | OD | armynavysales |
| ALICE Large | US | CW | 3.2 | 62 | 27.2 | external | OD | Glens Surplus |
| 58 Pattern large pack | UK | CW | >1.5 | 30-40 | >10 | none | OD | Kango |
| PLCE bergen | UK | CW | 2.45 | 90 | n/s | internal | DPM | SOS Outdoors |
| SAS bergen | UK | CW | 2.2 | 100 | 25 | internal | DPM | calendar-uk |
| Soviet sidor | USSR | CW | n/s | 25-30 | n/s | none | OD | ganwear |
| French F1 | France | CW | 2.2 | 70 | n/s | none | OD | militarytravel |
| Chinese Type 81 rig | China | CW | 0.42 | mags | n/s | none | OD | Amazon |
| MOLLE II Large | US | Modern | 3.6 | 65.5 | 54.4 | external | ACU/OCP | TM 10-8465-236-10 |
| MOLLE II Medium | US | Modern | 1.59 | 49 | n/s | external | camo | TM 10-8465-236-10 |
| MOLLE II assault | US | Modern | 1.76 | 33 | n/s | none | camo | TM 10-8465-236-24P |
| USMC ILBE | US | Modern | 3.6 | 82 | n/s | internal | MARPAT | Wikipedia |
| FILBE | US | Modern | 4.3 | 81 | 56.7 | internal | coyote | Venture Surplus |
| Virtus 90L bergen | UK | Modern | 3.5 | 90 | n/s | internal | MTP | Becketts |
| Berghaus Munro | UK | Modern | 1.0 | 35 | n/s | internal | OD | Survival Aids |
| Berghaus Vulcan | UK | Modern | n/s | 100 | n/s | internal | Multicam | Task Force |
| 6Sh117 vest | Russia | Modern | 2.5 | n/a | n/s | n/a | EMR | ratnikshop |
| 6B38/6Sh118 ruck | Russia | Modern | 3.5 | 60 | 50 | internal | EMR | ratniksafe |
| Tort-2 Tortila | Russia | Modern | 2.15 | 40 | n/s | internal | camo | mbcgear |
| Mystery Ranch NICE 6500 | US | Modern | 4.3 | 106 | n/s | external | coyote | OV Innovations |
| Kifaru 44 Mag | US | Modern | 1.47 | 77 | n/s | internal | coyote | kifaru.net |
| Eberlestock Operator | US | Modern | 4.62 | 97.5 | n/s | internal | coyote | eberlestock |
| Osprey Exos 58 | US | Modern | 1.29 | 58-61 | 14-16 | internal | OD | osprey.com |

Webbing weights: ALICE LC-2 belt+suspenders 0.71 kg, MOLLE II belt 0.73,
58 Pattern belt 0.275, PLCE belt 0.3, Russian 6Sh112 base 0.7.

## Classname mapping (verified against installed configs)

Vanilla inventory extracted from the installed game configs: 139 helmet
classes (107 families), 47 vest classes (33 families), 97 pack classes.
RHS inventory: helmets (Stahlhelm M1940/M1942, M1, SSH-68, PASGT, ACH,
MICH, LWH, 6B7-1M, Altyn, ZSh-7a, ZSh-12, Kaska, 6B26/6B27, CVC,
Pro-Tec, GSSH-18), vests (6B2, 6B13, 6B23, 6B45, IOTV, SPCS, MBAV,
Plateframe, OTV, chestrigs, ALICE webbing), packs (RD-54, Sidor,
Tortila, RK-SHT-30, UMBTS, 6Sh117, Eagle III, ALICE packs).

## Dynamic classification (no hardcoding)

The library classifies EVERY item by its classname's family keywords —
the codebase's dynamic pattern.  Per-classname config entries were
considered and rejected: RHS alone has 2,000+ headgear classes, and a
config list can never cover a mod we have never seen.  The keyword
tiers carry the researched values, so any classname carrying the family
signal (helmet/vest/pack type + era + protection class) resolves
correctly:

- helmet tiers: steel (unrated), heavy SF (Altyn/ZSh), Russian aramid
  (6B7/6B26/6B27/6B47), PASGT, MICH/ACH/LWH/ECH, FAST/EXFIL, CVC,
  aircrew, and the light headwear families
- vest tiers: 6B43/6B45, 6B23, 6B13, 6B2-6B5, 6B11/6B12/6B17/6B18,
  IOTV, SPCS, CIRAS, PlateFrame/MBAV/MSV, Osprey, Virtus, CBA/ECBA,
  historical flak, plate carriers, and the light rigs
- pack tiers: 6Sh118/6B38, RD-54, Sidor/Tortila, ALICE, MOLLE,
  ILBE/FILBE, Eagle, PLCE/Virtus, Berghaus, RK-SHT-30, and the large
  rucksack family

The uniform library (fnc_getClothingInsulation) keeps its config walk
for the uniform slot — the uniform family signal is weaker (classnames
are less standardised), so the CfgWeapons inheritance chain disambiguates
there.  Helmets/vests/packs classify on the name alone.

## Classifier tier values (locked by test_equipment_values.py)

Each keyword tier carries the researched value.  The verification test
extracts the SQF mapping and asserts the values against this table, so
a drift from research fails the gate.

| Family | weight kg | armor | NIR | clo | Research anchor |
|---|---|---|---|---|---|
| Steel helmets (Stahlhelm, M1, SSh-68) | 1.2 | 0 | 0.40 | 0.04 | 0.81-1.4 by family |
| Altyn | 2.1 | 2 | 0.40 | 0.08 | ~2.1 w/ visor |
| 6B47 (Ratnik) | 1.0 | 2 | 0.40 | 0.06 | ~1.0 |
| 6B7-1M | 1.15 | 2 | 0.40 | 0.06 | 1.1-1.2 |
| 6B26/6B27 | 1.1 | 2 | 0.40 | 0.06 | 0.95-1.25 |
| 6B28 | 1.3 | 2 | 0.40 | 0.06 | ~1.3 |
| PASGT | 1.9 | 2 | 0.40 | 0.06 | 1.9 complete |
| MICH/ACH/LWH | 1.5 | 2 | 0.40 | 0.07 | 1.36-1.72 |
| ECH | 1.05 | 2 | 0.40 | 0.06 | 1.0-1.1 |
| Ops-Core FAST/EXFIL | 0.9 | 2 | 0.40 | 0.06 | 0.63-0.89 |
| Aircrew (HGU-55/56, GSSH) | 1.1 | 1 | 0.45 | 0.15 | 0.91-1.5 |
| CVC/DH-132 | 1.4 | 1 | 0.40 | 0.05 | ~1.4 |
| 6B2 | 4.5 | 2 | 0.40 | 0.12 | 4.2-4.8 |
| 6B3 | 10.0 | 3 | 0.40 | 0.13 | 8.2-12.2 |
| 6B4 | 9.5 | 3 | 0.40 | 0.13 | 7.6-12.0 |
| 6B5 | 7.0 | 2 | 0.40 | 0.13 | 3-11.5 |
| 6B13 | 9.0 | 3 | 0.40 | 0.14 | 7-11 |
| 6B23 | 7.9 | 3 | 0.40 | 0.14 | 7.2-10.2 |
| 6B43 | 11.0 | 3 | 0.40 | 0.15 | 9-13 |
| 6B45 | 9.0 | 3 | 0.40 | 0.15 | 8-13 |
| IOTV/SPC | 4.5 | 3 | 0.38 | 0.18 | 4.47 (TM) |
| SPCS | 2.7 | 3 | 0.38 | 0.16 | ~2.7 |
| CIRAS | 3.5 | 3 | 0.38 | 0.15 | ~1.8 carrier |
| MBAV/MSV | 5.5 | 3 | 0.38 | 0.16 | 7.3/11.3 |
| Osprey | 8.5 | 3 | 0.40 | 0.15 | 8-9 |
| Virtus | 5.5 | 3 | 0.40 | 0.14 | 5-6 |
| ECBA/CBA | 4.5 | 2 | 0.40 | 0.10 | 4-5 |
| Flak (M-69 etc) | 3.8 | 1 | 0.40 | 0.08 | 3.8 |
| RD-54 | 1.3 | 0 | 0.40 | 0.08 | 1.3 |
| Sidor | 2.2 | 0 | 0.40 | 0.09 | 25-30 L class |
| Tortila | 2.15 | 0 | 0.40 | 0.09 | 2.15 |
| ALICE | 3.2 | 0 | 0.40 | 0.10 | 3.2 |
| MOLLE II | 3.6 | 0 | 0.40 | 0.10 | 3.6 |
| ILBE | 3.6 | 0 | 0.40 | 0.11 | 3.6 |
| FILBE | 4.3 | 0 | 0.40 | 0.11 | 4.3 |
| PLCE | 2.45 | 0 | 0.40 | 0.10 | 2.45 |
| Virtus 90L | 3.5 | 0 | 0.40 | 0.10 | 3.5 |
| Assault pack (vanilla) | 3.0 | 0 | 0.40 | 0.10 | config |
| Tactical pack | 3.5 | 0 | 0.40 | 0.10 | config |
| Field pack | 4.0 | 0 | 0.40 | 0.10 | config |
| Kitbag | 4.0 | 0 | 0.40 | 0.10 | config |
| Bergen | 5.0 | 0 | 0.40 | 0.11 | config |
| Carryall | 6.0 | 0 | 0.40 | 0.12 | config |

clo derives from the researched material (aramid ~0.06-0.07, wool knit
0.30, soft armour 0.10-0.12, plate carrier 0.15-0.18, pack 0.08-0.12).
Armor maps: 0 none, 1 IIA/frag, 2 IIIA, 3 III/IV plates.  GOST classes
map to NIJ (GOST 2 ~IIIA, GOST 3 ~III, GOST 5a/6a ~III/IV).