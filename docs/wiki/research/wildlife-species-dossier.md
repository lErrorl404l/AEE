# AEE Wildlife: Real Species and Acoustic Behaviour Dossier

Committed research for the wildlife ecology plan. Sourcing key: **[S]** sourced
and fetched this session. **[S-lit]** sourced to named literature reached
through a fetched page. **[R]** documented in a standard reference database.
**[U]** UNKNOWN, no source obtained. No figure is stated unless it is [S] or
[S-lit]. Every [U] entry stays marked.

Purpose: turn AEE's static wildlife soundscape into a species-level matcher.
Inputs are AEE's own biome/time/weather state. Output is a per-biome species
list plus the real on/off calling structure per species group.

Read-only research. No file under `/ext/Development/AEE` was modified.

Sourcing key:
- **[S]** sourced and fetched this session (URL in Sources).
- **[S-lit]** sourced to named literature reached through a fetched page's
  reference list (not the primary PDF itself).
- **[R]** range or behaviour documented in standard reference databases
  (IUCN Red List, xeno-canto); the exact figure is not fetched this session.
- **[U]** UNKNOWN. No source obtained. Do not treat as a value.

Rule for this dossier: no numeric figure is stated unless it is [S] or
[S-lit]. Where a real rule needs a number and none was obtained, the entry
reads [U] and the qualitative rule is given instead.

---

## 1. AEE state the matcher can read (verified from the code)

| Matcher input | Source in AEE | Notes |
| --- | --- | --- |
| Koppen biome code | `aee_core_biome`, `aee_weather_localBiome` | e.g. `Csa`, `Dfb` |
| Biome family | wildlife code, first letter | `a` tropical, `b` arid, `d`/`e` cold, else temperate |
| Night | `sunOrMoon < 0.5`; `aee_core_currentSunElevation` | sun elevation is real, not bool |
| Air temperature °C | `aee_core_currentTemperature` | drives insect stridulation |
| Wind m/s | engine `wind`; `aee_core_currentWindStr` | drives song suppression |
| Rain 0–1 | engine `rain` | drives masking and amphibian triggering |
| Overcast | `aee_core_overcast` | low light shifts crepuscular timing |
| Near water | `aee_weather_getCoastDistance` | water overlay |
| Vegetation score 0–1 | `terrainSignals` `vegVotes` | forest vs open |
| Disturbance 0–1 | `aee_ai_disturbance` | silences, spooks |
| Season / month | engine `date` | AEE has no single published season scalar; use mission date and Koppen seasonal test |

Gap to flag to the planner: AEE publishes no explicit `season` variable.
Season is derivable from `date` (month) and is already implied by the biome's
seasonal test in `fnc_classifyBiome`. The matcher should read month from
`date` and the Koppen second/third letter.

---

## 2. Per-biome species table

"Present" means the species is documented in that climate class [R].
"Absent" is the operator's explicit question: it does NOT occur there.
Presence is at the climate-class level, not at one map cell. Local water,
altitude and vegetation move a species within a class.

### 2.1 Tropical (Koppen A): Af, Am, Aw

AEE family `tropical`. Biome names: Af Tropical Rainforest, Am Monsoon
Tropical, Aw Tropical Savanna.

| Group | Present | Absent / not expected |
| --- | --- | --- |
| Birds, dawn | Hornbills (Bucerotidae), barbets and tinkerbirds, turacos (Af/Am), bulbuls, parrots, pigeons/doves; gibbons chorus (SE Asia, dawn) | Temperate dawn-chorus species (European robin, song thrush, blackbird) |
| Birds, day | Sunbirds, white-eyes, drongos, bee-eaters, kingfishers, raptors | Larks and wheatears of arid zones |
| Birds, night | Nightjars, owls (e.g. African wood owl, tropical screech owl), some frogmouths (Australia) | Most temperate owls |
| Insects | Cicadas (dominant daytime loud source; tropical peak diversity), katydids (Tettigoniidae), crickets (Gryllidae); many nocturnal | No seasonal cicada quietus of the temperate kind; cicadas call year-round where warm |
| Amphibians | Tree frogs (Hylidae/Rhacophoridae), poison frogs, many; strongly nocturnal, rain-triggered | Temperate frogs that need cold winter |
| Mammals | Bats (ultrasonic, mostly inaudible to humans), hyrax, some primates with loud calls | Wolves, deer of boreal zones |

Note Af has no dry season, so the insect chorus has no seasonal gap [R].
Aw has a strong dry season: cicadas and frogs are seasonal, tied to the wet
season [R].

