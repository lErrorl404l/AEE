// The ECOTI environment HUD (aee_optics).
//
// A text HUD over the night-vision view: heading tape, grid, altitude,
// time, and the aee environment state.  The control layout follows the
// FPANO ECOTI HUD (workshop 3759527903 addons/FPANO_ECOTI/ui_hud.hpp).
// The source ships raster icons and an audio cue; neither can be added here
// without a binary asset, so this HUD is text only.
//
// The control base is local to this display, so no class name clashes
// with an engine RscText.  The fusionFrame / fusionOutline displays in
// addons/thermal/RscTitles.hpp use the same local-base pattern.
class RscTitles {

    class GVAR(hud) {
        idd = 10781;
        movingEnable = 0;
        enableSimulation = 0;
        enableDisplay = 1;
        onLoad = QUOTE(with uiNamespace do {GVAR(hudDisplay) = _this select 0};);
        onUnload = QUOTE(with uiNamespace do {GVAR(hudDisplay) = displayNull};);
        duration = 999999;
        fadein = 0;
        fadeout = 0;

        class controls {
            // Local base for every text line; the source RscText block.
            class AEETextHud {
                type = 0;
                idc = -1;
                style = 0;
                shadow = 1;
                font = "PuristaMedium";
                sizeEx = "0.016 * safezoneH";
                text = "";
                colorText[] = {1, 1, 1, 1};
                colorBackground[] = {0, 0, 0, 0};
                colorShadow[] = {0, 0, 0, 0.85};
                x = 0;
                y = 0;
                w = 0;
                h = 0.025;
            };

            class AEECardinal: AEETextHud {
                idc = 9010;
                text = "N";
                style = 0x02;
                sizeEx = "0.018 * safezoneH";
                x = "0.46 * safezoneW + safezoneX";
                y = "0.105 * safezoneH + safezoneY";
                w = "0.08 * safezoneW";
                h = "0.025 * safezoneH";
            };

            class AEEDegrees: AEETextHud {
                idc = 9003;
                text = "000";
                style = 0x02;
                sizeEx = "0.014 * safezoneH";
                x = "0.46 * safezoneW + safezoneX";
                y = "0.130 * safezoneH + safezoneY";
                w = "0.08 * safezoneW";
                h = "0.025 * safezoneH";
            };

            class AEEGrid: AEETextHud {
                idc = 9004;
                text = "0000 - 0000";
                style = 0x02;
                sizeEx = "0.018 * safezoneH";
                x = "0.40 * safezoneW + safezoneX";
                y = "0.165 * safezoneH + safezoneY";
                w = "0.20 * safezoneW";
                h = "0.035 * safezoneH";
            };

            class AEEAltitude: AEETextHud {
                idc = 9005;
                text = "0m";
                style = 0x00;
                x = "0.36 * safezoneW + safezoneX";
                y = "0.78 * safezoneH + safezoneY";
                w = "0.08 * safezoneW";
                h = "0.03 * safezoneH";
            };

            class AEETime: AEETextHud {
                idc = 9006;
                text = "00:00";
                style = 0x01;
                x = "0.56 * safezoneW + safezoneX";
                y = "0.78 * safezoneH + safezoneY";
                w = "0.08 * safezoneW";
                h = "0.03 * safezoneH";
            };

            class AEELabelTop: AEETextHud {
                idc = 9011;
                text = "AEE ENV";
                style = 0x02;
                sizeEx = "0.014 * safezoneH";
                x = "0.465 * safezoneW + safezoneX";
                y = "0.755 * safezoneH + safezoneY";
                w = "0.09 * safezoneW";
                h = "0.022 * safezoneH";
            };

            class AEELabelBottom: AEETextHud {
                idc = 9007;
                text = "HUD";
                style = 0x02;
                sizeEx = "0.014 * safezoneH";
                x = "0.465 * safezoneW + safezoneX";
                y = "0.775 * safezoneH + safezoneY";
                w = "0.07 * safezoneW";
                h = "0.022 * safezoneH";
            };

            class AEETemperature: AEETextHud {
                idc = 9012;
                text = "00 C";
                style = 0x02;
                sizeEx = "0.014 * safezoneH";
                x = "0.465 * safezoneW + safezoneX";
                y = "0.815 * safezoneH + safezoneY";
                w = "0.07 * safezoneW";
                h = "0.022 * safezoneH";
            };

            class AEEHumidity: AEETextHud {
                idc = 9013;
                text = "RH 00";
                style = 0x02;
                sizeEx = "0.014 * safezoneH";
                x = "0.465 * safezoneW + safezoneX";
                y = "0.835 * safezoneH + safezoneY";
                w = "0.07 * safezoneW";
                h = "0.022 * safezoneH";
            };

            class AEEWind: AEETextHud {
                idc = 9014;
                text = "WIND 0";
                style = 0x02;
                sizeEx = "0.014 * safezoneH";
                x = "0.465 * safezoneW + safezoneX";
                y = "0.855 * safezoneH + safezoneY";
                w = "0.09 * safezoneW";
                h = "0.022 * safezoneH";
            };
        };
    };
};
