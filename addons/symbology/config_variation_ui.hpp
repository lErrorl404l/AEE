/* SPDX-License-Identifier: GPL-2.0-or-later */
// The AEE dynamic variation selector (aee_symbology).
//
// ONE display, opened by a CBA keybind, that lists the active family's options
// and their values as buttons.  The option list is NOT declared here: the
// controls are built at run time from fnc_variationOptions, so a new option
// value appears with no UI change.  This file declares the display, the title,
// the options group and the close button only.
class RscText;
class RscControlsGroup;
class RscButton;

class RscDisplayAEEVariation {
    idd = 10790;
    movingEnable = 0;
    enableSimulation = 1;
    enableDisplay = 1;
    onLoad = QUOTE(with uiNamespace do {GVAR(variationDisplay) = _this select 0}; _this call FUNC(variationDialogRefresh););
    onUnload = QUOTE(with uiNamespace do {GVAR(variationDisplay) = displayNull};);

    class controlsBackground {
        class AEEVariationBackground: RscText {
            idc = 1200;
            x = "0.30 * safezoneW + safezoneX";
            y = "0.24 * safezoneH + safezoneY";
            w = "0.40 * safezoneW";
            h = "0.52 * safezoneH";
            colorBackground[] = {0, 0, 0, 0.85};
            text = "";
        };
        class AEEVariationTitle: RscText {
            idc = 1201;
            x = "0.30 * safezoneW + safezoneX";
            y = "0.24 * safezoneH + safezoneY";
            w = "0.40 * safezoneW";
            h = "0.05 * safezoneH";
            style = 0x02;
            sizeEx = "0.03 * safezoneH";
            colorBackground[] = {0.1, 0.1, 0.1, 0.9};
            text = "";
        };
    };

    class controls {
        class AEEVariationOptions: RscControlsGroup {
            idc = 1202;
            x = "0.31 * safezoneW + safezoneX";
            y = "0.30 * safezoneH + safezoneY";
            w = "0.38 * safezoneW";
            h = "0.38 * safezoneH";
        };
        class AEEVariationClose: RscButton {
            idc = 1203;
            x = "0.56 * safezoneW + safezoneX";
            y = "0.71 * safezoneH + safezoneY";
            w = "0.13 * safezoneW";
            h = "0.04 * safezoneH";
            text = "Close";
            action = "closeDialog 0";
        };
    };
};