### 2.2 Arid (Koppen B): BWh, BWk, BSh, BSk

AEE family `arid`. BWh Hot Desert, BWk Cold Desert, BSh Hot Semi-Arid, BSk
Cold Semi-Arid.

| Group | Present | Absent / not expected |
| --- | --- | --- |
| Birds, dawn | Larks (crested, desert), wheatears, sandgrouse (crepuscular), trumpeter finch, shrikes | Forest barbets, turacos, rainforest species |
| Birds, day | Doves (palm, laughing), raptors, bee-eaters, hoopoes | Waterfowl away from oases |
| Birds, night | Owls (little owl, eagle owl), nightjars (Egyptian) | Owls of closed forest |
| Insects | Crickets and katydids (strongly nocturnal), grasshoppers/locusts (diurnal stridulation), arid cicadas where trees/scrub exist (e.g. *Diceroprocta* in N America) | Cicadas in hyper-arid core with no woody host [R] |
| Amphibians | Spadefoot toads and other explosive breeders, only after rain, near water | Most frogs; no permanent-water breeders in BWh core |
| Mammals | Bats (ultrasonic), foxes, gerbils/jerboas (mostly silent) | Deer, wolves except at range edges |

Key arid rule: the frog and many insect sources are **ephemeral and rain-
triggered**, not steady [R]. A matcher must gate amphibians on rain, not on
temperature alone.

### 2.3 Temperate (Koppen C): Csa, Csb, Csc, Cfa, Cfb, Cfc, Cwa, Cwb, Cwc

AEE family `temperate` (the "else" branch). This is the best-documented
family for real soundscape work.

#### Csa / Csb / Csc: Mediterranean (dry summer)

| Group | Present | Absent / not expected |
| --- | --- | --- |
| Birds, dawn | Nightingale (*Luscinia megarhynchos*), the archetypal Mediterranean night/dawn singer; Sardinian warbler, cirl bunting, blackcap, common nightingale | Boreal species (brambling, redpoll) |
| Birds, day | Hoopoe, bee-eater, kestrel, stonechat, finches | Winter thrushes except on migration |
| Birds, night | European scops owl (*Otus scops*), insect-like whistle, nocturnal; little owl; nightjar | Tawny owl at higher altitude |
| Insects | Cicadas *Cicada orni* and *Cicada barbara* (very loud, hot daytime); tree crickets *Oecanthus*; bush-crickets; field crickets | Boreal bush-crickets; no cicadas above the tree line |
| Amphibians | Tree frogs (*Hyla*), toads, *Discoglossus*; breed in the cool wet winter/spring, so the chorus is a **winter–spring** event, not summer | Most breeding calls in high summer, Mediterranean frogs are drought-stressed then |
| Mammals | Bats (ultrasonic), foxes; small mammals mostly silent | n/a |

Mediterranean special: cicada calls peak in the hot dry months and stop in
the cool wet season, the inverse of the frog chorus [R]. A `Csa` matcher must
therefore run a summer insect layer and a winter amphibian layer.

#### Cfa / Cfb / Cfc: Oceanic / humid subtropical

| Group | Present | Absent / not expected |
| --- | --- | --- |
| Birds, dawn | Robin, blackbird, song thrush, wren, great tit, blue tit, chaffinch, blackcap, chiffchaff, dunnock; cuckoo (spring) | Mediterranean-only scops owl in the colder edge |
| Birds, day | Finches, tits, corvids | n/a |
| Birds, night | Tawny owl, little owl; nightjar (heath/forest edge); robin sings at night in lit areas [R] | n/a |
| Insects | Field crickets (*Gryllus*), bush-crickets, mole cricket; cicadas in the warmer Cfa margin | Cicadas thin out toward Cfb/Cfc |
| Amphibians | Common frog, common toad, newts; spring breeding; tree frogs in Cfa | n/a |
| Mammals | Bats (ultrasonic), fox, badger (mostly silent) | n/a |

#### Cwa / Cwb / Cwc: dry-winter, monsoon subtropical

| Group | Present | Absent / not expected |
| --- | --- | --- |
| Birds, dawn | Bulbuls, white-eyes, magpie-robin, laughingthrushes (Asia); strong pre-monsoon dawn chorus | European robin/blackbird as the dominant voices |
| Birds, night | Owls, nightjars | n/a |
| Insects | Cicadas with a **monsoon emergence**, synchronous and loud, then quiet in the dry winter; crickets and katydids | Winter insect chorus |
| Amphibians | Frogs breed with the wet summer monsoon; explosive | Winter breeding |
| Mammals | Bats, civets (mostly silent) | n/a |

