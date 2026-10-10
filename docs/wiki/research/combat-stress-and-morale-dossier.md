---
title: "Combat stress and morale dossier"
---

# Combat stress and morale dossier

This dossier records the suppression-psychology and morale model (issue
#110), the source of every value, and the values that have no source.

The model wraps two things the engine already gives. The first is the
suppression value of a unit (`getSuppression`, Arma 3 1.42). The second is
the unit's AI skill set (`skill unit "courage"`, `skill unit "spotDistance"`).
The model adds no second suppression value and no second skill value. It
reads the engine values and derives a stress index, a morale index, a
decision-quality record, an effective spotting value and a morale action.

## Grade key

The grades follow `wildlife-ecology-constants.md`.

- **S** sourced to a published relation or standard.
- **S-lit** a sourced literature value.
- **R** derived by a formula from a sourced value.
- **U** an unsourced modelling choice. It is stated so the register holds it.

## The model

The pure kernels are in `addons/strain/functions/psychology/`. The state
driver is `addons/physiology/functions/state/fnc_updatePsychologyState.sqf`.
This split matches the tree: every pure soldier-physiology kernel is in
`strain`, and the state drivers are in `physiology` (ADR-032).

```
stress   = clamp(suppression + 0.3*fatigue + 0.3*casualtyRatio, 0, 1)
morale   = clamp(1 - 0.5*casualtyRatio - 0.3*fatigue + missionBonus, 0, 1)
decision = banded lookup on stress -> [reaction, accuracy, spotting, firingRate]
spotting = spotDistanceSkill * spottingMultiplier
action   = banded lookup on (morale + (courage - 0.5)*0.2) -> hold/cover/break
```

`suppression` is the engine value (`getSuppression`). `fatigue` is the
engine per-unit stamina fatigue (`getFatigue`). `casualtyRatio` is the
fraction of the unit's group that is a casualty. `missionBonus` is a
mission-set morale term (`aee_physiology_missionMoraleBonus`, default 0).

The driver runs at 1 Hz where the unit is local, because `getSuppression` is
a local command. It publishes a fixed 8-element array on each unit under
`aee_physiology_psychology`. It never writes an engine skill: `setSkill` is
global and would double-count the engine's own suppression response. The AI
behaviour layer (#81) reads the array.

## Courage integration

The issue says two things that conflict: "multiply Courage and spotting by
the decision multiplier" and "Courage gates the behavioural response, not the
physiological one". The second sentence is the clarification, so the model
splits the two:

- **Physiological layer, courage-independent.** The decision table maps
  stress to four performance multipliers. Spotting is reduced regardless of
  courage (Easterbrook 1959, cue narrowing). The driver publishes the
  effective spotting as `spotDistanceSkill * spottingMultiplier`. A
  suppressed soldier with high courage still spots less.
- **Behavioural layer, courage-modulated.** Courage shifts the effective
  morale that the action gate reads. A high-courage soldier holds the line
  at lower morale. The gate returns 0 hold, 1 seek cover or 2 break.

Courage is therefore an input to the gate only, and it is never scaled by the
decision multiplier.

## Per-value source table

| Value | Value | Grade | Formula or basis |
|---|---|---|---|
| suppression input | `getSuppression unit` | S | BI wiki command, Arma 3 1.42, range 0 to 1, -1 when disabled |
| fatigue input | `getFatigue unit` | S | BI wiki command, stamina system, 0 to 1 |
| courage input | `skill unit "courage"` | S | BI wiki command |
| spotting input | `skill unit "spotDistance"` | S | BI wiki command |
| stress shape | additive in suppression | U | issue #110 spec; no published additive stress index |
| fatigue weight in stress | 0.3 | U | issue #110 spec |
| casualty weight in stress | 0.3 | U | issue #110 spec |
| morale shape | 1 minus penalties plus bonus | U | issue #110 spec |
| casualty weight in morale | 0.5 | U | issue #110 spec |
| fatigue weight in morale | 0.3 | U | issue #110 spec |
| decision band edges | 0.4, 0.6, 0.8 | U | issue #110 spec |
| decision multipliers, band below 0.4 | 1.0, 1.0, 1.0, 1.0 | U | issue #110 spec |
| decision multipliers, band 0.4-0.6 | 0.9, 0.8, 0.7, 0.6 | U | issue #110 spec |
| decision multipliers, band 0.6-0.8 | 0.7, 0.5, 0.4, 0.3 | U | issue #110 spec |
| decision multipliers, band 0.8-1.0 | 0.5, 0.3, 0.2, 0.1 | U | issue #110 spec |
| morale cover threshold | 0.30 | U | issue #110 spec |
| morale break threshold | 0.15 | U | issue #110 spec |
| courage weight | 0.2 | U | issue #110 spec |
| inversion-U shape of the curve | qualitative | S | Yerkes & Dodson 1908 |
| downward arm past optimum | qualitative | S | Lupien et al. 2007 |
| attention narrowing with arousal | qualitative | S-lit | Easterbrook 1959 |
| freezing at high stress | qualitative | S-lit | Roelofs 2017 |
| stress impairs uncertain decisions | qualitative | S-lit | Starcke & Brand 2016 |
| casualties are one of five collapse factors | qualitative | S-lit | Wainstein 1986 |

## The shape is sourced, the numbers are not

The curve shape comes from published work. The exact multipliers do not. No
peer-reviewed source gives a stress-index-to-reaction-time multiplier, and no
source gives this four-channel multiplier table. The table is the issue's
modelling choice. It is graded U and marked UNSOURCED in the code.

The engine heart-rate bands that Grossman popularised (80-115 optimal,
115-145, 145-175, 175+) come from Bruce Siddle, "Sharpening the Warrior's
Edge" (1995), a practitioner synthesis. They are not peer reviewed. This
model uses no heart rate, so it does not carry those bands.

## Verified sources

- Yerkes, R.M. & Dodson, J.D. (1908). "The relation of strength of stimulus
  to rapidity of habit-formation". Journal of Comparative Neurology and
  Psychology 18(5):459-482. DOI 10.1002/cne.920180503. The inverted-U is a
  plotted empirical shape. The paper gives no equation.
- Lupien, S.J., Maheu, F., Tu, M., Fiocco, A. & Schramek, T.E. (2007). "The
  effects of stress and stress hormones on human cognition: Implications for
  the field of brain and cognition". Brain and Cognition 65(3):209-237.
  DOI 10.1016/j.bandc.2007.02.007, PMID 17466428. The glucocorticoid
  inverted-U is explicit. Both low and high levels impair cognition.
- Easterbrook, J.A. (1959). "The effect of emotion on cue utilization and
  the organization of behavior". Psychological Review 66(3):183-201.
  DOI 10.1037/h0047707. Arousal narrows the range of cues used.
- Roelofs, K. (2017). "Freeze for action: neurobiological mechanisms in
  animal and human freezing". Philosophical Transactions of the Royal
  Society B 372:20160206. DOI 10.1098/rstb.2016.0206.
- Starcke, K. & Brand, M. (2016). "Effects of stress on decisions under
  uncertainty: A meta-analysis". Psychological Bulletin 142(9):909-933.
  DOI 10.1037/bul0000060.
- Wainstein, L. (1986). "The Relationship of Battle Damage to Unit Combat
  Performance". IDA Paper P-1903. Institute for Defense Analyses. DTIC
  AD-A170631. Five factors whose loss can put a unit out of action: loss of
  personnel, loss of equipment, failure of supply, collapse of command, and
  loss of morale. Wainstein states morale is the most important. The study
  reports "25 percent was not generally considered enough to destroy the
  combat performance of a unit" and "heavy casualties (30 percent is not
  unusual)". It states the loss-to-performance relationship "defies precise
  definition".

## Operations-research background

This model does not implement attrition. It records the OR basis that the
issue cites, for the reader. A force-level attrition model belongs to a
future command or force surface, not to #110.

- Lanchester, F.W. (1916). "Aircraft in Warfare: The Dawn of the Fourth
  Arm". London: Constable. Aimed fire is the square law: dR/dt = -gG,
  dG/dt = -rR, with rR^2 - gG^2 constant. Unaimed fire, which includes
  suppression and area fire, is the linear law: dR/dt = -F_G, dG/dt = -F_R,
  with the per-unit rates independent of the numbers. See MacKay, N.J.
  (2006). "Lanchester combat models". arXiv:math/0606300.
- Hughes, W.P. (1995). "A salvo model of warships in missile combat used to
  evaluate their staying power". Naval Research Logistics 42(2):267-289.
  DOI 10.1002/1520-6750(199503)42:2<267::AID-NAV3220420209>3.0.CO;2-Y. The
  model uses striking power, defensive power and staying power. The exact
  equation is not reproduced here. It could not be read from the paywalled
  primary.
- The morale `-0.5*casualtyRatio` term and the 0.30 / 0.15 action gates are
  the per-soldier realisation of the force-level breakpoints the issue
  cites. The 10/30/50 ladder itself is not sourced (see below).

## Values marked UNSOURCED

These values appear in the issue. No primary source states them. The model
carries them as explicit UNSOURCED constants, not as fact.

- The 10 percent, 30 percent and 50 percent casualty breakpoints. Wainstein
  gives no such ladder, and states the relationship "defies precise
  definition". The issue's 10/30/50 ladder is a wargaming conflation.
- The Grossman and Siddle heart-rate cut-points (115, 145, 175).
- Every value in the decision multiplier table.
- The stress and morale formula coefficients (0.3, 0.3, 0.5, 0.3).
- The morale action thresholds (0.30, 0.15) and the courage weight (0.2).
- The claim that "4-6 comrades is the strongest morale factor". Shils and
  Janowitz (1948), "Cohesion and Disintegration in the Wehrmacht in World
  War II", Public Opinion Quarterly 12(2):280-315, DOI 10.1086/265951,
  state the primary group is the chief determinant of combat motivation.
  They give no number. The "4-6" is likely Marshall's four-man fire team.
- Any stress-index-to-reaction-time multiplier.
- The police hit-rate figures. NYPD 1996-2006 was about 34 percent. The FBI
  Training Division figure (2014) is 20-30 percent, not 30-40 percent. The
  "90 percent on range" figure has no source. This model does not use them.
