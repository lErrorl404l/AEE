// The MGRS GPS device readout (aee_cartography).
//
// A dedicated display raised when the player carries an ItemGPS and the
// aee_cartography_mgrsEnabled setting is on.  The device green marks it as an
// instrument, not the environment HUD.
class RscTitles {
    // MGRS GPS device readout (task 9).  A dedicated display raised when the
    // player carries an ItemGPS and the aee_cartography_mgrsEnabled setting is on.
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
