# P3 research backlog: un-researched features and verification flags (issue #114)

This page is the record for issue #114. It holds the trailing edge of the
AEE research phase. The P1 and P2 physics features are researched and ready
to implement. This page keeps the remaining P3 backlog visible and names the
primary source for each open item.

No value on this page is invented. Every named source is real. Every number
is either cited or marked UNKNOWN. A source named by identity is not a
verified value until the source body is read.

## 1. Backlog status

Issue #114 lists seven un-researched P3 features and two verification flags.
An update on the issue (2026-09-16) moved three of the seven features out of
the backlog. They now live under other issues. Four features stay open.

| Feature | Issue | Effort | Status |
|---|---|---|---|
| Frost heave terrain modification | #20 | M | open, un-researched |
| Volcanic activity module | #25 | L | open, research in progress |
| Groundwater and aquifer model | #26 | M | open, un-researched |
| Seismic activity effects | #27 | M | open, un-researched |
| 3D EM wave propagation | #13 | XL | re-homed to #116 |
| Ship motion model | #33 | M | re-homed to #28 and #17 |
| Scent dispersion | #39 | M | re-homed to #116 |

The effort column repeats the value in the issue #114 body. The issue label
differs for three items. The label reads `effort/L` for #26 and #27, and
`effort/M` for #39. Keep the two figures apart. The body figure scopes the
backlog. The label figure scopes the feature issue.

A re-homed feature keeps its research need. The home issue owns the work.
This page records the entry point so the work is not lost.

## 2. Frost heave terrain modification (#20)

Research needed: ice lens formation, heave displacement against soil type and
moisture, the segregation potential (Konrad and Morgenstern), the heave rate,
and the freeze-thaw cycle count. The item ties to the ground frost model that
issue #11 confirmed. That model uses the Stefan solution.

The verified relations and sources are these.

- The segregation potential. Konrad and Morgenstern (1980), "A mechanistic
  theory of ice lens formation in fine-grained soils", *Canadian Geotechnical
  Journal* 17(4):473-486, DOI 10.1139/t80-056. The parameter is
  `SP = v_h / grad(T)`, with `v_h` the water (heave) velocity to the freezing
  front and `grad(T)` the temperature gradient next to the growing ice lens.
  The unit is mm2/(s degC). Source for the definition: Fukuda and Kinosita
  (1985), *Annals of Glaciology* 6:87-91, DOI 10.3189/1985AoG6-1-87-91.
- The magnitude. Devon silt gives `SP` about `110e-5 mm2/(s degC)`. A
  field-fit value is `9e-4 mm2/(s degC)`. The order of magnitude is 1e-4 to
  1e-3 mm2/(s degC). The field-fit source is Nixon (1982/83), "Field frost
  heave predictions using the segregation potential concept", *Canadian
  Geotechnical Journal*, DOI 10.1139/t82-059.
- The Stefan solution. `X = sqrt(2 k dT t / L_v)`, with `k` the soil thermal
  conductivity, `dT` the surface-to-front temperature difference, `t` the
  time, and `L_v` the volumetric latent heat. Sources: Kurylyk and Hayashi
  (2015), *Permafrost and Periglacial Processes*, DOI 10.1002/ppp.1865, and
  the USACE CRREL report TR-19-24, DOI 10.21079/11681/34893. The exact
  published algebraic form and its correction factors stay UNKNOWN. Confirm
  against Andersland and Ladanyi, *Frozen Ground Engineering*, ISBN
  0471615498, before transcribing.
- The heave against soil type. Witek-Zielonka et al. (2024), "Effect of Silt
  and Clay Fraction Content on Frost Heave of Fine-Grained Soils", DOI
  10.2478/acee-2024-0023. The laboratory total heave `Wp` is 48.8 mm for a
  soil with 65 per cent silt and clay, 21.5 mm for a sandy clay, 4.7 mm for a
  sandy silt, 1.6 mm for a silty sand, and 1 to 5 mm for a clay-free soil.
  The clay fraction dominates the heave.
- The frost susceptibility. The common criterion is the percentage of
  particles finer than 0.02 mm. Source: Chamberlain (1981), "Frost
  Susceptibility of Soil: Review of Index Tests", USACE CRREL, handle
  11681/2629. The ASTM D5918 frost-heave test is a related standard.

Two items stay UNKNOWN.

