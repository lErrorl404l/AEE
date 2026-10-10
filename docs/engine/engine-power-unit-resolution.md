# The enginePower unit resolution

This note resolves the `enginePower` unit contradiction. It records the
verdict, the evidence and the consequence for the corpus.

## Verdict

`enginePower` is a PhysX tuning value. It is not a kilowatt figure. The
corpus does not map `net_power_kw` onto it. The generated `CfgVehicles`
block does not emit `enginePower`, `torqueCurve`, `peakTorque` or a
gearbox ratio.

## The contradiction

Two claims disagree.

1. The BIKI "Arma 3: Vehicle Config Guidelines" states that `enginePower`
   is in kW. `data/vehicle/SCHEMA.md` section 17 records that claim at the
   `enginePower` row.
2. `docs/wiki/research/soil-strength-nrmm.md` line 85 states that
   `enginePower` is a PhysX tuning value. `data/vehicle/SCHEMA.md` section
   4 rule 1 names `enginePower` as an engine value and forbids an engine
   source for a numeric value.

## The evidence

### The prior decision

`data/vehicle/mass_model.json` disables the power-to-weight band. The
`power_to_weight` object reads `enabled: false` and `hard_factor: 2.0`. Its
reason reads "enginePower is a PhysX tuning value with no verified
real-world unit (docs/wiki/research/soil-strength-nrmm.md:85); a band needs
an in-engine probe". `docs/wiki/research/vehicle-mass-estimate.md` lines 50
to 58 record the same decision and name the probe.

### The in-engine probe

The probe at `.omo/evidence/vehicle-mass-model/power-probe.json` is dated
2026-09-25. It read the merged `enginePower` and `getMass` in the engine for
five classes. The table gives the reading.

| Class | enginePower | getMass (kg) | enginePower per tonne |
|---|---|---|---|
| B_MRAP_01_F | 276 | 8306.63 | 33.226 |
| B_Truck_01_transport_F | 450 | 10942.9 | 41.123 |
| B_APC_Wheeled_01_cannon_F | 506.25 | 23299.8 | 21.728 |
| B_APC_Tracked_01_rcws_F | 895 | 62385 | 14.346 |
| C_Hatchback_01_F | 103 | 1190 | 86.555 |

The probe records an engine-relative spread of 6.033. The low is 14.346 and
the high is 86.555 over five classes.

### Why the spread rejects the kilowatt claim

A real power-to-weight spread over these five classes is inside about two
times. The hard factor in the mass model is 2.0. The engine returns 6.033.
The raw value spans 8.7 times from 103 to 895. The mass spans 52 times from
1190 kg to 62385 kg. The quotient is therefore not a physical
power-to-weight. No sample class carries a cited published power. The engine
number cannot be checked against a published figure. A unit that cannot be
checked is not a kilowatt figure.

### The shipped config

The probe read the merged engine config. The five values above are the
shipped config values as the engine returns them. The AEE generator does not
emit `enginePower`. No repository config file holds an `enginePower` value.
The BIKI kW claim is unsupported by the shipped values, because the values
do not track a published power.

## The consequence

1. `net_power_kw` stays a corpus field. The corpus never writes it to
   `enginePower`.
2. The land physics section of `data/vehicle/SCHEMA.md` keeps the
   `enginePower` marker. This note is the resolution: the unit is not a
   kilowatt figure, so the key is not emitted.
3. A later mapping needs a new in-engine probe. The probe must pair each
   merged `enginePower` with a cited published power. It must show a spread
   inside the hard factor 2.0. Without that probe the decision stays closed.

## Sources

- `data/vehicle/mass_model.json`, the `power_to_weight` object.
- `docs/wiki/research/vehicle-mass-estimate.md` lines 50 to 58.
- `docs/wiki/research/soil-strength-nrmm.md` line 85.
- `.omo/evidence/vehicle-mass-model/power-probe.json`.
- `data/vehicle/SCHEMA.md` sections 4 and 17.
- The BIKI "Arma 3: Vehicle Config Guidelines", the `enginePower` kW claim.
