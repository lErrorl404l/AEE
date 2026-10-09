// The player-perception debug overlay (aee_vision).
//
// One line of reconstructed view state, gated by the aee_vision_perceptionHud
// setting.  The idd band above 10800 is fresh; it never collides with the
// aee_optics GVAR(hud) at 10781, the aee_optics GVAR(gps) at 10783 or the
// thermal fusion display.
class RscTitles {

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
};
