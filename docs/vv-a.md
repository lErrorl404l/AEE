# Verification, Validation and Accreditation

This record states the AEE VV&A position. It follows JSP 939, Defence
Policy for Modelling and Simulation (V3.1, 2025). JSP 939 applies by
relevance. AEE holds no MOD system and no accreditation. Section 5 states
the limit of this record.

## 1. The three terms

- Verification checks that the mod is built the stated way. The question
  is: does the code match the published formula?
- Validation checks that the mod models the real behaviour. The question
  is: does the output match an independent solver?
- Accreditation is the formal acceptance of a model for a stated use. AEE
  holds none. AEE claims none.

## 2. Verification

The script `tools/validation/validate_physics.py` holds a mirror of each
formula. The mirror is SQF-identical to the shipped code. The script checks
the mirror against a published reference value.

A mirror that disagrees with the published formula fails the gate.

The sensor scripts `validate_sensors.py`, `validate_illuminance.py`, and
`validate_dof.py` verify the sensor equations against published bands.

## 3. Validation

The script `tools/validation/validate_oracles.py` is the validation layer.
It feeds one scenario state through the mod and through an independent
oracle. It compares the two with a tolerance band. JSP 939 names this
direction 2, accuracy.

The oracles are independent references.

| Oracle | Reference | Domain |
|---|---|---|
| Atmospheric absorption | ISO 9613-1:1993 | Acoustics |
| Standard atmosphere | ICAO Doc 7488, ISO 2533 | Pressure and density |
| Heat index | NWS Rothfusz 1990 regression | Thermal comfort |
| Optional Python libraries | `metpy`, `pythermalcomfort`, `psychrolib` | Cross-check |

The check values are the acceptance criteria. The two ISO 9613-1 check
values, 2.60 dB/km at 1 kHz and 12.59 dB/km at 8 kHz, were corrected in
issue #80. The first hand-computed values were wrong.

An optional library that is absent is skipped. It never fails the core
path.

## 4. Tolerance and acceptance

A tolerance band is set per domain. The band is the acceptance criterion.
A result inside the band passes. A result outside the band fails.

The band is recorded beside the oracle. A band change is a change to the
acceptance criterion, so it needs a recorded reason.

## 5. Accreditation limit

AEE is not an accredited model. AEE holds no Safety Critical or Training
Accreditation (SCTA). AEE is not registered with the Defence Simulation
Centre. JSP 939 applies to AEE by relevance only, because AEE is a
hobby-scale environment mod, not a Defence M&S asset.

This record states the verification and validation AEE performs. It claims
no accreditation and no compliance certificate.

## 6. Evidence

The evidence is the gate result at each release. The gate
`tools/validation/validate_oracles.py` exits 0 when every run check passes.

The release record under `docs/release-records/` carries the gate result. The
Software Test Report carries the run counts.