- The canonical typical segregation-potential range table (Konrad 1994
  colloquium, DOI 10.1139/t94-028).
- The typical heave-rate table in mm per day by soil, and the exact USACE
  CRREL F-group percentage thresholds. The CRREL PDF is blocked by 403.

## 3. Volcanic activity module (#25)

Research needed: plume rise, ash concentration, and the lava flow rate. The
ash plume can reuse the CBRN Gaussian model from issue #105. The lava flow
uses a Herschel-Bulkley rheology.

The verified values are these.

- Sulphur dioxide exposure. NIOSH Pocket Guide `npgd0575` and the NIOSH IDLH
  record `7446095`. IDLH 100 ppm. NIOSH REL 2 ppm time-weighted average and
  5 ppm short-term. OSHA PEL 5 ppm. One ppm is 2.62 mg/m3. The NRC
  Emergency Exposure Guidance Levels are 30 ppm at 10 minutes, 20 ppm at 30
  minutes, 10 ppm at 60 minutes, and 5 ppm at 24 hours.
- Volcanic forcing. Robock (2000), "Volcanic eruptions and climate",
  *Reviews of Geophysics* 38(2):191-219. The stratospheric aerosol e-folding
  time is about one year. Pinatubo injected about 20 Mt of sulphur dioxide.
  The effective aerosol radius is about 0.5 micrometre. The surface radiative
  forcing is about -0.2 W/m2 globally and -0.3 W/m2 in the northern
  hemisphere. Stratospheric warming was about 1 C for El Chichon and about
  twice that for Pinatubo. Table 1 gives VEI 7 for Tambora, VEI 6 for
  Krakatau, and VEI 6 for Pinatubo.
- The Volcanic Explosivity Index. Newhall and Self (1982), *Journal of
  Geophysical Research* 87(C2):1231-1238, DOI 10.1029/JC087iC02p01231. The
  index is `floor(log10(tephra volume in km3)) + 5`. Rows 0 to 5 are
  confirmed.
- The lava rheology is Herschel-Bulkley, `tau = tau0 + K gamma_dot^n`, with
  `tau0` the yield stress. Source: Pinkerton and Sparks (1978), "Field
  measurements of the rheology of lava", *Nature* 276(5686):383-385, DOI
  10.1038/276383a0.
