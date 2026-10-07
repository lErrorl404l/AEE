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

// ─── NATO/OPFOR map symbology markers (ADR-024) ──────────────────────────
// Real engine map markers.  Every AEE symbol is a CfgMarkers entry whose
// icon is a real .paa, so it is selectable in the marker dialog, placeable
// in Eden and drawn by the engine marker layer.  The name is
// AEE_<family>_<glyph>: the family is the affiliation (b friend, o hostile,
// n neutral, u unknown) and the glyph is the class category.  The engine's
// own NATO textures are referenced where they carry the symbol; the rest
// are produced by tools/gen_symbology_markers.py under data/markers.
class CfgMarkerClasses {
    class AEE_Symbology {
        displayName = "AEE Symbology";
    };
};

class CfgMarkers {
    // Building block.  scope = 0, so it is never a usable icon on its own.
    class AEE_MarkerBase {
        scope = 0;
        markerClass = "AEE_Symbology";
        size = 32;
        shadow = 0;
        color[] = {0, 0, 0, 1};
        showEditorMarkerColor = 1;
    };

    // Friendly family (side 1).
    class AEE_b_inf: AEE_MarkerBase {
        name = "AEE Friendly Infantry";
        icon = "\A3\ui_f\data\map\markers\nato\b_inf.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_inf.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_armor: AEE_MarkerBase {
        name = "AEE Friendly Armour";
        icon = "\A3\ui_f\data\map\markers\nato\b_armor.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_armor.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_motor_inf: AEE_MarkerBase {
        name = "AEE Friendly Motorised";
        icon = "\A3\ui_f\data\map\markers\nato\b_motor_inf.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_motor_inf.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_art: AEE_MarkerBase {
        name = "AEE Friendly Artillery";
        icon = "\A3\ui_f\data\map\markers\nato\b_art.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_art.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_eng: AEE_MarkerBase {
        name = "AEE Friendly Engineer";
        icon = "\z\aee\addons\optics\data\markers\AEE_b_eng.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_b_eng.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_sig: AEE_MarkerBase {
        name = "AEE Friendly Signal";
        icon = "\z\aee\addons\optics\data\markers\AEE_b_sig.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_b_sig.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_med: AEE_MarkerBase {
        name = "AEE Friendly Medical";
        icon = "\A3\ui_f\data\map\markers\nato\b_med.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_med.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_sup: AEE_MarkerBase {
        name = "AEE Friendly Supply";
        icon = "\z\aee\addons\optics\data\markers\AEE_b_sup.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_b_sup.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_support: AEE_MarkerBase {
        name = "AEE Friendly Support";
        icon = "\A3\ui_f\data\map\markers\nato\b_support.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_support.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_recon: AEE_MarkerBase {
        name = "AEE Friendly Recon";
        icon = "\A3\ui_f\data\map\markers\nato\b_recon.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_recon.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_antiair: AEE_MarkerBase {
        name = "AEE Friendly Air Defence";
        icon = "\A3\ui_f\data\map\markers\nato\b_antiair.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_antiair.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_plane: AEE_MarkerBase {
        name = "AEE Friendly Fixed Wing";
        icon = "\A3\ui_f\data\map\markers\nato\b_plane.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_plane.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_air: AEE_MarkerBase {
        name = "AEE Friendly Rotary";
        icon = "\A3\ui_f\data\map\markers\nato\b_air.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_air.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_uav: AEE_MarkerBase {
        name = "AEE Friendly Uav";
        icon = "\A3\ui_f\data\map\markers\nato\b_uav.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_uav.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_naval: AEE_MarkerBase {
        name = "AEE Friendly Sea Surface";
        icon = "\A3\ui_f\data\map\markers\nato\b_naval.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_naval.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_sub: AEE_MarkerBase {
        name = "AEE Friendly Subsurface";
        icon = "\z\aee\addons\optics\data\markers\AEE_b_sub.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_b_sub.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_installation: AEE_MarkerBase {
        name = "AEE Friendly Installation";
        icon = "\A3\ui_f\data\map\markers\nato\b_installation.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_installation.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_hq: AEE_MarkerBase {
        name = "AEE Friendly Hq";
        icon = "\A3\ui_f\data\map\markers\nato\b_hq.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_hq.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_dot: AEE_MarkerBase {
        name = "AEE Friendly Waypoint";
        icon = "\z\aee\addons\optics\data\markers\AEE_b_dot.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_b_dot.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_unknown: AEE_MarkerBase {
        name = "AEE Friendly Unknown";
        icon = "\A3\ui_f\data\map\markers\nato\b_unknown.paa";
        texture = "\A3\ui_f\data\map\markers\nato\b_unknown.paa";
        side = 1;
        scope = 2;
    };

