/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * The shared control base classes (ADR-032, "the lib boundary").
 *
 * RscText and RscPicture are the engine control bases the display controls
 * inherit across modules: the nightvision tube HUD and the cartography map
 * tooltip both build on RscText.  RscTitles splits by display owner (hud,
 * vision, cartography), so one lib-owned home keeps each base declared once.
 *
 * NOT included by main/config.cpp yet: both classes are still declared in
 * addons/nightvision/RscTitles.hpp, and including this now would declare the
 * same class in two PBOs (ADR-032 ceiling 2).  Wire the include at step 1 and
 * remove the nightvision copies at step 9.  RscMapControl stays with
 * cartography, which carries the map colours.
 */
class RscText {
    type = 0;
    idc = -1;
    style = 0;
    shadow = 1;
    font = "PuristaMedium";
    sizeEx = "0.02 * safezoneH";
    colorText[] = {1, 1, 1, 1};
    colorBackground[] = {0, 0, 0, 0};
};

// style 48 is ST_PICTURE.  Both bases need a full body: an empty parent class
// gives the control no type, so it never renders.
class RscPicture {
    type = 0;
    idc = -1;
    style = 48;
    colorBackground[] = {0, 0, 0, 0};
    colorText[] = {1, 1, 1, 1};
    texture = "";
};
