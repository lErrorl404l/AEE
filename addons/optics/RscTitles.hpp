// RscText needs a FULL base definition, not a forward declaration.  An
// empty parent class gives the control no type, so it never renders (the
// focus HUD was invisible for exactly this reason).  Definition mirrors
// FPANO ECOTI's working HUD (workshop 3759527903) and the vanilla default.
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

class RscTitles {
    class GVAR(nvgTitle) {
        idd = 10778;
        movingEnable = 0;
        enableSimulation = 1;
        enableDisplay = 1;
        onLoad = QUOTE(with uiNamespace do {GVAR(titleDisplay) = _this select 0};);
        duration = 999999;
        fadein = 0;
        fadeout = 0;
        class controls {
            // ─── Focus readout (ECOTI HUD style) ──────────────────────────
            // Position: bottom of NVG tube, like ECOTI's AltText/TimeText.
            // Real NVGs have no readout — the operator reads ring markings —
            // but a game needs to show the value the physics is using.
            // The bar spans 0-100 m (log display, dominated by the 0-25 m
            // patrol band) with a tick at the current focus.
            //
            // NVG tube geometry: circle inscribed in safeZoneH, centred on
            // screen.  On 16:9, safeZoneW > safeZoneH so the tube is
            // centred horizontally with black bars on the sides.
            // Tube vertical range: safeZoneY to safeZoneY + safeZoneH.
            // Tube horizontal range: safeZoneX + (safeZoneW - safeZoneH)/2
            //                     to safeZoneX + (safeZoneW + safeZoneH)/2.
            class NVGFocusText: RscText {
                idc = 1002;
                text = "FOCUS 15m";
                style = 2;   // centre-aligned
                shadow = 1;
                font = "PuristaMedium";
                sizeEx = "0.014 * safezoneH";
                // WHITE, not green: the engine tints the whole NVG view
                // green (phosphor screen), so a green readout is invisible
                // against it.  White stands out on the dark tube face.
                colorText[] = {1, 1, 1, 1};
                // ECOTI formula: x = "(fraction) * safezoneW + safezoneX"
                // Bottom of tube, centred horizontally.
                // y=0.88 places text in lower portion of tube (tube bottom ~1.0).
                x = "0.5 * safezoneW + safezoneX - (0.17 * safezoneH)";
                y = "0.88 * safezoneH + safezoneY";
                w = "0.34 * safezoneH";
                h = "0.020 * safezoneH";
            };
            class NVGFocusBar: RscText {
                idc = 1003;
                text = "|----o----------------------|";
                style = 2;   // centre-aligned
                shadow = 1;
                font = "PuristaMedium";
                sizeEx = "0.012 * safezoneH";
                colorText[] = {1, 1, 1, 0.8};
                x = "0.5 * safezoneW + safezoneX - (0.17 * safezoneH)";
                y = "0.90 * safezoneH + safezoneY";
                w = "0.34 * safezoneH";
                h = "0.018 * safezoneH";
            };

            // ─── PVS-31 low-battery red LED ───────────────────────────────
            // Real PVS-31: red LED in each monocular FOV when ≤10 min
            // battery remains (L3Harris PVS-31A datasheet).
            // Position: upper-right of tube, like ECOTI's compass area.
            // The LED is at the edge of the tube face, visible without
            // breaking position.
            class NVGBatteryWarning: RscText {
                idc = 1004;
                text = "●";
                style = 2;   // centre-aligned
                shadow = 0;
                font = "PuristaMedium";
                sizeEx = "0.018 * safezoneH";
                colorText[] = {1, 0, 0, 1};
                // Upper-right of tube: y=0.15 (near top), x shifted right.
                x = "0.5 * safezoneW + safezoneX + (0.06 * safezoneH)";
                y = "0.15 * safezoneH + safezoneY";
                w = "0.04 * safezoneH";
                h = "0.025 * safezoneH";
            };

            // ─── GEN3/PVS-14 low-battery blinking indicator ───────────────
            // Real PVS-14: blinking indicator in eyepiece when ≤30 min
            // battery remains (TM 11-5855-306-10).
            // Position: bottom of tube, like ECOTI's label area.
            // "Just outside the intensified FOV" per the manual.
            class NVGBatteryBlink: RscText {
                idc = 1005;
                text = "BATT";
                style = 2;   // centre-aligned
                shadow = 1;
                font = "PuristaMedium";
                sizeEx = "0.012 * safezoneH";
                colorText[] = {1, 0.3, 0, 1};
                // Bottom of tube: y=0.82 (near bottom, outside intensified area).
                x = "0.5 * safezoneW + safezoneX - (0.04 * safezoneH)";
                y = "0.82 * safezoneH + safezoneY";
                w = "0.08 * safezoneH";
                h = "0.018 * safezoneH";
            };
        };
    };
};
