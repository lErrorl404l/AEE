/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * The Eden and Zeus (curator) symbol reconciliation.
 *
 * Eden and Zeus draw a group marker for each side from CfgCurator >> DrawGroup.
 * The engine points every side at the neutral or unknown frame, so the
 * civilian side and the unknown-affiliation side carry the wrong symbol.  This
 * file re-declares the five side textures so Eden and Zeus carry the real NATO
 * symbol for each side: friend, hostile, neutral, civilian and unknown.
 *
 * The curator map control (RscDisplayCurator >> ControlsBackground >> Map)
 * inherits RscMapControl, so the map colours, the location symbols and the
 * object icons reach Eden and Zeus with no separate re-declare.
 *
 * Engine ceiling: the DrawGroup texture is per SIDE, not per unit function, so
 * a specific unit function glyph cannot be shown here.  The Eden object-tree
 * and unit icons are engine-internal, like the map object-icon routing.
 */
class CfgCurator {
    class DrawGroup {
        textureWest = "\A3\ui_f\data\map\markers\nato\b_unknown.paa";
        textureEast = "\A3\ui_f\data\map\markers\nato\o_unknown.paa";
        textureGuer = "\A3\ui_f\data\map\markers\nato\n_unknown.paa";
        textureCivilian = "\A3\ui_f\data\map\markers\nato\c_unknown.paa";
        textureUnknown = "\z\aee\addons\symbology\data\markers\AEE_u_unknown.paa";
        class 3D {
            textureWest = "\A3\ui_f\data\map\markers\nato\b_unknown.paa";
            textureEast = "\A3\ui_f\data\map\markers\nato\o_unknown.paa";
            textureGuer = "\A3\ui_f\data\map\markers\nato\n_unknown.paa";
            textureCivilian = "\A3\ui_f\data\map\markers\nato\c_unknown.paa";
            textureUnknown = "\z\aee\addons\symbology\data\markers\AEE_u_unknown.paa";
        };
        class 2D {
            textureWest = "\A3\ui_f\data\map\markers\nato\b_unknown.paa";
            textureEast = "\A3\ui_f\data\map\markers\nato\o_unknown.paa";
            textureGuer = "\A3\ui_f\data\map\markers\nato\n_unknown.paa";
            textureCivilian = "\A3\ui_f\data\map\markers\nato\c_unknown.paa";
            textureUnknown = "\z\aee\addons\symbology\data\markers\AEE_u_unknown.paa";
        };
    };
};
