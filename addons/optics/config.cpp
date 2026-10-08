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
            "aee_nightvision",
            "aee_thermal",
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

// The map terrain palette and the object icons are included inside this block
// so the engine class is not declared twice.  The map grid font is NOT
// repointed here.  The AEE fonts need the FontToTGA operator step (see
// docs/wiki/research/arma-font-surface.md), and the engine draws no text for a
// family whose glyph files are absent, so the engine font stays until the AEE
// glyphs ship.  Re-point fontGrid and fontNames at AEEFont then.
class RscMapControl {
#include "config_mapcolors.hpp"
#include "config_mapicons.hpp"
};

#include "config_locationtypes.hpp"
#include "config_mapdisplays.hpp"
#include "config_curator.hpp"

// ─── NATO/OPFOR map symbology markers (ADR-023) ──────────────────────────
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

// The marker colour classes.  Every AEE marker texture carries its OWN colour
// (the affiliation frame, the black glyph and the standard fills), so the
// engine tint must be NEUTRAL: ColorAEE is white and leaves the texture's
// colours untouched.  The affiliation classes are kept because
// FUNC(symbologyAffiliation) reads a mission marker's original colour through
// them before AEE converts it.
class CfgMarkerColors {
    class ColorAEE { color[] = {1, 1, 1, 1}; };
    class ColorWEST { color[] = {0, 1, 1, 1}; };
    class ColorEAST { color[] = {1, 0, 0, 1}; };
    class ColorGUER { color[] = {0, 1, 0, 1}; };
    class ColorCIV { color[] = {1, 0, 1, 1}; };
    class ColorUNKNOWN { color[] = {1, 1, 0, 1}; };
};

class CfgMarkers {
    // Building block.  scope = 0, so it is never a usable icon on its own.
    class AEE_MarkerBase {
        scope = 0;
        markerClass = "AEE_Symbology";
        size = 32;
        shadow = 0;
        // Neutral, so each texture shows its own colours (the colour IS the
        // information).  The engine tint is applied by setMarkerColorLocal;
        // ColorAEE is white.
        color[] = {1, 1, 1, 1};
        showEditorMarkerColor = 1;
    };

    // The complete AEE APP-6 marker set, generated from the pulled catalogue
    // by tools/gen_symbology_catalogue.py.  Do not edit by hand.
#include "config_markers.hpp"

    // The composed APP-6 cross-product: each real function glyph re-framed in
    // the four affiliation frames AEE draws from the APP-6 geometry, generated
    // by tools/gen_symbology_crossproduct.py.  Do not edit by hand.
#include "config_crossproduct.hpp"

    // The MIL-STD-2525 function glyphs the pulled catalogue does not hold,
    // rendered from the standard taxonomy by tools/gen_symbology_taxonomy.py.
    // Do not edit by hand.
#include "config_taxonomy.hpp"

    // The APP-6 mission-task graphics, the amplifier modifiers and the
    // echelon overlays, rendered by tools/gen_symbology_modifiers.py.  The
    // echelon overlay classes are selected at run time by the marker layer.
    // Do not edit by hand.
#include "config_modifiers.hpp"

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
        icon = "\z\aee\addons\optics\data\markers\AEE_FA_Friendly_Unit_Aviation_Fixed_Win.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_FA_Friendly_Unit_Aviation_Fixed_Win.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_air: AEE_MarkerBase {
        name = "AEE Friendly Rotary";
        icon = "\z\aee\addons\optics\data\markers\AEE_FA_APP_6_Army_Aviation.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_FA_APP_6_Army_Aviation.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_uav: AEE_MarkerBase {
        name = "AEE Friendly Uav";
        icon = "\z\aee\addons\optics\data\markers\AEE_FA_Friendly_Unit_Unmanned_Aerial_Ve.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_FA_Friendly_Unit_Unmanned_Aerial_Ve.paa";
        side = 1;
        scope = 2;
    };
    class AEE_b_naval: AEE_MarkerBase {
        name = "AEE Friendly Sea Surface";
        icon = "\z\aee\addons\optics\data\markers\AEE_FS_Friendly_Unit_Naval.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_FS_Friendly_Unit_Naval.paa";
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
        icon = "\z\aee\addons\optics\data\markers\AEE_FI_Installation.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_FI_Installation.paa";
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
        icon = "\z\aee\addons\optics\data\markers\AEE_HA_Hostile_Unit_Aviation_Fixed_Wing.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_HA_Hostile_Unit_Aviation_Fixed_Wing.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_air: AEE_MarkerBase {
        name = "AEE Hostile Rotary";
        icon = "\z\aee\addons\optics\data\markers\AEE_HA_Hostile_Unit_Aviation.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_HA_Hostile_Unit_Aviation.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_uav: AEE_MarkerBase {
        name = "AEE Hostile Uav";
        icon = "\z\aee\addons\optics\data\markers\AEE_HA_Hostile_Unit_Unmanned_Aerial_Veh.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_HA_Hostile_Unit_Unmanned_Aerial_Veh.paa";
        side = 0;
        scope = 2;
    };
    class AEE_o_naval: AEE_MarkerBase {
        name = "AEE Hostile Sea Surface";
        icon = "\z\aee\addons\optics\data\markers\AEE_HS_Hostile_Unit_Naval.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_HS_Hostile_Unit_Naval.paa";
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
        icon = "\z\aee\addons\optics\data\markers\AEE_HI_Installation.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_HI_Installation.paa";
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
        icon = "\z\aee\addons\optics\data\markers\AEE_NA_Neutral_Unit_Aviation_Fixed_Wing.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_NA_Neutral_Unit_Aviation_Fixed_Wing.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_air: AEE_MarkerBase {
        name = "AEE Neutral Rotary";
        icon = "\z\aee\addons\optics\data\markers\AEE_NA_Neutral_Unit_Aviation.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_NA_Neutral_Unit_Aviation.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_uav: AEE_MarkerBase {
        name = "AEE Neutral Uav";
        icon = "\z\aee\addons\optics\data\markers\AEE_NA_Neutral_Unit_Unmanned_Aerial_Veh.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_NA_Neutral_Unit_Unmanned_Aerial_Veh.paa";
        side = 2;
        scope = 2;
    };
    class AEE_n_naval: AEE_MarkerBase {
        name = "AEE Neutral Sea Surface";
        icon = "\z\aee\addons\optics\data\markers\AEE_NS_Neutral_Unit_Naval.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_NS_Neutral_Unit_Naval.paa";
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
        icon = "\z\aee\addons\optics\data\markers\AEE_NI_Installation.paa";
        texture = "\z\aee\addons\optics\data\markers\AEE_NI_Installation.paa";
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