### 2.4 Cold (Koppen D and E): Dfa–Dfd, Dsa–Dsd, Dwa–Dwd, ET, EF

AEE family `cold`.

#### Dfa / Dfb / Dsa–Dsd / Dwa / Dwb (warm-to-humid continental)

| Group | Present | Absent / not expected |
| --- | --- | --- |
| Birds, dawn | Thrushes, warblers, finches, vireos, orioles; very strong spring dawn chorus [S] | Mediterranean-only cicada-dependent species |
| Birds, night | Tawny/Ural/great grey owls, nightjar in the south | n/a |
| Insects | Field crickets, katydids, grasshoppers, **summer only**; the calling season is short | Cicadas absent in Dfb and colder [R] |
| Amphibians | Wood frog, spring peeper, chorus frogs (N America), common frog/toad (Eurasia); **explosive spring breeding**, then quiet | Mid-summer chorus |
| Mammals | Bats (ultrasonic), deer (alarm barks), wolves at range edge | n/a |

#### Dfc / Dfd: subarctic / severe continental

| Group | Present | Absent / not expected |
| --- | --- | --- |
| Birds | Spruce-forest species; brief but intense summer dawn chorus | Many temperate songbirds |
| Insects | Mosquitoes (flight buzz), some grasshoppers; crickets and katydids only in the brief warm season | Cicadas; long insect chorus |
| Amphibians | Wood frog, boreal chorus frog at the southern margin | Most frogs |
| Mammals | Bats (short season), small mammals | n/a |

#### ET: tundra

| Group | Present | Absent / not expected |
| --- | --- | --- |
| Birds | Snow bunting, Lapland bunting, ptarmigan, shorebirds (breeding) | All woodland songbirds |
| Insects | Mosquitoes, bumblebees; no crickets/cicadas | Crickets, katydids, cicadas absent |
| Amphibians | Wood frog only at the extreme southern margin | No amphibian chorus in ET core |
| Mammals | Lemmings, arctic fox (mostly silent) | n/a |

#### EF: ice cap

| Group | Present | Absent / not expected |
| --- | --- | --- |
| Birds | Coastal seabirds (fulmar, petrels) at the sea edge only | All land songbirds |
| Insects | None resident | All insects |
| Amphibians | None | All amphibians |
| Mammals | Polar bear, seals (mostly silent) | n/a |

Rule for `ET`/`EF`: the soundscape must be **sparse**. A dense bird or insect
chorus is wrong for these classes [R].

### 2.5 Water overlay (any biome, waterFrac > 0.5)

| Group | Present | Absent |
| --- | --- | --- |
| Birds | Gulls, terns, waders, ducks/geese, herons, kingfisher | n/a |
| Amphibians | Breeding frog/toad chorus (strongly seasonal and rain-dependent) | n/a |
| Insects | Dragonflies (mostly silent), some damselflies | Cicadas away from bankside trees |
| Mammals | Bats over water (ultrasonic) | n/a |

### 2.6 Settlement overlay

| Group | Present | Absent |
| --- | --- | --- |
| Birds | Swallows, house martins, swifts, house sparrows, starlings, pigeons, poultry, roosters | n/a |
| Mammals | Dogs, cats (mostly silent) | n/a |

---

## 3. Behaviour rules per species group

### 3.1 Birds

- **Diurnal / crepuscular / nocturnal.** Most songbirds are diurnal with a
  strong crepuscular peak (dawn, and a weaker dusk chorus). Nightjars and
  owls are nocturnal/crepuscular. In temperate countries the dawn chorus is
  a spring breeding-season phenomenon [S]. Robins sing at night in lit
  areas [R].
- **Seasonal.** Song peaks in the breeding season and is concentrated at
  dawn [S]. Migrants add voices in spring; song declines after pairing [S-lit].
  The tropical `Af` chorus has no cold-season gap; `Aw`, `Cwa` etc. gate
  insect and amphibian layers on the wet season [R].
- **Dawn-chorus order.** Birds with larger eyes and higher perches tend to
  sing first [S, Jamieson 2007]. This is real on/off structure that a
  matcher can vary by species, not one blended bed.
- **Temperature.** Cold nights suppress dawn song; the chorus is a warm-
  season, warm-morning event [R].