    // Hostile family (side 0).
    class AEE_o_inf: AEE_MarkerBase {
        name = "AEE Hostile Infantry";
        icon = "\A3\ui_f\data\map\markers\nato\o_inf.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_inf.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_armor: AEE_MarkerBase {
        name = "AEE Hostile Armour";
        icon = "\A3\ui_f\data\map\markers\nato\o_armor.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_armor.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_motor_inf: AEE_MarkerBase {
        name = "AEE Hostile Motorised";
        icon = "\A3\ui_f\data\map\markers\nato\o_motor_inf.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_motor_inf.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_art: AEE_MarkerBase {
        name = "AEE Hostile Artillery";
        icon = "\A3\ui_f\data\map\markers\nato\o_art.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_art.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_eng: AEE_MarkerBase {
        name = "AEE Hostile Engineer";
        icon = "\z\aee\addons\optics\data\markers\AEE_o_eng.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_o_eng.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_sig: AEE_MarkerBase {
        name = "AEE Hostile Signal";
        icon = "\z\aee\addons\optics\data\markers\AEE_o_sig.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_o_sig.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_med: AEE_MarkerBase {
        name = "AEE Hostile Medical";
        icon = "\A3\ui_f\data\map\markers\nato\o_med.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_med.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_sup: AEE_MarkerBase {
        name = "AEE Hostile Supply";
        icon = "\z\aee\addons\optics\data\markers\AEE_o_sup.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_o_sup.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_support: AEE_MarkerBase {
        name = "AEE Hostile Support";
        icon = "\A3\ui_f\data\map\markers\nato\o_support.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_support.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_recon: AEE_MarkerBase {
        name = "AEE Hostile Recon";
        icon = "\A3\ui_f\data\map\markers\nato\o_recon.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_recon.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_antiair: AEE_MarkerBase {
        name = "AEE Hostile Air Defence";
        icon = "\A3\ui_f\data\map\markers\nato\o_antiair.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_antiair.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_plane: AEE_MarkerBase {
        name = "AEE Hostile Fixed Wing";
        icon = "\A3\ui_f\data\map\markers\nato\o_plane.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_plane.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_air: AEE_MarkerBase {
        name = "AEE Hostile Rotary";
        icon = "\A3\ui_f\data\map\markers\nato\o_air.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_air.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_uav: AEE_MarkerBase {
        name = "AEE Hostile Uav";
        icon = "\A3\ui_f\data\map\markers\nato\o_uav.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_uav.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_naval: AEE_MarkerBase {
        name = "AEE Hostile Sea Surface";
        icon = "\A3\ui_f\data\map\markers\nato\o_naval.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_naval.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_sub: AEE_MarkerBase {
        name = "AEE Hostile Subsurface";
        icon = "\z\aee\addons\optics\data\markers\AEE_o_sub.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_o_sub.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_installation: AEE_MarkerBase {
        name = "AEE Hostile Installation";
        icon = "\A3\ui_f\data\map\markers\nato\o_installation.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_installation.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_hq: AEE_MarkerBase {
        name = "AEE Hostile Hq";
        icon = "\A3\ui_f\data\map\markers\nato\o_hq.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_hq.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_dot: AEE_MarkerBase {
        name = "AEE Hostile Waypoint";
        icon = "\z\aee\addons\optics\data\markers\AEE_o_dot.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_o_dot.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_unknown: AEE_MarkerBase {
        name = "AEE Hostile Unknown";
        icon = "\A3\ui_f\data\map\markers\nato\o_unknown.paa";
        texture = "\A3\ui_f\data\map\markers\nato\o_unknown.paa";
        side = 0;
        scope = 2;
    };

