# Marker source glyph licences

These SVG files are the inner function glyphs for the AEE map markers. Each one
is a frame-less APP-6 function symbol. AEE draws the affiliation frame itself
and composites the glyph onto it.

All files here are Public domain. Redistribution is allowed. No condition
applies.

The files come from Wikimedia Commons. The author column is the artist that the
Commons record names. The source column is the original file URL.

| File | Function | Licence | Author | Source |
|---|---|---|---|---|
| `APP-6 Air Defence.svg` | Air Defence | Public domain | APP-6 and myown work | https://upload.wikimedia.org/wikipedia/commons/d/dc/APP-6_Air_Defence.svg |
| `APP-6 Armored.svg` | Armored | Public domain | Original: Noclador Vector: Chabacano | https://upload.wikimedia.org/wikipedia/commons/0/03/APP-6_Armored.svg |
| `APP-6 Army Aviation.svg` | Army Aviation | Public domain | Original: noclador, vectorized by Chabacano. | https://upload.wikimedia.org/wikipedia/commons/c/cd/APP-6_Army_Aviation.svg |
| `APP-6 Artillery.svg` | Artillery | Public domain | Original: noclador, vectorized by Chabacano. | https://upload.wikimedia.org/wikipedia/commons/7/79/APP-6_Artillery.svg |
| `APP-6 Combat Service Support.svg` | Combat Service Support | Public domain | APP-6 and myown work | https://upload.wikimedia.org/wikipedia/commons/2/2f/APP-6_Combat_Service_Support.svg |
| `APP-6 Combat Supply.svg` | Combat Supply | Public domain | APP-6 and myown work | https://upload.wikimedia.org/wikipedia/commons/a/ae/APP-6_Combat_Supply.svg |
| `APP-6 Engineer.svg` | Engineer | Public domain | APP-6 and myown work | https://upload.wikimedia.org/wikipedia/commons/6/60/APP-6_Engineer.svg |
| `APP-6 Infantry Motorised.svg` | Infantry Motorised | Public domain | APP-6 and myown work | https://upload.wikimedia.org/wikipedia/commons/0/03/APP-6_Infantry_Motorised.svg |
| `APP-6 Medical.svg` | Medical | Public domain | APP-6 and myown work | https://upload.wikimedia.org/wikipedia/commons/f/fa/APP-6_Medical.svg |
| `APP-6 Navy.svg` | Navy | Public domain | APP-6 and myown work | https://upload.wikimedia.org/wikipedia/commons/8/82/APP-6_Navy.svg |
| `APP-6 Reconnaissance.svg` | Reconnaissance | Public domain | APP-6 and myown work | https://upload.wikimedia.org/wikipedia/commons/a/ac/APP-6_Reconnaissance.svg |
| `APP-6 Signals.svg` | Signals | Public domain | APP-6 and myown work | https://upload.wikimedia.org/wikipedia/commons/3/32/APP-6_Signals.svg |
| `APP-6 Unmanned Air Recon.svg` | Unmanned Air Recon | Public domain | APP-6 and myown work | https://upload.wikimedia.org/wikipedia/commons/7/7f/APP-6_Unmanned_Air_Recon.svg |

## What is not here

The Commons NATO catalogue is mostly CC BY-SA 4.0. Share-alike would apply to a
converted texture and to the mod distribution. No CC BY-SA file is used and no
CC BY-SA file is committed.

No `.paa` from a Workshop marker mod is used. The three studied mods forbid
reuse.

The framed affiliation symbols on Commons are CC BY-SA 4.0. AEE draws the
affiliation frame itself from `fnc_symbolFrame.sqf`, so no framed image is used.

The generator strips the friendly frame rectangle from each source file and
keeps the inner glyph only. The command is
`python3 tools/gen_symbology_markers.py`.
