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
            // The AEE font is a load-time config font.  The operator
            // procedure in docs/wiki/research/arma-font-surface.md produces
            // the AEEFont glyph set.  Until it exists the engine falls back
            // to its default font, so the default state is unchanged.
            class AEETextHud {
                type = 0;
                idc = -1;
                style = 0;
                shadow = 1;
                font = "RobotoCondensed";
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

            // Retired in place.  The grid line moved to AEEMgrs (idc 9015)
            // so one control carries either the MGRS reference or the legacy
            // numeric grid; the idc stays assigned and the text stays empty.
            class AEEGrid: AEETextHud {
                idc = 9004;
                text = "";
                style = 0x02;
                sizeEx = "0.018 * safezoneH";
                x = "0.40 * safezoneW + safezoneX";
                y = "0.165 * safezoneH + safezoneY";
                w = "0.20 * safezoneW";
                h = "0.035 * safezoneH";
            };

            // MGRS grid readout (aee_optics_mgrsEnabled).  Sits on the retired
            // AEEGrid line so the HUD does not move when MGRS is switched off.
            class AEEMgrs: AEETextHud {
                idc = 9015;
                text = "";
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

    // The player-perception debug overlay: one line of reconstructed view
    // state, gated by the aee_optics_perceptionHud setting.  The idd band
    // above 10800 is fresh; it never collides with GVAR(hud) at 10781 or
    // the thermal fusion display.
    class GVAR(perceptionHud) {
        idd = 10801;
        movingEnable = 0;
        enableSimulation = 0;
        enableDisplay = 1;
        onLoad = QUOTE(with uiNamespace do {GVAR(perceptionHudDisplay) = _this select 0};);
        onUnload = QUOTE(with uiNamespace do {GVAR(perceptionHudDisplay) = displayNull};);
        duration = 999999;
        fadein = 0;
        fadeout = 0;

        class controls {
            // Local base for the perception text line, so no class name
            // clashes with an engine RscText.
            class AEEPerceptionText {
                type = 0;
                idc = 10811;
                style = 0;
                shadow = 1;
                font = "RobotoCondensed";
                sizeEx = "0.016 * safezoneH";
                text = "";
                colorText[] = {1, 1, 1, 1};
                colorBackground[] = {0, 0, 0, 0};
                colorShadow[] = {0, 0, 0, 0.85};
                x = "0.02 * safezoneW + safezoneX";
                y = "0.30 * safezoneH + safezoneY";
                w = "0.96 * safezoneW";
                h = "0.025 * safezoneH";
            };
        };
    };

    // MGRS GPS device readout (task 9).  A dedicated display raised when the
    // player carries an ItemGPS and the aee_optics_mgrsEnabled setting is on.
    // The engine GPS readout is fixed and cannot be repointed, so this is the
    // aee MGRS surface for the hand-held device.
    class GVAR(gps) {
        idd = 10783;
        movingEnable = 0;
        enableSimulation = 0;
        enableDisplay = 1;
        onLoad = QUOTE(with uiNamespace do {GVAR(gpsDisplay) = _this select 0};);
        onUnload = QUOTE(with uiNamespace do {GVAR(gpsDisplay) = displayNull};);
        duration = 999999;
        fadein = 0;
        fadeout = 0;

        class controls {
            // Local base for the GPS text lines.  The device green marks it as
            // an instrument, not the environment HUD.
            // The MGRS device readout uses the monospaced companion, so the
            // coordinate columns do not jitter as the digits change.
            class AEEGpsText {
                type = 0;
                idc = -1;
                style = 0;
                shadow = 1;
                font = "EtelkaMonospacePro";
                sizeEx = "0.016 * safezoneH";
                text = "";
                colorText[] = {0.55, 1, 0.55, 1};
                colorBackground[] = {0, 0, 0, 0.4};
                colorShadow[] = {0, 0, 0, 0.85};
                x = 0;
                y = 0;
                w = 0;
                h = 0.025;
            };

            class AEEGpsGrid: AEEGpsText {
                idc = 9020;
                text = "";
                sizeEx = "0.022 * safezoneH";
                x = "0.02 * safezoneW + safezoneX";
                y = "0.06 * safezoneH + safezoneY";
                w = "0.32 * safezoneW";
                h = "0.035 * safezoneH";
            };

            class AEEGpsPrecision: AEEGpsText {
                idc = 9021;
                text = "";
                x = "0.02 * safezoneW + safezoneX";
                y = "0.095 * safezoneH + safezoneY";
                w = "0.32 * safezoneW";
                h = "0.025 * safezoneH";
            };

            class AEEGpsFix: AEEGpsText {
                idc = 9022;
                text = "";
                x = "0.02 * safezoneW + safezoneX";
                y = "0.120 * safezoneH + safezoneY";
                w = "0.32 * safezoneW";
                h = "0.025 * safezoneH";
            };

            class AEEGpsEllipse: AEEGpsText {
                idc = 9023;
                text = "";
                x = "0.02 * safezoneW + safezoneX";
                y = "0.145 * safezoneH + safezoneY";
                w = "0.32 * safezoneW";
                h = "0.025 * safezoneH";
            };
        };
    };
};