- **Wind and rain.** Wind severely degrades song in the open and attenuates
  lower frequencies [S-lit, Wiley et al.]. One secondary account states
  that above ~4 kHz attenuates from about 8 km/h and signal-to-noise drops
  about 23 dB by 15 km/h [S, secondary blog, treat the numbers as [U]
  until a primary is obtained]. Rain masks song, and masking worsens with
  intensity [S, secondary]. Behavioural result: birds sing less and shorter
  in strong wind and steady rain.
- **Gregariousness.** Many songbirds are territorial while breeding, so
  calls are spaced point sources; finches, larks and starlings flock and
  call as a group.
- **Reaction (flight initiation) distance.** Scales with body mass and
  starting distance; repo already cites Blumstein 2003 and Ydenberg & Dill
  1986, small-bird range 8–25 m [S-lit]. That is the spook range, not the
  acoustic localisation range.

### 3.2 Insects: crickets, katydids, cicadas

- **Crickets/katydids are nocturnal or crepuscular**, ectothermic, and call
  only when thoracic muscle temperature is high enough [S-lit]. Below a
  species-specific floor they are silent [U for the exact floor]. The
  stridulation rate rises with temperature (Dolbear relation, section 4).
- **Cicadas are mostly diurnal**, some call at dawn or dusk, a rare few are
  nocturnal [S, Cicada article]. African platypleurine cicadas use
  endothermy to call at dusk [S-lit, Sanborn et al. 2003]. One Australian
  cicada, *Froggattoides typicus*, sings nocturnally [S-lit, Ewart & Popple
  2007].
- **Cicada propagation.** Two cicada species segregate by microhabitat
  because of calling-song propagation constraints [S-lit, Sueur & Aubin
  2003]. This is the acoustic-biology basis for a positional cicada source.
- **Temperature.** Desert cicadas actively cool above about 39 °C [S].
- **Wind and rain.** Wind and rain suppress insect stridulation; rain
  physically damps the substrate and masks the signal [R].
- **Disturbance.** Crickets stop calling when disturbed and resume after a
  pause [R]; this matches AEE's existing disturbance-silence kernel.
- **Gregariousness.** Cicadas chorus synchronously (a loud continuous
  wall of sound); crickets and katydids are individual, intermittent
  sources.

### 3.3 Amphibians

- **Nocturnal or crepuscular**, strongly **temperature and rain gated**.
  Breeding choruses are explosive and seasonal, often after rain [R].
- The chorus is a **group** source (many males), continuous for hours, then
  silence outside the breeding window [R].
- Zero in `ET` core, `EF`, hyper-arid `BWh` outside rain events, and
  Mediterranean high summer [R].

### 3.4 Mammals

- Bats echolocate in ultrasound (mostly above human hearing); social calls
  are audible but sparse. Treat as intermittent and weakly localisable [R].
- Wolves howl at dusk/night, low frequency, long range, pack chorus [R].
- Deer give alarm barks, otherwise quiet [R].
- Dogs (settlement) bark in bursts, day and night [R].

---

## 4. The temporal patterns (the operator's core point)

### 4.1 Birds do not chirp constantly

Real on/off structure [S, dawn chorus; R]:
1. **Pre-dawn window**: the earliest species start roughly 30–60 minutes
   before sunrise [S, secondary; exact minutes [U] as a single number].
   Birds with larger eyes and higher perches start first [S-lit].
2. **Peak**: at or just before sunrise [S, secondary].
3. **Post-sunrise decline**: the chorus fades over the first 1–2 hours
   [S, secondary]. The exact slope is [U].
4. **Mid-day lull**: low song output through the middle of the day [R].
5. **Dusk chorus**: a second, weaker peak [R].
6. **Night**: roost and silence for most songbirds; only nocturnal species
   (owls, nightjars, robins in lit areas) call [R].
7. **Season**: all of the above is strongest in the breeding season and
   weak or absent outside it [S].

The matcher should not emit a constant bird bed. It should emit a
**probability per species per time-bin**, highest pre-dawn/dawn, near zero
mid-day, low at night for diurnal species.

### 4.2 Crickets are not constant

- **Duty cycle**: a cricket chirps in pulses and trills, not a continuous
  tone. Temperature changes pulse length, inter-pulse length, peak
  frequency and trill length [S-lit, Martin et al. 2000].
- **Temperature gated**: below a species floor they are silent [U for the
  floor]. Rate rises with temperature.
- **Nocturnal**: most calling is at night or dusk [S-lit].
- **Stop when disturbed**, resume after a pause [R].
- **Seasonal**: adults in the warm season only in cold/temperate biomes [R].

