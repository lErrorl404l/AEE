// layer 1 is also used by addons/visuals/scripts/fn_thermal.sqf for a different resource (UI001)
1 cutRsc ["HudB", "PLAIN"];
// typo in the class name: nothing is shown (UI006)
"badmod_hud" cutRsc ["badmod_compas", "PLAIN", 1, false];
// markup printed literally (UI005), unknown effect type (UI003)
"badmod_msg" cutText ["<t size='1.4' color='#ff0000'>Low ammo</t>", "PLAIN"];
"badmod_msg" cutText ["", "FLASH"];
// white-out with no fade-in (UI014), black curtain that is never lifted (UI016)
"badmod_flash" cutText ["", "WHITE OUT"];
"badmod_fade" cutText ["", "BLACK OUT", 1, true];
// the layer name differs only in case, so the fade-out below hits a different layer (UI009)
"BadmodCompass" cutRsc ["badmod_compass", "PLAIN"];
"badmodcompass" cutFadeOut 2;
