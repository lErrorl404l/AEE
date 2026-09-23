# Equipment source schema

Every research capture writes one JSON file under `sources/`. The build
reads them all, so a new file joins the build with no code change.

```json
{
  "retrieved": "2026-09-23",
  "note": "How this file was gathered.",
  "sources": [
    {
      "source_id": "opscore_fast_sf",
      "title": "FAST SF High Cut helmet product page",
      "url": "https://web.archive.org/web/2026/https://ops-core.com/...",
      "sha256": "hex digest of the downloaded bytes",
      "publisher": "Ops-Core (Gentex)",
      "tier": 4
    }
  ],
  "items": [
    {
      "item": "FAST SF High Cut",
      "category": "helmet",
      "family": "opscore fast",
      "mass_kg": 1.36,
      "state": "shell only",
      "maker": "Ops-Core",
      "country": "US",
      "era": "modern",
      "note": "verbatim mass line from the source",
      "source_id": "opscore_fast_sf"
    }
  ],
  "leads": [
    {"item": "not primary enough", "url": "https://...", "why": "forum estimate"}
  ],
  "conflicts": [
    {
      "item": "PVS-14",
      "field": "mass_kg",
      "value_a": 0.352,
      "source_a": "nightoptics_pvs14",
      "value_b": 0.31,
      "source_b": "another_maker",
      "note": "both values recorded, neither discarded"
    }
  ]
}
```

## Fields

- `source_id`: stable snake_case key. One id per document.
- `tier`: 1 issue standard or specification, 2 military manual or
  technical manual, 3 reference work, 4 manufacturer, 5 compilation.
  A tier 5 source (a compilation, for example Wikipedia) is weaker, but a
  labelled weak value beats a silent zero, so it DOES become an item.  It
  enters at grade `claimed` and is counted in the build output, so the
  confidence mix is visible.  A tier 1-4 value always displaces a tier 5
  value for the same family and category.  A physically impossible mass
  (above 40 kg or below 1 g for a carried item) is rejected whatever the
  tier.  Prefer tiers 1-4; reach for 5 only when nothing stronger exists,
  and sanity-check the figure against the material and the size.
- `category`: one of `uniform`, `garment`, `vest`, `rucksack`, `helmet`,
  `webbing`, `footwear`, `nv`, `thermal`, `optic`, `laser`, `light`,
  `mount`, `suppressor`, `rangefinder`, `binocular`, `gps`, `designator`,
  `radio`, `medical`, `tool`, `hydration`, `food`, `power`, `misc`.
  The build folds the plural `binoculars` onto `binocular`. A rucksack row
  states the mass of the EMPTY pack: the load model weighs the contents
  separately, so a filled mass would count them twice.
- `family`: the lowercase keyword signal that a classname carries, for
  example `pvs14`, `peq15`, `prc152`, `alice`, `fast`. One word or a
  short phrase, no punctuation.
- `mass_kg`: one published number in kilograms. Convert grams exactly
  (`1000 g = 1 kg`). Never estimate, never average, never invent.
- `state`: the configuration the number belongs to, for example
  `shell only`, `complete`, `without magazine`, `empty`, `with battery`.
  A mass without its state is not usable.
- `note`: the verbatim line that carries the mass, with enough words to
  find it in the source again.

## Rules

1. Real published data only. Mod and engine config values are identity
   evidence and never a value source.
2. Primary sources first: issue specifications, military manuals,
   manufacturer datasheets and product pages. Use an Internet Archive
   snapshot when the live site blocks.
3. A tier 5 source is allowed as a last resort: it becomes an item at
   grade `claimed`, never at a stronger grade, and it is counted in the
   build output. It never displaces a tier 1-4 value. A tier 5 source
   that only *supports* a value (corroboration) goes to `leads`, and so
   does anything you would not put in front of a reader.
4. Record a disagreement in `conflicts` and keep the higher tier value
   on the item. Never average two sources.
5. One item per row. A product family with published variants gets one
   row per variant, and `state` names the variant.
6. Write only your own output file. Never edit another file and never
   commit.