### 4.3 Cicadas are not constant

- Diurnal with dawn/dusk activity in some species [S].
- Strongly seasonal and, in monsoon climates, synchronous after the first
  rains [R].
- Chorus is dense and continuous while it lasts, then the species ends its
  adult flight season and goes silent [R].

### 4.4 Amphibians are not constant

- Explosive and rain-triggered; the general chorus is absent outside the
  breeding window [R].

### 4.5 Dolbear relation (cricket rate vs temperature)

FORMULAS [S, Dolbear 1897 via Wikipedia and the literature it cites]:
- T_F = 50 + (N60 − 40) / 4
- T_C = (N60 + 30) / 7
- Shortcut: T_C ≈ 5 + N8, stated accurate between 5 and 30 °C [S].

CAVEATS [S]:
- Dolbear did not name the species. Later workers assumed the snowy tree
  cricket; the correct name is *Oecanthus fultoni* (early reports used
  *O. niveus*, a misidentification) [S, Walker 1962].
- The relation is **reliable for the snowy tree cricket**, less so for
  common field crickets (*Gryllinae*), whose rate varies with age and
  mating success [S].
- The formula breaks down outside the cricket's living range (the linear
  model predicts chirping at 1000 °C, which cannot happen) [S].

For the matcher: use the inverse. Given air temperature T_C, the expected
chirp rate for a tree-cricket-like source is
N60 ≈ 7·T_C − 30 (erived from the sourced formula). Mark that as [S]
derived, and gate it to the source's own valid band and the species' floor.

---

## 5. Acoustic character

Frequency bands and continuity. Bands are stated as typical ranges; exact
per-species figures are [U] unless fetched.

| Group | Call type | Band | Continuity | Localisability |
| --- | --- | --- | --- | --- |
| Songbirds | whistles, trills, notes | ~1–8 kHz; many warblers >4 kHz [S-lit] | intermittent, phrase and pause | good; short wavelengths localise well at close range |
| Owls | hoot | low, ~0.3–1 kHz [U exact] | repeated hoot, long pauses | good, carries far |
| Nightjars | churring | low-mid [U] | continuous churr | moderate |
| Crickets/katydids | pulses/trills | ~2–8 kHz [U exact] | pulsed duty cycle | moderate; high frequency attenuates fast |
| Cicadas | tymbal song | often 2–12 kHz, some louder and lower [U exact] | dense continuous chorus | moderate as a wall; individual hard to separate |
| Frogs | croaks/trills | ~0.5–4 kHz [U exact] | repeated notes, chorus | moderate |
| Bats | echolocation | ultrasonic >20 kHz [R] | pulsed | inaudible to humans; not localisable without a detector |
| Wolves | howl | ~0.15–1 kHz [U exact] | long phrase | long range, low localisability at distance |

Propagation rule for positional audio [S-lit, Wiley et al.; physical basis]:
atmospheric absorption rises with frequency, so low-frequency calls (owl,
wolf) travel farther and are harder to pin than high-frequency calls
(cricket, warbler). AEE's current one-shot max distance is 120 m
(`WILDLIFE_SOUND_MAX_DISTANCE`, from `playSound3D`). Exact per-species
propagation distances are [U] and should not be invented. Use the existing
120 m ceiling and vary gain, not a fabricated range, until a field source
is obtained.

Reaction distance for the spook model is already cited in the repo dossier
(Blumstein 2003; Ydenberg & Dill 1986; small bird 8–25 m) [S-lit].

---

## 6. Matcher mapping (planner hand-off)

Pseudo-rule per tick:

```
present = species where biomeClass matches AND
          month within seasonWindow(species, biome) AND
          (species.minTemp <= airTemp) AND
          (species.water ? nearWater : true) AND
          (species.forest ? vegScore >= 0.5 : true)

active  = present where timeBin(now, sunElevation) in species.activeBins
          AND wind < species.windLimit
          AND rain  < species.rainLimit
          AND disturbance < species.spookLimit

rate    = baseRate(species)
          * tempFactor(species, airTemp)      // Dolbear for tree crickets
          * (1 - windSuppression) * (1 - rainSuppression)

gain    = rate * distanceFalloff(position, listener)
```

Time bins to use (real):
- `pre_dawn` (about −60 to −20 min before sunrise): earliest birds first [S-lit]
- `dawn` (sunrise ±30 min): peak chorus [S]
- `morning` (to ~2 h after): fading [S]
- `midday`: lull [R]
- `dusk` (±30 min around sunset): second peak [R]
- `night`: owls/nightjars/crickets only [R]

