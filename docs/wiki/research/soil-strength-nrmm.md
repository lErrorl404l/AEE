# Soil strength NRMM: verified research boundary (issue #117)

The NRMM soil-strength model is fail-closed. It publishes no numeric result.
The required vehicle records and the VCI50 prediction source are not verified.
This page records what the primary sources do and do not support. It does not
present an equation or a value as live. A later corpus and a second source must
exist before the model computes a result.

## 1. The published state

`fnc_calculateSoilStrength` always returns `[false, reason]`. Every call
publishes these two variables:

| Variable | Meaning |
|---|---|
| `aee_mobility_currentSoilStrengthKnown` | false while no sourced result exists |
| `aee_mobility_currentSoilStrengthReason` | the closed reason code |

The reason code is one of `null`, `tracked`, or `unverifiedInputs`.

- `null`: the vehicle argument is objNull.
- `tracked`: the vehicle is a Tank or a Tracked_APC.
- `unverifiedInputs`: every other vehicle.

The numeric variables `aee_mobility_currentVCI1`,
`aee_mobility_currentVCI50`, and `aee_mobility_currentMobilityIndex` are
cleared with nil. No numeric soil value exists while the state is unknown.

## 2. Laws verified from primary sources

The verified laws are these.

1. RCI = CI * RI, the Rating Cone Index.
   Source: ERDC/GSL SR-13-2 Eq. 1.
2. The wheeled Mobility Index and the VCI1 low branch.
   Source: Priddy 1999, ERDC TR GL-99-8 (DTIC ADA368656), pp. 42-43.

The VCI1 low-branch denominator is (MI + 2.14). The MI branch boundary is
strict. It is MI < 115 or MI > 115. No value is defined at exactly 115.

The Deflection Correction Factor DCF = (0.15 / delta)^0.25 is on Priddy
p. 43. Priddy states that MI was built at about 15 percent deflection. Priddy
also states that DCF normalises to 16 percent. Treat that 15/16 difference as
an open risk. A fixed DCF of 1 is not supported by the source.

These laws are verified. They are not live. They need the section 4 inputs
before any use.

## 3. The unresolved VCI50 source

The VCI50 prediction equations are in neither source checked. They are absent
from Priddy 1999 (ERDC TR GL-99-8) and from ERDC/GSL SR-13-2. A full-text
search of Priddy found no matching constant. SR-13-2 is a test procedure only.

Priddy says only that MI was developed to predict VCI50 (p. 42). Do not
attribute VCI50 to Priddy. Before any VCI50 use, get a primary source. A
candidate is Ahlvin and Haley, NRMM II. Another primary source of equal
standing is acceptable. Record the source that supplies the equations.

## 4. Inputs a later corpus must supply

Each vehicle variant needs one record. A record must carry these fields. This
page provides no values.

- Weight, as a real operating weight.
- Tyre width.
- Tyre diameter.
- Ground clearance.
- Net power.
- Transmission type, manual or automatic.
- Grouser or chain state.

Missing fields must fail closed. An unknown class returns no result.

## 5. Engine config fields are identity or model geometry

An engine field is an identity input or a model-geometry input only. It
becomes a scientific input when its unit and its meaning are verified.

- The wheel memory points `wheel_N` declare `center` and `boundary`. These
  are model geometry. The tyre diameter is twice the distance from the axis
  to the boundary. The wheel count is the number of declared stations. This
  is the one quantity the engine verifies.
- `getMass` returns the PhysX mass. It has no stated real-world unit.
- `enginePower` is a PhysX tuning value.
- `maxSpeed` is a game limiter.
- The wheel `width` field has no stated unit.
- `complexGearbox` does not give a manual gearbox input.
- `maxFordingDepth` is fording depth, not ground clearance.
- An `isKindOf` match is an inheritance match, not a source.

No config field gives the operating weight, the tyre width in millimetres, or
the ground clearance. A later corpus must get those figures from a vehicle
manual or a tyre record.
