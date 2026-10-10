# Vehicle class identity sources and the claimed lead

This note records the identity grade of every concrete class binding and the
lead for each one. It comes from the work to prove the gated `CfgVehicles`
surface.

## The rule

A binding links one concrete game class to one held catalogue entry. The
`grade` states how strong the link is. A `documented` link needs a held tier 2
or tier 3 source that names the class to vehicle link. A `claimed` link is an
engine class table or config binding. The engine evidence binds a concrete
class at grade `claimed` only.

## The finding

Every class binding in `data/vehicle/class_bindings.json` uses the identity
source `aee_class_table`. That source is an engine class table. It is tier 4
evidence, so the rule above keeps every link at grade `claimed`.

No held source names a fictional Arma class. The published manuals name the
real vehicle, for example the Oshkosh M-ATV, and never the class
`B_MRAP_01_F`. A class-to-vehicle link therefore has no tier 2 or tier 3
source. The correct grade stays `claimed`.

The lead is the same for every class. The source to seek is a real-world
document that names both the fictional Arma class and the real vehicle. No
such document is public. The lead stays open.

## The held side

The catalogue entry carries the real figures. Each figure holds its own
source. The link is weak; the weight is not. The held weight and its source
for each ground token are these.

| Token | Catalogue entry | Held weight source |
|---|---|---|
| `Car` | `honda_civic_6gen_hatchback` | Honda Civic factory service manual, gross weight |
| `Truck` | `m923a2` | TM 9-2320-272-10, M923A2 empty weight |
| `Tracked_APC` | `m113a2` | TM 9-2350-261-10, M113A2 gross weight |
| `MRAP` | `m_atv_m1240` | TM 9-2355-335-10, M1240 curb weight |
| `Tank` | `m1_abrams` | TM 9-2350-255-10, combat loaded weight |
| `Wheeled_APC` | `btr_80` | BTR-80 technical description, full mass |

## The lead

Record the lead once. Add a real-world tier 2 or tier 3 source that names the
class to vehicle link. Raise the grade to `documented` only when that source is
held. Until then every link stays `claimed` and the gated surface ships
nothing.
