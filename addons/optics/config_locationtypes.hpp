/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * Terrain and map-feature location symbols (CfgLocationTypes re-declare).
 *
 * One class per engine location type.  Each re-declared class RESTATES its
 * vanilla parent, read from the engine's own config.  The inheritance graph
 * is the merged one the engine resolves at load:
 *
 *   - The engine core, `Dta/bin.pbo` (`bin_raw/bin/config.cpp:14800`), holds
 *     `Mount` and `Name` as the two parentless roots and derives `Strategic`,
 *     the name classes, `Hill` and the vegetation classes from them.
 *   - `ui_f.pbo` (`ui_f_x2/config.cpp:81444`) re-declares the same names and
 *     adds `fakeTown`, `Area` and `Flag`.
 *
 * A reopen that omits the parent invokes the engine Empty syntax and strips
 * every inherited value.  That is what produced, once per class,
 *   Warning Message: No entry 'bin\config.bin/CfgLocationTypes/<cls>.drawStyle'
 *   Warning Message: '/' is not a value
 *   Wrong location draw style - ""
 * in the RPT, because `drawStyle` and the base `texture` live on the parent
 * (`Name` or `Hill`) and were dropped.  The three parentless roots (`Mount`,
 * `Name`, `Area`) have no parent to restate and stay bare, exactly as `ui_f`
 * declares them.
 *
 * The eight icon classes (Hill, ViewPoint, RockArea, BorderCrossing and the
 * four vegetation classes) carry an AEE topographic texture and the standard
 * colour.  The name and area classes carry the standard colour, size and
 * label font.
 *
 * The icon `size` is expressed in the user's interface scale, so a larger
 * interface size gives larger symbols.  The interface scale is
 * uiScale = 1/safeZoneH (BIKI Pixel Grid System: at 1080p/16:9 the interface
 * size Normal is uiScale 0.7 and safeZoneH 1.42857 = 1/0.7), so the
 * expression N / (safezoneH * 0.7) gives N at Normal and scales linearly
 * with it.  The vanilla sizeEx* safezone idiom is a constant 0.04 and would
 * not scale.  The name and area classes carry no icon, so their size stays
 * the vanilla value.
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
    // The two parentless roots.  No parent to restate; ui_f declares them bare.
    class Mount {
        color[] = {0.70, 0.48, 0.32, 1};
        size = 18;
        font = "RobotoCondensed";
        textSize = 0.09;
        shadow = 1;
    };
    class Name {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 12;
        font = "RobotoCondensed";
        textSize = 0.06;
        shadow = 1;
    };

    // Areas.  FM 21-31 s19, s20.
    class Strategic: Name {
        color[] = {0.80, 0.10, 0.10, 1};
        size = 16;
        font = "RobotoCondensed";
        textSize = 0.08;
        shadow = 1;
    };
    class StrongpointArea: Strategic {
        color[] = {0.80, 0.10, 0.10, 1};
        size = 14;
        font = "RobotoCondensed";
        textSize = 0.07;
        shadow = 1;
    };
    class FlatArea: Strategic {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 14;
        font = "RobotoCondensed";
        textSize = 0.07;
        shadow = 0;
    };
    class FlatAreaCity: FlatArea {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 14;
        font = "RobotoCondensed";
        textSize = 0.07;
        shadow = 0;
    };
    class FlatAreaCitySmall: FlatAreaCity {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 12;
        font = "RobotoCondensed";
        textSize = 0.06;
        shadow = 0;
    };
    class CityCenter: Strategic {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 16;
        font = "RobotoCondensed";
        textSize = 0.08;
        shadow = 1;
    };
    class Airport: Strategic {
        color[] = {0.80, 0.10, 0.10, 1};
        size = 16;
        font = "RobotoCondensed";
        textSize = 0.07;
        shadow = 1;
    };

    // Populated places and labels.  FM 21-31 s19, s20.
    class NameMarine: Name {
        color[] = {0.00, 0.50, 0.75, 1};
        size = 12;
        font = "RobotoCondensed";
        textSize = 0.06;
        shadow = 1;
    };
    class NameCityCapital: Name {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 14;
        font = "RobotoCondensed";
        textSize = 0.09;
        shadow = 1;
    };
    class NameCity: Name {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 13;
        font = "RobotoCondensed";
        textSize = 0.075;
        shadow = 1;
    };
    class NameVillage: Name {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 11;
        font = "RobotoCondensed";
        textSize = 0.06;
        shadow = 1;
    };
    class NameLocal: Name {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 10;
        font = "RobotoCondensed";
        textSize = 0.05;
        shadow = 1;
    };

    // Relief and control: the engine draws Hill as an icon.  FM 21-31 s10, s22.
    class Hill: Name {
        texture = "\z\aee\addons\optics\data\terrain\hill.paa";
        color[] = {1, 1, 1, 1};
        size = "14 / (safezoneH * 0.7)";
        shadow = 0;
    };
    class ViewPoint: Hill {
        texture = "\z\aee\addons\optics\data\terrain\monument.paa";
        color[] = {1, 1, 1, 1};
        size = "16 / (safezoneH * 0.7)";
        shadow = 0;
    };
    class RockArea: Hill {
        texture = "\z\aee\addons\optics\data\terrain\rock.paa";
        color[] = {1, 1, 1, 1};
        size = "12 / (safezoneH * 0.7)";
        shadow = 0;
    };

    // Boundary.  FM 21-31 s23.
    class BorderCrossing: Hill {
        texture = "\z\aee\addons\optics\data\terrain\border_crossing.paa";
        color[] = {1, 1, 1, 1};
        size = "16 / (safezoneH * 0.7)";
        shadow = 0;
    };

    // Vegetation.  FM 21-31 s11.
    class VegetationBroadleaf: Hill {
        texture = "\z\aee\addons\optics\data\terrain\deciduous.paa";
        color[] = {1, 1, 1, 1};
        size = "18 / (safezoneH * 0.7)";
        shadow = 0;
    };
    class VegetationFir: Hill {
        texture = "\z\aee\addons\optics\data\terrain\coniferous.paa";
        color[] = {1, 1, 1, 1};
        size = "18 / (safezoneH * 0.7)";
        shadow = 0;
    };
    class VegetationPalm: Hill {
        texture = "\z\aee\addons\optics\data\terrain\palm.paa";
        color[] = {1, 1, 1, 1};
        size = "18 / (safezoneH * 0.7)";
        shadow = 0;
    };
    class VegetationVineyard: Hill {
        texture = "\z\aee\addons\optics\data\terrain\vineyard.paa";
        color[] = {1, 1, 1, 1};
        size = "16 / (safezoneH * 0.7)";
        shadow = 0;
    };

    class fakeTown: Name {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 12;
        font = "RobotoCondensed";
        textSize = 0.06;
        shadow = 0;
    };
    // Parentless root.
    class Area {
        color[] = {0.15, 0.15, 0.15, 1};
        size = 12;
        font = "RobotoCondensed";
        textSize = 0.06;
        shadow = 0;
    };
    class Flag: Hill {
        color[] = {0.80, 0.10, 0.10, 1};
        size = 12;
        font = "RobotoCondensed";
        textSize = 0.05;
        shadow = 0;
    };
};
