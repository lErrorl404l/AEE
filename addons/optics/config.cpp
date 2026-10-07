/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = 2.04;
        requiredAddons[] = {
            "aee_main",
            "aee_core",
            "cba_main",
            "cba_xeh"
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
            "z\aee\addons\optics\data\fonts\rajdhani\AEEFont9",
            "z\aee\addons\optics\data\fonts\rajdhani\AEEFont10",
            "z\aee\addons\optics\data\fonts\rajdhani\AEEFont11",
            "z\aee\addons\optics\data\fonts\rajdhani\AEEFont12"
        };
        spaceWidth = 0.9;
    };
    class AEEFontMono {
        fonts[] = {
            "z\aee\addons\optics\data\fonts\b612mono\AEEFontMono9",
            "z\aee\addons\optics\data\fonts\b612mono\AEEFontMono10",
            "z\aee\addons\optics\data\fonts\b612mono\AEEFontMono11",
            "z\aee\addons\optics\data\fonts\b612mono\AEEFontMono12"
        };
        spaceWidth = 0.5;
    };
};

// Repoint the map grid labels at the AEE font at load time.  No runtime
// command repoints fontGrid, so this override is the only route.
class RscMapControl {
    fontGrid = "AEEFont";
};

#include "CfgEventHandlers.hpp"
#include "RscTitles.hpp"

