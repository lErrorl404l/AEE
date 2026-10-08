/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * Terrain and map-feature location symbols (CfgLocationTypes re-declare).
 *
 * One class per engine location type.  The engine merges each class by name,
 * so the drawStyle, the base and every field not set here are unchanged.  The
 * eight icon classes (Hill, ViewPoint, RockArea, BorderCrossing and the four
 * vegetation classes) carry an AEE topographic texture and the standard
 * colour.  The name and area classes carry the standard colour, size and
 * label font.
 *
 * The authority is STANAG 3675, succeeded by the DGIWG Symbol Register (the
 * DTM50 product), with the US Army FM 21-31 and the USGS Topographic Map
 * Symbols sheet as the public-domain fallback.  The values are generated from
 * data/symbology/terrain_symbols.json and locked by tools/tests/test_terrain.py.
 * Relief prints brown, water blue, vegetation green.
 *
 * The engine ceiling: drawStyle is a fixed enum (name, icon, area, mount).
 * The engine owns the draw routine; a mod changes the texture, colour, size,
 * font, shadow and importance only.
 */
class CfgLocationTypes {
    // Relief and control: the engine draws Mount as relief.  FM 21-31 s10, s22.
    class Mount {
        color[] = {0.70, 0.48, 0.32, 1};
        size = 18;
        font = "AEEFont";
        textSize = 0.09;
        shadow = 1;
    };
    class Hill {
        texture = "\z\aee\addons\optics\data\terrain\hill.paa";
        color[] = {1, 1, 1, 1};
        size = 14;
        shadow = 0;
    };
    class RockArea {
        texture = "\z\aee\addons\optics\data\terrain\rock.paa";
        color[] = {1, 1, 1, 1};
        size = 12;
        shadow = 0;
    };
    class ViewPoint {
        texture = "\z\aee\addons\optics\data\terrain\monument.paa";
        color[] = {1, 1, 1, 1};
        size = 12;
        shadow = 0;
    };

    // Boundary.  FM 21-31 s23.
    class BorderCrossing {
        texture = "\z\aee\addons\optics\data\terrain\border_crossing.paa";
        color[] = {1, 1, 1, 1};
        size = 12;
        shadow = 0;
    };

    // Vegetation.  FM 21-31 s11.
    class VegetationBroadleaf {
        texture = "\z\aee\addons\optics\data\terrain\deciduous.paa";
        color[] = {1, 1, 1, 1};
        size = 12;
        shadow = 0;
    };
    class VegetationFir {
        texture = "\z\aee\addons\optics\data\terrain\coniferous.paa";
        color[] = {1, 1, 1, 1};
        size = 12;
        shadow = 0;
    };
    class VegetationPalm {
        texture = "\z\aee\addons\optics\data\terrain\palm.paa";
        color[] = {1, 1, 1, 1};
        size = 12;
        shadow = 0;
    };
    class VegetationVineyard {
        texture = "\z\aee\addons\optics\data\terrain\vineyard.paa";
        color[] = {1, 1, 1, 1};
        size = 12;
        shadow = 0;
    };

    // Populated places and labels.  FM 21-31 s19, s20.
    class Name {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 12;
        font = "AEEFont";
        textSize = 0.06;
        shadow = 1;
    };
    class NameMarine {
        color[] = {0.00, 0.50, 0.75, 1};
        size = 12;
        font = "AEEFont";
        textSize = 0.06;
        shadow = 1;
    };
    class NameCityCapital {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 14;
        font = "AEEFont";
        textSize = 0.09;
        shadow = 1;
    };
    class NameCity {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 13;
        font = "AEEFont";
        textSize = 0.075;
        shadow = 1;
    };
    class NameVillage {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 11;
        font = "AEEFont";
        textSize = 0.06;
        shadow = 1;
    };
    class NameLocal {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 10;
        font = "AEEFont";
        textSize = 0.05;
        shadow = 1;
    };

    // Areas.  FM 21-31 s19, s20.
    class Strategic {
        color[] = {0.80, 0.10, 0.10, 1};
        size = 16;
        font = "AEEFont";
        textSize = 0.08;
        shadow = 1;
    };
    class StrongpointArea {
        color[] = {0.80, 0.10, 0.10, 1};
        size = 14;
        font = "AEEFont";
        textSize = 0.07;
        shadow = 1;
    };
    class FlatArea {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 14;
        font = "AEEFont";
        textSize = 0.07;
        shadow = 0;
    };
    class FlatAreaCity {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 14;
        font = "AEEFont";
        textSize = 0.07;
        shadow = 0;
    };
    class FlatAreaCitySmall {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 12;
        font = "AEEFont";
        textSize = 0.06;
        shadow = 0;
    };
    class CityCenter {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 16;
        font = "AEEFont";
        textSize = 0.08;
        shadow = 1;
    };
    class Airport {
        color[] = {0.80, 0.10, 0.10, 1};
        size = 16;
        font = "AEEFont";
        textSize = 0.07;
        shadow = 1;
    };
    class fakeTown {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 12;
        font = "AEEFont";
        textSize = 0.06;
        shadow = 0;
    };
    class Area {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 12;
        font = "AEEFont";
        textSize = 0.06;
        shadow = 0;
    };
    class Flag {
        color[] = {0.80, 0.10, 0.10, 1};
        size = 12;
        font = "AEEFont";
        textSize = 0.05;
        shadow = 0;
    };
};
