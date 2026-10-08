/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * Terrain and map-feature object icons (RscMapControl re-declare).
 *
 * This file is included INSIDE the RscMapControl block in config.cpp, beside
 * the fontGrid and fontNames fields.  It does not open a second RscMapControl
 * class.  One nested class per engine object icon: church, lighthouse, the
 * power works, the works and the transport points.  Each carries an AEE
 * topographic icon and the standard colour.
 *
 * The operator directive: take the vanilla class and update it with our own
 * values.  These classes are parentless in the engine config, so the vanilla
 * visibility coefficients (coefMin, coefMax) cannot be inherited.  AEE
 * restates them from the engine's own config, so the re-declare keeps the
 * vanilla draw behaviour and overrides only the icon, the colour, the size
 * and the importance.  The values are the vanilla ui_f ones (ui_f.pbo,
 * RscMapControl icon classes); a size below the vanilla value draws the icon
 * too small on the map, so the vanilla size is kept.
 *
 * The engine ceiling: the object-to-icon routing is engine-internal.  Arma
 * config class names resolve case-insensitively, so the engine core names
 * (Dta/bin.pbo: `Church`, `Transmitter`, `Watertower` ...) and the ui_f names
 * (`church`, `transmitter`, `watertower` ...) are the same class.  No mapType
 * field exists in any shipped config, so a re-texture reaches only the objects
 * the engine already routes to a class.  Bohemia ticket T157884 records that a
 * custom object map icon needs engine support.
 *
 * The authority is STANAG 3675, succeeded by the DGIWG Symbol Register (the
 * DTM50 product), with FM 21-31 and the USGS sheet as the public-domain
 * fallback.  The values are generated from data/symbology/terrain_symbols.json
 * and locked by tools/tests/test_terrain.py.
 */

    // Vegetation.  FM 21-31 s11.
    class Bush {
        icon = "\z\aee\addons\optics\data\terrain\brushwood.paa";
        color[] = {1, 1, 1, 1};
        size = 7;
        importance = 1;
        coefMin = 0.25;
        coefMax = 4;
    };
    class SmallTree {
        icon = "\z\aee\addons\optics\data\terrain\deciduous.paa";
        color[] = {1, 1, 1, 1};
        size = 12;
        importance = 1;
        coefMin = 0.25;
        coefMax = 4;
    };
    class Tree {
        icon = "\z\aee\addons\optics\data\terrain\deciduous.paa";
        color[] = {1, 1, 1, 1};
        size = 12;
        importance = 1;
        coefMin = 0.25;
        coefMax = 4;
    };

    // Relief.  FM 21-31 s10.
    class Rock {
        icon = "\z\aee\addons\optics\data\terrain\rock.paa";
        color[] = {1, 1, 1, 1};
        size = 12;
        importance = 1;
        coefMin = 0.25;
        coefMax = 4;
    };

    // Works.  FM 21-31 s19, s21.
    class church {
        icon = "\z\aee\addons\optics\data\terrain\church.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class Chapel {
        icon = "\z\aee\addons\optics\data\terrain\chapel.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class Cross {
        icon = "\z\aee\addons\optics\data\terrain\cross.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class Ruin {
        icon = "\z\aee\addons\optics\data\terrain\ruin.paa";
        color[] = {1, 1, 1, 1};
        size = 16;
        importance = 1;
        coefMin = 1;
        coefMax = 4;
    };
    class hospital {
        icon = "\z\aee\addons\optics\data\terrain\hospital.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class fuelstation {
        icon = "\z\aee\addons\optics\data\terrain\fuel_station.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class Stack {
        icon = "\z\aee\addons\optics\data\terrain\stack.paa";
        color[] = {1, 1, 1, 1};
        size = 16;
        importance = 1;
        coefMin = 0.4;
        coefMax = 2;
    };
    class transmitter {
        icon = "\z\aee\addons\optics\data\terrain\radio_tower.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class watertower {
        icon = "\z\aee\addons\optics\data\terrain\water_tower.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class lighthouse {
        icon = "\z\aee\addons\optics\data\terrain\lighthouse.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class power {
        icon = "\z\aee\addons\optics\data\terrain\power_plant.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class powersolar {
        icon = "\z\aee\addons\optics\data\terrain\solar.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class powerwind {
        icon = "\z\aee\addons\optics\data\terrain\wind.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class powerwave {
        icon = "\z\aee\addons\optics\data\terrain\wave.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class Fountain {
        icon = "\z\aee\addons\optics\data\terrain\fountain.paa";
        color[] = {1, 1, 1, 1};
        size = 11;
        importance = 1;
        coefMin = 0.25;
        coefMax = 4;
    };
    class Tourism {
        icon = "\z\aee\addons\optics\data\terrain\tourism.paa";
        color[] = {1, 1, 1, 1};
        size = 16;
        importance = 1;
        coefMin = 0.7;
        coefMax = 4;
    };
    class ViewTower {
        icon = "\z\aee\addons\optics\data\terrain\view_tower.paa";
        color[] = {1, 1, 1, 1};
        size = 16;
        importance = 1;
        coefMin = 0.5;
        coefMax = 4;
    };

    // Transport.  FM 21-31 s12, s16.
    class busstop {
        icon = "\z\aee\addons\optics\data\terrain\bus_stop.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class quay {
        icon = "\z\aee\addons\optics\data\terrain\quay.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };
    class Shipwreck {
        icon = "\z\aee\addons\optics\data\terrain\shipwreck.paa";
        color[] = {1, 1, 1, 1};
        size = 24;
        importance = 1;
        coefMin = 0.85;
        coefMax = 1;
    };

    // Military structures.  FM 21-31 s19.
    class Bunker {
        icon = "\z\aee\addons\optics\data\terrain\bunker.paa";
        color[] = {1, 1, 1, 1};
        size = 14;
        importance = 1;
        coefMin = 0.25;
        coefMax = 4;
    };
    class Fortress {
        icon = "\z\aee\addons\optics\data\terrain\fortress.paa";
        color[] = {1, 1, 1, 1};
        size = 16;
        importance = 1;
        coefMin = 0.25;
        coefMax = 4;
    };