- The lava flow rates come from the USGS Volcano Hazards Program
  (https://www.usgs.gov/programs/VHP/lava-flows-destroy-everything-their-path).
  Basalt runs below 1 km/h on a gentle slope, up to 10 km/h on a steep slope,
  and above 30 km/h in a channel or a tube. Andesite runs a few km/h and
  rarely above 8 km/h. A dacite or rhyolite dome runs below a few metres per
  hour.
- A lahar runs above 200 km/h on a steep slope. Its volume grows more than
  ten times by entrainment. Source: USGS
  (https://www.usgs.gov/programs/VHP/lahars-move-rapidly-down-valleys-rivers-concrete).
  The physics source is Iverson (1997), "The physics of debris flows",
  *Reviews of Geophysics* 35(3):245-296, DOI 10.1029/97RG00426.
- Tephra dispersal uses an advection-diffusion model with a diffusion
  coefficient scaled by the wind and settling per grain size. Source: Suzuki
  (1983), "A theoretical model for dispersion of tephra", in *Arc Volcanism:
  Physics and Tectonics*, TERRAPUB, 95-113.

Three items stay UNKNOWN.

- The Briggs plume-rise identity is Briggs (1975), in *Lectures on Air
  Pollution and Environmental Impact Analyses*, American Meteorological
  Society, 59-111, and Briggs (1984), in *Atmospheric Science and Power
  Production*, DOE/TIC-27601, 327-366. The buoyancy flux is
  `F = g d^2 V dT / (4 Ts)`. The final branch is ambiguous across sources.
  One form gives `38.7 F^(3/5) / u` for `F >= 55` and `21.4 F^(3/4) / u` for
  `F < 55`. A secondary source gives the inverse. Verify against EPA ISC3 or
  AERMOD, or Briggs 1975, before use.
- The Briggs rural dispersion coefficients are a single expression. The
  one-kilometre split belongs to Martin (1976) and the original Pasquill and
  Gifford curves. Do not attach the split to Briggs.
- The ash aviation-hazard threshold is about 2 mg/m3. The source is ICAO or a
  Volcanic Ash Advisory Centre. It is not pinned.

## 4. Groundwater and aquifer model (#26)

Research needed: Darcy's law, the hydraulic conductivity, the recharge from
the water balance, and the water table dynamics. The item pairs with the
hydrology work in issue #24.

The verified relations and sources are these.

- Darcy's law. `Q = -K A (dh/dL)`. Sources: Woessner and Poeter (2020),
  *Hydrogeologic Properties of Earth Materials and Principles of Groundwater
  Flow*, The Groundwater Project, equations 15 and 16, DOI 10.21083/CPET1503,
  and Freeze and Cherry (1979), *Groundwater*, Prentice-Hall.
- The hydraulic conductivity. Freeze and Cherry figure 2.2 gives the
  saturated `K` range across about 13 orders of magnitude. A worked value is
  sand at about 0.2 cm/s. The per-material table is Freeze and Cherry figure
  2.2.
- The specific yield. Woessner and Poeter table 3 gives the specific yield in
  per cent, compiled from Morris and Johnson (1967). Clay 1 to 18. Silt 1 to
  40. Eolian sand 32 to 47. Fine sand 1 to 46. Medium sand 16 to 46. Coarse
  sand 18 to 43. Fine gravel 13 to 40. Medium gravel 17 to 44. Coarse gravel
  13 to 25. Shale 0.5 to 5. Siltstone 1 to 33. Fine sandstone 2 to 40.
  Limestone and dolomite 0 to 36. Karstic limestone 2 to 15. Fresh granite or
  gneiss below 0.1. Fractured basalt 2 to 10. Tuff 2 to 47.
- The storativity. The unconfined storativity is `S = S_y + S_s b`. The
  confined storativity is `S = S_s b`, dimensionless.
- The water-table fluctuation recharge. `R = S_y dH/dt`. Source: Healy and
  Cook (2002), "Using groundwater levels to estimate recharge",
  *Hydrogeology Journal* 10(1):91-109, DOI 10.1007/s10040-001-0178-0.
- The baseflow recession. Source: Brutsaert and Nieber (1977), "Regionalized
  drought flow hydrographs from a mature glaciated plateau", *Water Resources
  Research* 13(3):637-643, DOI 10.1029/WR013i003p00637. It comes from
  Boussinesq (1877). The linear-reservoir exponential recession follows
  Maillet (1905).

One item stays UNKNOWN.

- The confined storativity numeric ranges, and the Freeze and Cherry ISBN.
  Neither is read.

## 5. Seismic activity effects (#27)

Research needed: the magnitude scales, the ground motion attenuation, and the
building damage curves. The ground motion ties to the structural integrity
work.

The verified relations and sources are these.

- Moment magnitude. Hanks and Kanamori (1979), "A moment magnitude scale",
  *Journal of Geophysical Research: Solid Earth* 84(B5):2348-2350, DOI
  10.1029/JB084iB05p02348. The working form is `Mw = (2/3)(log10 M0 - 9.1)`
  with `M0` the seismic moment in N m, and `M0 = rigidity * area * slip`.
  The energy relation is `log10 E = 5.24 + 1.44 Mw`. Source: USGS,
  "Earthquake Magnitude, Energy Release, and Shaking Intensity",
  https://www.usgs.gov/programs/earthquake-hazards/earthquake-magnitude-energy-release-and-shaking-intensity.
- Local magnitude. Richter (1935), "An instrumental earthquake magnitude
  scale", *Bulletin of the Seismological Society of America* 25(1):1-32. The
  definition is `ML = log10 A - log10 A0(delta)`, with `A` the maximum
  Wood-Anderson trace amplitude in millimetres and `A0` a distance
  correction. It holds for California within 600 km. No DOI is registered.
- The ground motion attenuation. A named ground motion prediction equation
  is Boore and Atkinson (2008), *Earthquake Spectra* 24(1):99-138, DOI
  10.1193/1.2830434. The form is a sum of a magnitude term, a distance term,
  a site term, and a residual. The coefficients are the paper Tables 6 to 8.
  The coefficients are not read. The Campbell and Bozorgnia (2008) equation
  is *Earthquake Spectra* 24(1):139-171, DOI 10.1193/1.2857546.
- The distance decay. Ground motion decays by geometric spreading near `1/R`
  and by anelastic loss `exp(-pi f R / Q beta)`. Source: Kramer (1996),
  *Geotechnical Earthquake Engineering*, Prentice Hall. For a shaking
  intensity from a ground motion, use Wald et al. (1999), *Earthquake
  Spectra* 15(3):557-564, DOI 10.1193/1.1586058.
- The damage states. HAZUS-MH (FEMA) gives four damage states: slight,
  moderate, extensive, complete. Fragility curves drive them. The European
  Macroseismic Scale 1998 (Gruenthal, ed., *Cahiers du Centre Europeen de
  Geodynamique et de Seismologie* 15) gives damage grades D1 to D5 and
  vulnerability classes A to F.
- Liquefaction. The simplified procedure is Seed and Idriss (1971),
  *Journal of the Soil Mechanics and Foundations Division, ASCE*
  97(SM9):1249-1273. The NCEER summary is Youd et al. (2001), *Journal of
  Geotechnical and Geoenvironmental Engineering* 127(10):817-833, DOI
  10.1061/(ASCE)1090-0241(2001)127:10(817). It holds the cyclic resistance
  ratio `CRR7.5`, the magnitude scaling factor, and the overburden term.
  Liquefaction needs a saturated, loose, cohesionless sand or silt and a
  shallow water table.

Two items stay UNKNOWN.

- The Boore and Atkinson coefficient values. The locator is confirmed. The
  values are not read.
- The HAZUS and EMS-98 numeric fragility thresholds. The locators are
  confirmed. The values are not read.

## 6. Features re-homed by the issue update

The update of 2026-09-16 moved three features. Each stays recorded here with
its research entry point.

### 6.1 3D EM wave propagation (#13, now #116)

The scalar-field advection engine (#116) owns multipath and ground bounce.
They become per-field physics on the shared grid.

Research entry points, verified.

- The Fresnel reflection coefficient for a ground plane is
  `Gamma(theta) = (sin theta - X) / (sin theta + X)`. For horizontal
  polarisation `X = sqrt(eps_g - cos^2 theta)`. For vertical polarisation,
  divide that value by `eps_g`. `eps_g` is the ground relative permittivity.
  The two-ray
  ground-reflection model gives this form. The ground electrical parameters
  come from ITU-R Recommendation P.527, "Electrical characteristics of the
  surface of the Earth", edition P.527-6 (09/2021),
  https://www.itu.int/rec/R-REC-P.527/en
- The two-ray ground-bounce path loss is `Pr = Pt * G * ht^2 * hr^2 / d^4`.
  In decibels, `PL = 40 log10(d) - 10 log10(G * ht^2 * hr^2)`. The form holds
  in the far field only, where `d >> 4 pi ht hr / lambda`.
- Knife-edge diffraction uses the Fresnel diffraction parameter
  `nu = h * sqrt(2 (d1 + d2) / (lambda d1 d2))`. The loss follows from the
  Fresnel integrals `C(nu)` and `S(nu)`. The governing standard is ITU-R
  Recommendation P.526, "Propagation by diffraction", edition P.526-16
  (11/2025), https://www.itu.int/rec/R-REC-P.526/en

### 6.2 Ship motion model (#33, now #28 and #17)

Issue #28 and issue #17 hold the ocean-current work. That work gives the
Ekman and tidal vectors. The ship response functions remain for a later
pass.

A defect is recorded. The ship motion issue text cites "NATO STANAG 4569:
helicopter landing conditions". That citation is wrong. STANAG 4569 with
AEP-55 is the vehicle armour protection level standard. It covers kinetic,
artillery and blast protection. It does not cover ship motion. The correct
seakeeping standard is NATO STANAG 4154, "Common Procedures for Seakeeping in
the Ship Design Process". The current naval engineering publication is
ANEP-4154, promulgated 2018. The NATO Science and Technology Organization
AVT-217 panel confirms the standard. The exact edition year of STANAG 4154
stays UNKNOWN.

The verified ship-motion relations are these.

- Encounter frequency `we = w - (w^2 / g) U cos(mu)`. The angle `mu` is
  measured from the bow.
- The single-degree-of-freedom response amplitude operator is
  `|H| = [(1 - r^2)^2 + (2 zeta r)^2]^(-1/2)`, with `r = we / wn`.
- The natural roll period is `T = 2 pi kxx / sqrt(g GM)`. The IMO
  Intact Stability Code (2008) weather criterion gives `T = 2 C B / sqrt(GM)`
  with `C = 0.373 + 0.023 (B / d) - 0.043 (L / 100)`. The roll radius of
  gyration ratio `kxx / B` is typically 0.35 to 0.42.
- The Pierson-Moskowitz spectrum is
  `S(w) = alpha g^2 / w^5 * exp[-beta (w0 / w)^4]`, with `alpha = 8.1e-3`,
  `beta = 0.74`, and `w0 = g / U19.5`. The significant wave height is
  `Hs = 0.21 U19.5^2 / g`, about `0.22 U10^2 / g`.

Two items need a source before use.

- The repository `fnc_calculateSeaState.sqf` uses `Hs = 0.0246 v^2`. The
  Pierson-Moskowitz primary gives `0.0213 U19.5^2`. The repository figure is
  about ten per cent higher. Name a source or re-derive the figure.
- Roll damping of 0.05 to 0.15 is widely quoted but no primary was pinned.
  The IMO s-factor table (Intact Stability Code 2.3.4-4) is the citable
  damping proxy.

### 6.3 Scent dispersion (#39, now #116)

The scalar-field engine (#116) owns scent as a per-field source on the same
grid. Scent is a detection cue. It is distinct from the CBRN plume (#105).

Research entry points, verified.

- The Gaussian plume equation for a continuous point source at effective
  height `H` is
  `C(x,y,z) = Q / (2 pi u sigma_y sigma_z) * exp(-y^2 / 2 sigma_y^2) *
  [exp(-(z-H)^2 / 2 sigma_z^2) + exp(-(z+H)^2 / 2 sigma_z^2)]`.
  The source is D. Bruce Turner, *Workbook of Atmospheric Dispersion
  Estimates*, US EPA Office of Air Programs Publication AP-26 (1970). A later
  edition is CRC Press, chapter DOI 10.1201/9780138733704-2. The `sigma_y`
  and `sigma_z` terms are the Pasquill-Gifford stability-class curves,
  tabulated in the same workbook.
- The meandering plume model is Frank Gifford Jr., "Statistical Properties
  of a Fluctuating Plume Dispersion Model", *Advances in Geophysics* 6
  (1959):117-137, DOI 10.1016/S0065-2687(08)60099-0. In this model the
  concentration is a random variable, not a fixed mean.
- A wildlife olfactory threshold source is D. B. Walker et al., "Naturalistic
  quantification of canine olfactory sensitivity", *Applied Animal Behaviour
  Science* 97(2-4) (2006):241-254, DOI 10.1016/j.applanim.2005.07.009. The
  named odorant is n-amyl acetate. The numeric threshold is behind a paywall
  and stays UNKNOWN.
- The rural dispersion coefficients. Briggs (1973), "Diffusion estimation for
  small emissions", ATDL Contribution File No. 79, NOAA. The `sigma_y` and
  `sigma_z` forms are a single expression per stability class, with no
  one-kilometre split. Class A gives `sigma_y = 0.22 x (1 + 0.0001 x)^-0.5`
  and `sigma_z = 0.20 x`. Class D gives `sigma_y = 0.08 x (1 + 0.0001 x)^-0.5`
  and `sigma_z = 0.06 x (1 + 0.0015 x)^-0.5`. This confirms the note in
  section 3 about the #25 plume-rise split.
- The Gaussian puff normalization is `(2 pi)^-3/2`. Source: Hanna, Briggs and
  Hosker (1982), *Handbook on Atmospheric Diffusion*, DOE/TIC-11223, chapter
  6. A review is Stockie (2011), "The Mathematics of Atmospheric Dispersion
  Modeling", *SIAM Review*, DOI 10.1137/10080991X.
- Odour thresholds. The human geosmin taste threshold is 0.006 to 0.01 ug/L
  in water. The enantiomer threshold is 9.5 and 78 parts per trillion (Polak
  and Provasi 1992, *Chemical Senses*, DOI 10.1093/chemse/17.1.23). The
  threshold compilation is van Gemert (2003), *Odour Thresholds*, ISBN
  90-810295-1-X. The test method is ASTM E679-04.
- The wildlife detection. Amo, Galvan, Tomas and Sanz (2008), "Predator odour
  recognition and avoidance in a songbird", *Functional Ecology*, DOI
  10.1111/j.1365-2435.2007.01361.x. The avoidance direction is confirmed. A
  counter-example is Johnson et al. (2011), *Journal of Field Ornithology*,
  DOI 10.1111/j.1557-9263.2011.00317.x. The House Wren shows no avoidance, so
  the response is species-specific. Do not apply one detection threshold to
  every species.
- A dense gas needs a dense-gas model. The Gaussian plume holds for a passive
  or a neutral gas. A dense gas needs DEGADIS or SLAB. See issue #120. The
  NATO AEP-66 and AEP-72 content stays UNVERIFIED.

## 7. Verification flags

The issue carries two flags from completed research. Each flag names a
secondary value that must be re-checked against a primary source.

### 7.1 Flag A: suppression psychology sources (#110)

Issue #110 cites several psychology figures from secondary sources. The
re-check found this.

| Claim | Source state |
|---|---|
| Grossman heart-rate bands | Locatable in Grossman and Christensen, *On Combat* (2004). The bands are the author's synthesis, not peer-reviewed physiology. Treat as anecdotal. |
| Marshall, fewer than 25 per cent fired | Locatable in S. L. A. Marshall, *Men Against Fire* (1947). CONTESTED. Spiller, "S.L.A. Marshall and the Ratio of Fire", *RUSI Journal* (1988), challenges the method. |
| NYPD hit rate about 34 per cent | The Annual Firearms Discharge Report is the primary. The NYPD page returned 404 during the check. UNKNOWN until read. |
| FBI hit rate 30 to 40 per cent | UNKNOWN. No primary located. |
| 10/30/50 per cent breakpoints | UNKNOWN. No primary located. |
| Yerkes-Dodson inverted-U | R. M. Yerkes and J. D. Dodson (1908), *Journal of Comparative Neurology and Psychology* 18(5):459-482, DOI 10.1002/cne.920180503. The popular inverted-U is a later reading. The original simple-task curve is monotonic. |
| Lupien 2007 glucocorticoid inverted-U | S. J. Lupien et al. (2007), *Brain and Cognition* 65(3):209-237, DOI 10.1016/j.bandc.2007.02.007. |

The flag is best closed during implementation, when the values land in
tests. Do not publish the contested Marshall figure as fact.

### 7.2 Flag B: fire fuel model parameter table (#10)

The 13-model fuel parameter table must be verified against Albini,
"Estimating Wildfire Behavior Effects". The report identity is Frank A.
Albini, USDA Forest Service, Intermountain Forest and Range Experiment
Station, General Technical Report INT-30. The canonical path is
https://www.fs.usda.gov/rm/pubs_int/int_gtr030.pdf

The check found this.

- The report path exists. The USFS host returns 403 to the fetcher, so the
  host holds the document but blocks the read.
- A readable copy is available through the Internet Archive. A second
  research pass read it and reports the fuel-model parameter table as Albini
  INT-30 Table 7. The table cross-matches J. E. Anderson, "Aids to
  determining fuel models for estimating fire behavior", GTR INT-122 (1982),
  Table 1. The heat content 8000 Btu/lb, the total mineral content 0.0555,
  and the effective mineral content 0.010 agree across the two tables.
- The issue locator "page 92" is not confirmed. The second pass places the
  table at Table 7. Confirm the page against the readable copy before use.
- The report year 1976 is not confirmed by a read. Treat it as UNKNOWN.

## 8. What remains UNKNOWN

These items have no verified source today. Each needs a primary read.

- The Konrad and Morgenstern segregation-potential magnitude range and the
  heave-rate relation.
- The Briggs plume-rise final branch, pending an EPA source.
- The canine odour detection threshold value for n-amyl acetate.
- The NYPD and FBI hit rates, and the 10/30/50 per cent breakpoints.
- The Albini INT-30 year and the page-92 locator.

## 9. Related

- Issue #116, the unified scalar-field advection engine. It is the home for
  #13 and #39.
- Issue #28 and issue #17, the ocean-current work. They hold the #33
  vectors.
- Issue #105, the CBRN plume. The volcanic ash plume (#25) can reuse its
  Gaussian model.
- Issue #24, the hydrology research. It pairs with the groundwater model
  (#26).
- Issue #11, the ground frost research. It holds the Stefan solution that
  the frost heave model (#20) extends.
- `docs/wiki/research/soil-strength-nrmm.md`, the soil-strength boundary
  (issue #117).
