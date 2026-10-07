# Map grid and cursor surface

Read-only record of what the Arma 3 engine exposes for the map grid and the
map cursor. The MGRS presentation work uses it. No code was changed to
produce it.

- Repo: `/ext/Development/AEE`, HEAD `98a918c`.
- Method: the BIKI pages through the Wayback Machine (the live site returns
  HTTP 403 to the fetcher), the shipped world config, and the repository's own
  map-control usage.
- Every claim cites a page or a file line. An unverified claim is marked
  UNKNOWN.

## 1. The map control

| Item | Value | Evidence |
|---|---|---|
| Control | `findDisplay 12 displayCtrl 51` (`RscMapControl`) | BIKI ctrlAddEventHandler, example 3 |
| Draw event | `ctrlAddEventHandler ["Draw", { params ["_ctrl"] }]` | BIKI ctrlAddEventHandler; User Interface Event Handlers, `onDraw`, "Use on: Map" |
| Local proof | A `Draw` handler on a `RscMapControl` with `drawLine` | `addons/thermal/functions/outline/fnc_outlineCanvas.sqf:36-49` |

The Draw event is the only map-scoped draw hook. `Draw3D` and `Draw2D` are
screen and world space, not map-scoped.

## 2. Draw commands on a map control

The BIKI category "GUI Control - Map" lists 23 pages. The draw commands are:
`drawArrow`, `drawEllipse`, `drawIcon`, `drawLine`, `drawLocation`,
`drawPolygon`, `drawRectangle`, `drawTriangle` and `drawXPolygon` (added in
2.20). `drawLink` is not a map command. `drawIcon3D` and `drawLine3D` are
world-space commands for the `Draw3D` event, not map commands.

Source: BIKI Category: Command Group: GUI Control - Map, and the per-command
pages drawIcon and drawLine.

## 3. Coordinate conversion and the cursor

| Command | Exists | Signature | Notes |
|---|---|---|---|
| `ctrlMapScreenToWorld` | yes | `control ctrlMapScreenToWorld [x,y]` -> Position2D | screen to world |
| `ctrlMapWorldToScreen` | yes | `control ctrlMapWorldToScreen position` -> `[x,y]` | world to screen |
| `ctrlMapAnimAdd` | yes | `[time, zoom, position]` | zoom 0.001 is maximum, 1 is minimum |
| `ctrlMapAnimCommit` | yes | `ctrlMapAnimCommit control` | |
| `ctrlMapScale` | yes | `ctrlMapScale control` -> Number | 1 is minimum zoom, 0.001 is maximum |
| `ctrlMapPosition` | yes | -> `[x,y,w,h]` | the control rectangle |
| `ctrlMapMouseOver` | yes | -> the map sign under the cursor | a unit, vehicle, marker or task, not a coordinate |
| `ctrlMapMousePosition` | no | - | not a command |

`getMousePosition` returns UI coordinates. No engine command returns the world
position under the map cursor. A script computes it as
`ctrlMapScreenToWorld (getMousePosition)`. The main map is not fullscreen, so
a map control's coordinates are not the screen coordinates. The BIKI note
(Ceeeb) says to use `ctrlPosition` for that conversion. There is no
cursor-move event. The `onMouseMoving` and `onMouseHolding` handlers are UI
events for interactive controls, so a Draw handler poll is the robust route.

## 4. The vanilla cursor readout

The default `RscMapControl` config exposes styling only: `fontGrid`,
`sizeExGrid`, `colorGrid`, `colorMap` and a `Legend` class. No command and no
config field was found that replaces, repoints or hides the cursor coordinate
and elevation readout. UNKNOWN whether any exists. This matches the MGRS
close-out record: the `ItemGPS` readout is engine-hardcoded.

## 5. The CfgWorlds Grid class

From the shipped Altis config
(`Addons/map_altis/a3/map_altis/config.cpp:2338-2368`):

```
class Grid: Grid
{
    offsetX = 0;
    offsetY = 30720;
    class Zoom1 { zoomMax = 0.05; format = "XY"; formatX = "000"; formatY = "000"; stepX = 100; stepY = -100; };
    class Zoom2 { zoomMax = 0.5;  format = "XY"; formatX = "00";  formatY = "00";  stepX = 1000; stepY = -1000; };
    class Zoom3 { zoomMax = 1e30; format = "XY"; formatX = "0";   formatY = "0";   stepX = 10000; stepY = -10000; };
};
```

`zoomMax` is the zoom threshold for the block, `stepX` and `stepY` are the
grid spacing in metres, and `formatX` and `formatY` are digit patterns. The BI
format is `"XY"` with numeric digits. No script command writes the Grid class.
An override is a config patch at load. UNKNOWN whether `format` accepts
arbitrary literal text; some worlds show letter-bearing output from
`mapGridPosition`.

Source: the shipped config above, and BIKI Arma 3: CfgWorlds Config Reference
for the companion keys.

## 6. Mission event handlers

| Event | Exists | Parameters | Notes |
|---|---|---|---|
| `Map` | yes | `[_mapIsOpened, _mapIsForced]` | fires on open and close, user or `openMap` |
| `Draw3D` | yes | none | each frame, client side |
| `Draw2D` | yes | none | each frame, after all UI |

There is no map-specific 3D draw event. The map-scoped draw hook is the
control-level Draw event.

Source: BIKI Arma 3: Mission Event Handlers.

## Result for AEE

The map grid lines cannot be relabelled in place, so AEE draws its own MGRS
grid over them. The vanilla cursor tooltip cannot be replaced, so AEE draws
its own readout adjacent to it. Both are operator-only, so no headless probe
claims a relabelled grid or a replaced tooltip.
