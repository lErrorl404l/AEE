# Capturing screenshots for the visual QA pass

The engine draws the map, the optics and the sky. A config value that is set but
never drawn looks correct to every config assertion. Only a rendered frame shows
it. A dedicated server renders nothing, so the frames come from a client by
hand. This page is the procedure.

The analysis half is `tools/validation/compare_screens.py`. It takes a baseline
frame and a candidate frame of the same scene and reports the delta, where it
is, and the dominant colours of each frame.

## What the differential proves

- A surface that AEE is meant to change must differ from vanilla. If the delta
  is near zero, the config re-declare did not reach the render.
- The dominant colours name the palette. A water-blue shift from `#4878b0` to
  `#2868a8` is visible as evidence, not as an opinion.

Exact pixel registration between two game sessions is not practical. Treat the
change grid and the dominant colours as the evidence. Do not read a large mean
delta as a defect on its own.

## Capture

Run each step twice: once with AEE, once without it. Use the same scene both
times.

1. Pin the scene. Open the debug console (Esc, then the debug console) and run:

   ```sqf
   setDate [2035, 6, 21, 12, 0]; 0 setOvercast 0; 0 setFog 0; 0 setRain 0; forceWeatherChange;
   ```

   For the night sky, use `setDate [2035, 6, 21, 0, 0]`.

2. Frame the surface and capture it with a label:

   ```sqf
   screenshot "map_aee";
   ```

   Use the same label with the suffix `_vanilla` in the run without AEE.

3. Repeat for each surface. One label per surface and zoom:

   | Surface | Label stem | Notes |
   |---------|-----------|-------|
   | Map overlay, grid, legend | `map` | Open the map, fix the zoom, one capture per zoom |
   | Map colours | `map` | The same map captures carry the palette |
   | GPS | `gps` | Open the GPS |
   | Minimap | `minimap` | Top-right corner in view |
   | Thermal | `thermal` | Look through the thermal optic at a scene with a hot and a cold object |
   | Night vision | `nvg` | Look through the NVG at a dim scene |
   | Sky, aurora, stars | `sky` | Look up at night |

4. The files land in the Arma profile `Screenshots` directory as
   `<label>.png`.

With AEE loaded you can also take the labelled dev screenshot, which adds a
paired state line to the RPT:

```sqf
["map_aee"] call aee_dev_fnc_devScreenshot;
```

## Compare

```sh
python3 tools/validation/compare_screens.py \
    --label map \
    --baseline vanilla_map.png \
    --candidate aee_map.png \
    --expect-change 0.02
```

`--expect-change` fails the run when the frames are near identical, which is the
signal that AEE did not change the render. Add `--crop X,Y,W,H` to compare only
the region of interest, for example the sky in a frame that also holds a HUD.
