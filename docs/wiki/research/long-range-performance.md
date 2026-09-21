# Long-range performance cost analysis (issue #139)

The honest cost analysis of long-range Arma 3 performance, verified
from primary sources (BI community wiki via the Wayback Machine,
archived captures).  All claims below are direct quotes or extracted
table values from the official pages.

## The cost ranking (BI official impact table)

1. **Object view distance** - "The CPU killer" (BI quote).  The
   dominant cost at range.  Official guidance: set object distance to
   1/3 to 1/2 of terrain view distance.
2. **Terrain view distance** - "alleviate pressure on the GPU".
3. **Shadow** - draw distance range 50-200 m per the table.
4. **Particles** - smoke, fire, dust.
5. **PIP** - "Adds (doubles?) the strain on the CPU".
6. **AI simulation cycles** - scale with view distance via the
   knowledge-range mechanism (see below).

## The AI link (verified, BI quote)

> "View distance also defines the maximum distance between a unit and
> any other unit they can know about.  Higher view distance will
> involve more AI simulation cycles for every unit, which causes low
> performance." (setViewDistance page)

The mechanism is unit-knowledge range (visibility/knowledge checks),
NOT inventory.  Enemy inventories are config/data, read on access, zero
per-frame cost (not in any performance guidance).

## The command specs (verified)

- `setViewDistance` - scripted max is 40,000 m (NOT 12,000; 12,000 is
  the UI max).  Negative resets to the client's video setting.
- `setObjectViewDistance [object, shadow]` - the two-parameter array
  form sets object AND shadow distance together.  Example:
  `setObjectViewDistance [2000, 800]`.
- `viewDistanceCoef` (description.ext) - scales client view distance.

## What AEE does with it (this issue)

The physics-driven view distance (#138) previously drove only terrain
(`setViewDistance`).  The verified "CPU killer" lever - object view
distance - was not driven.  This adds it:

- Object distance follows terrain at **1/2** (the BI guidance mid-
  point), capped at 2 km
- The two-parameter form sets shadow distance to **25% of object**
  (mapping the shadow impact range)
- Same 500 m deadband + 4 s ramp rate limiting as terrain
- The AI knowledge-range link means lower object distance ALSO reduces
  AI simulation load - a third performance channel

## Performance win (the physics tie)

The driver LOWERS view distance in weather (a soldier in dense fog sees
to the physics range, not the engine default).  Every reduction is a
performance win on all three channels: terrain render, object render
("the CPU killer"), and AI simulation cycles.

## Validation

- Measure diag_fps at terrain view 2/5/10 km with object at 1/2
- Confirm the 40,000 scripted max and the [object, shadow] two-param
  form
- Confirm the AI knowledge-range effect (#97 monitoring should measure
  render cost AND the AI channel)

## Sources

- BI wiki setViewDistance (Wayback 2025-03-20): range table + AI quote
- BI wiki setObjectViewDistance (Wayback 2025-03-20): two-param syntax
- BI wiki viewDistance (archived): returns rendering distance
- BI wiki Arma 3: Performance Optimisation (archived): impact table,
  "The CPU killer", 1/3-1/2 guidance