Use `aee_core_currentSunElevation` (real degrees), not a boolean, so the
pre-dawn and dusk ramps are smooth. AEE already reads this fact.

Species presence must be gated by biome **and** season **and** water. The
current `fnc_speciesForBiome` only uses biome family, night, water and
vegetation; it has **no temperature and no season** input. That is the two
missing axes for a real matcher.

---

## 7. Sources

Fetched this session:
- [S] Wikipedia, "Dolbear's law". https://en.wikipedia.org/wiki/Dolbear%27s_law
  (formula; *Oecanthus fultoni*; field-cricket caveat; 5–30 °C shortcut).
- [S] Wikipedia, "Dawn chorus (birds)". https://en.wikipedia.org/wiki/Dawn_chorus_(birds)
  (temperate spring breeding; species sing at different times; Jamieson 2007
  larger-eyed/higher-perched sing first).
- [S] Wikipedia, "Cicada". https://en.wikipedia.org/wiki/Cicada
  (mostly diurnal, some dawn/dusk, rare nocturnal; tymbal; 3000+ species;
  desert cicada cooling above ~39 °C; Sanborn et al. 2003; Sueur & Aubin
  2003; Ewart & Popple 2007 in its reference list).

Named literature (via fetched reference lists, [S-lit]):
- Dolbear, A. (1897). "The cricket as a thermometer". *The American
  Naturalist* 31(371): 970–971. doi:10.1086/276739.
- Frings & Frings (1957, 1962). *J. Exp. Zool.* 134(3):411–425 and
  151(1):33–51 (temperature vs chirp rate).
- Walker, T. J. (1962). *Ann. Entomol. Soc. Am.* 55(3):303–322 (snowy tree
  cricket naming).
- Sanborn, Villet & Phillips (2003). "Hot-blooded singers: endothermy
  facilitates crepuscular signaling in African platypleurine cicadas".
  *Naturwissenschaften* 90(7):305–308.
- Sueur & Aubin (2003). "Is microhabitat segregation between two cicada
  species due to calling song propagation constraints?".
  *Naturwissenschaften* 90(7):322–326.
- Ewart & Popple (2007). *The Australian Entomologist* 34(4):127–139
  (nocturnally singing cicada *Froggattoides typicus*).
- Martin, Gray & Cade (2000). "Fine-scale temperature effects on cricket
  calling song". *Can. J. Zool.* (temperature affects pulse length,
  inter-pulse length, peak frequency, trill length). PDF:
  https://www.csun.edu/~dgray/pdfs/Martinetal2000CJZtemp.pdf (fetch timed
  out; abstract text reached via search snippet) [S-lit].
- Wiley et al., *Ecology and Evolution*. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5980359/
  (wind severe in the open, attenuates lower frequencies) [S-lit].

Secondary (weak; cite cautiously, numbers [U]):
- RSPB dawn chorus page. https://www.rspb.org.uk/whats-happening/news/the-dawn-chorus-all-you-need-to-know-about-natures-big-show
- frameandfocal blog (wind attenuation numbers), treat as UNKNOWN.
- bird-life.com (rain masking), treat as UNKNOWN.

Reference databases for the species ranges [R]:
- IUCN Red List. https://www.iucnredlist.org
- xeno-canto (call recordings and structure). https://xeno-canto.org

Repo-internal (already cited in the project):
- `docs/wiki/research/wildlife-ambience-dossier.md` (Blumstein 2003;
  Ydenberg & Dill 1986; vanilla media inventory).
- `addons/wildlife/data/species_table.sqf`, `sound_manifest.sqf`.
- `addons/weather/functions/biome/fnc_classifyBiome.sqf`.

---

## 8. Gaps and UNKNOWNs for the operator

1. Exact cricket lower calling threshold is [U]. Do not invent a number.
2. Exact per-species propagation distance is [U]. Use AEE's 120 m ceiling.
3. Exact dawn-chorus start minutes per species is [U].
4. Wind/rain behavioural thresholds in m/s and mm/h is [U]; the secondary
   sources disagree.
5. AEE has no published season scalar; the matcher must derive season from
   `date`. Flag to the planner.
6. Non-vanilla audio: a species-level matcher needs per-species media that
   vanilla Arma 3 does not supply (the repo already records deer, wolf and
   night-insect as findings). The biology is real; the assets are the
   constraint.
