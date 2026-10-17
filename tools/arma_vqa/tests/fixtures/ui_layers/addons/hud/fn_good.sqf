// REAL-WORLD (ACE3 / CBA) layer idioms: none of these may produce a warning or an error
"tag_hud" cutRsc ["tag_hud", "PLAIN", 1, false];
"tag_hud" cutText ["", "PLAIN"];
("tag_rsc" call BIS_fnc_rscLayer) cutRsc ["tag_hud", "PLAIN", -1, false];
private _layer = ["tag_zero"] call BIS_fnc_rscLayer;
_layer cutRsc ["tag_zero", "PLAIN", 0, false];
_layer cutFadeOut 2;
135471 cutRsc ["tag_hud", "plain down"];
135471 cutText ["", "PLAIN"];
// markup is fine when the structured-text flag is set (ACE hunterkiller)
"tag_text" cutText [format ["<br/><t color='#ff0000' size='1.25'>[%1]</t>", _name], "PLAIN", -1, false, true];
"tag_text" cutText ["", "PLAIN"];
// curtain that is lifted again (ACE huntir / zeus)
"tag_black" cutText ["", "BLACK", 0, false];
"tag_black" cutText ["", "PLAIN"];
("tag_cur" call bis_fnc_rscLayer) cutText ["", "black out", 0.25, false];
("tag_cur" call bis_fnc_rscLayer) cutText ["", "black in", 0.5, false];
titleText [" ", "BLACK IN", 4];
// the object variant
"tag_obj" cutObj ["tag_model", "PLAIN"];
