/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = 2.04;
        requiredAddons[] = {
            "aee_lib",
            "aee_core",
            "aee_weather",
            "aee_atmos",
            "aee_material",
            "cba_main",
            "cba_xeh",
            "cba_settings"
        };
        author = AUTHOR;
        authors[] = AUTHORS;
        url = URL;
        VERSION_CONFIG;
    };
};

// The AEE font families.  The converted .fxy glyph index and .paa glyph
// atlases are produced by the operator procedure in
// docs/wiki/research/arma-font-surface.md.  Until they exist the engine
// falls back to its default font, so the default state is unchanged.
class CfgFontFamilies {
    class AEEFont {
        fonts[] = {
            "z\aee\addons\cartography\data\fonts\rajdhani\AEEFont9",
            "z\aee\addons\cartography\data\fonts\rajdhani\AEEFont10",
            "z\aee\addons\cartography\data\fonts\rajdhani\AEEFont11",
            "z\aee\addons\cartography\data\fonts\rajdhani\AEEFont12"
        };
        spaceWidth = 0.9;
    };
    class AEEFontMono {
        fonts[] = {
            "z\aee\addons\cartography\data\fonts\b612mono\AEEFontMono9",
            "z\aee\addons\cartography\data\fonts\b612mono\AEEFontMono10",
            "z\aee\addons\cartography\data\fonts\b612mono\AEEFontMono11",
            "z\aee\addons\cartography\data\fonts\b612mono\AEEFontMono12"
        };
        spaceWidth = 0.5;
    };
};

// The map terrain palette and the object icons are included inside this block
// so the engine class is not declared twice.  The map grid font is NOT
// repointed here.  The AEE fonts need the FontToTGA operator step (see
// docs/wiki/research/arma-font-surface.md), and the engine draws no text for a
// family whose glyph files are absent, so the engine font stays until the AEE
// glyphs ship.  Re-point fontGrid and fontNames at AEEFont then.
//
// The engine grid fields SPLIT: colorGrid colours the EDGE COORDINATE NUMBERS
// and colorGridMap colours the in-map grid LINES (engine source: Poseidon
// UIMap.cpp, CStaticMap::DrawGrid).  The engine edge ruler is UNRELIABLE: it
// places each number half a grid spacing from its line and clips it to the
// control rect, and the northing spacing is wScreen/hScreen times the easting
// spacing, so at close zoom the left and right numbers leave the control and
// the operator sees them missing.  There is no per-axis toggle, so keeping the
// engine numbers would double every edge the AEE ruler already labels.  Both
// engine fields are off: the AEE MGRS overlay (FUNC(mgrsGridLines) and
// FUNC(mgrsMapDraw)) is the SINGLE complete ruler, lines and four-edge numbers.
class RscMapControl {
#include "config_mapcolors.hpp"
#include "config_mapicons.hpp"
    colorGrid[] = {0, 0, 0, 0};
    colorGridMap[] = {0, 0, 0, 0};
    sizeExGrid = 0.04;
};

// The engine cursor tooltip is filled and shown by closed engine C++ AFTER the
// map Draw event, so the script hide in FUNC(mgrsMapDraw) loses the race.  Make
// its text and every backdrop transparent at the config instead, so nothing
// renders whichever child the engine shows.
class RscControlsGroupNoScrollbars;
class RscText;
class RscStructuredText;
class RscMapControlTooltip: RscControlsGroupNoScrollbars {
    class Controls {
        class Background: RscText {
            colorBackground[] = {0, 0, 0, 0};
        };
        class InfoBackground: RscStructuredText {
            colorBackground[] = {0, 0, 0, 0};
        };
        class Info: RscStructuredText {
            colorText[] = {0, 0, 0, 0};
        };
        class AssetsBackground: RscStructuredText {
            colorBackground[] = {0, 0, 0, 0};
        };
        class Assets: RscStructuredText {
            colorText[] = {0, 0, 0, 0};
        };
        class PictureBackground: RscText {
            colorBackground[] = {0, 0, 0, 0};
        };
    };
};

#include "config_locationtypes.hpp"
#include "config_mapdisplays.hpp"
#include "config_curator.hpp"

#include "CfgEventHandlers.hpp"
#include "RscTitles.hpp"