    // Neutral family (side 2).
    class AEE_n_inf: AEE_MarkerBase {
        name = "AEE Neutral Infantry";
        icon = "\A3\ui_f\data\map\markers\nato\n_inf.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_inf.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_armor: AEE_MarkerBase {
        name = "AEE Neutral Armour";
        icon = "\A3\ui_f\data\map\markers\nato\n_armor.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_armor.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_motor_inf: AEE_MarkerBase {
        name = "AEE Neutral Motorised";
        icon = "\A3\ui_f\data\map\markers\nato\n_motor_inf.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_motor_inf.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_art: AEE_MarkerBase {
        name = "AEE Neutral Artillery";
        icon = "\A3\ui_f\data\map\markers\nato\n_art.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_art.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_eng: AEE_MarkerBase {
        name = "AEE Neutral Engineer";
        icon = "\z\aee\addons\optics\data\markers\AEE_n_eng.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_n_eng.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_sig: AEE_MarkerBase {
        name = "AEE Neutral Signal";
        icon = "\z\aee\addons\optics\data\markers\AEE_n_sig.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_n_sig.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_med: AEE_MarkerBase {
        name = "AEE Neutral Medical";
        icon = "\A3\ui_f\data\map\markers\nato\n_med.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_med.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_sup: AEE_MarkerBase {
        name = "AEE Neutral Supply";
        icon = "\z\aee\addons\optics\data\markers\AEE_n_sup.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_n_sup.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_support: AEE_MarkerBase {
        name = "AEE Neutral Support";
        icon = "\A3\ui_f\data\map\markers\nato\n_support.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_support.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_recon: AEE_MarkerBase {
        name = "AEE Neutral Recon";
        icon = "\A3\ui_f\data\map\markers\nato\n_recon.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_recon.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_antiair: AEE_MarkerBase {
        name = "AEE Neutral Air Defence";
        icon = "\A3\ui_f\data\map\markers\nato\n_antiair.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_antiair.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_plane: AEE_MarkerBase {
        name = "AEE Neutral Fixed Wing";
        icon = "\A3\ui_f\data\map\markers\nato\n_plane.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_plane.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_air: AEE_MarkerBase {
        name = "AEE Neutral Rotary";
        icon = "\A3\ui_f\data\map\markers\nato\n_air.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_air.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_uav: AEE_MarkerBase {
        name = "AEE Neutral Uav";
        icon = "\A3\ui_f\data\map\markers\nato\n_uav.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_uav.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_naval: AEE_MarkerBase {
        name = "AEE Neutral Sea Surface";
        icon = "\A3\ui_f\data\map\markers\nato\n_naval.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_naval.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_sub: AEE_MarkerBase {
        name = "AEE Neutral Subsurface";
        icon = "\z\aee\addons\optics\data\markers\AEE_n_sub.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_n_sub.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_installation: AEE_MarkerBase {
        name = "AEE Neutral Installation";
        icon = "\A3\ui_f\data\map\markers\nato\n_installation.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_installation.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_hq: AEE_MarkerBase {
        name = "AEE Neutral Hq";
        icon = "\A3\ui_f\data\map\markers\nato\n_hq.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_hq.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_dot: AEE_MarkerBase {
        name = "AEE Neutral Waypoint";
        icon = "\z\aee\addons\optics\data\markers\AEE_n_dot.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_n_dot.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_unknown: AEE_MarkerBase {
        name = "AEE Neutral Unknown";
        icon = "\A3\ui_f\data\map\markers\nato\n_unknown.paa";
        texture = "\A3\ui_f\data\map\markers\nato\n_unknown.paa";
        side = 2;
        scope = 2;
    };

    // Unknown family (side 2).
    class AEE_u_inf: AEE_MarkerBase {
        name = "AEE Unknown Infantry";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_inf.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_inf.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_armor: AEE_MarkerBase {
        name = "AEE Unknown Armour";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_armor.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_armor.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_motor_inf: AEE_MarkerBase {
        name = "AEE Unknown Motorised";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_motor_inf.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_motor_inf.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_art: AEE_MarkerBase {
        name = "AEE Unknown Artillery";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_art.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_art.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_eng: AEE_MarkerBase {
        name = "AEE Unknown Engineer";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_eng.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_eng.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_sig: AEE_MarkerBase {
        name = "AEE Unknown Signal";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_sig.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_sig.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_med: AEE_MarkerBase {
        name = "AEE Unknown Medical";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_med.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_med.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_sup: AEE_MarkerBase {
        name = "AEE Unknown Supply";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_sup.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_sup.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_support: AEE_MarkerBase {
        name = "AEE Unknown Support";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_support.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_support.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_recon: AEE_MarkerBase {
        name = "AEE Unknown Recon";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_recon.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_recon.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_antiair: AEE_MarkerBase {
        name = "AEE Unknown Air Defence";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_antiair.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_antiair.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_plane: AEE_MarkerBase {
        name = "AEE Unknown Fixed Wing";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_plane.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_plane.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_air: AEE_MarkerBase {
        name = "AEE Unknown Rotary";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_air.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_air.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_uav: AEE_MarkerBase {
        name = "AEE Unknown Uav";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_uav.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_uav.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_naval: AEE_MarkerBase {
        name = "AEE Unknown Sea Surface";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_naval.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_naval.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_sub: AEE_MarkerBase {
        name = "AEE Unknown Subsurface";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_sub.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_sub.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_installation: AEE_MarkerBase {
        name = "AEE Unknown Installation";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_installation.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_installation.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_hq: AEE_MarkerBase {
        name = "AEE Unknown Hq";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_hq.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_hq.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_dot: AEE_MarkerBase {
        name = "AEE Unknown Waypoint";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_dot.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_dot.paa";
        side = 2;
        scope = 2;
    };
    class AEE_u_unknown: AEE_MarkerBase {
        name = "AEE Unknown Unknown";
        icon = "\z\aee\addons\optics\data\markers\AEE_u_unknown.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_u_unknown.paa";
        side = 2;
        scope = 2;
    };
};

#include "CfgEventHandlers.hpp"
#include "RscTitles.hpp"

