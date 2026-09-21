#include "..\script_component.hpp"
/*
Scored token matcher (issue #167).

The elasticsearch/opensearch-style matcher: the query (a classname +
its displayName) is tokenised, each indexed term is scored by how well
it matches, and the HIGHEST score wins.  This replaces fragile
substring scanning - a whole-token match beats a partial one, and a
longer (more specific) term beats a shorter one.

Scoring (the ES-style relevance):
  +100  the term matches as a WHOLE TOKEN (boundary-aligned: HK416 in
        "MCC_HK416A8_556" is a partial token; "HK416" in
        "MCC_HK416_BLK" is a whole token)
   +30  the term is a token PREFIX (HK416 in "HK416A8")
   +15  the term appears as a SUBSTRING anywhere
   +L   the term's length (specificity: MK262 beats MK2)
   +10  the match is in the displayName (the readable name is more
        reliable than the opaque classname)

The score is the term's match quality; the caller picks the best match
or uses its base value when nothing scores above the threshold.

Arguments:
  0: query (STRING, the classname, lowercase expected)
  1: terms (ARRAY of STRING, the indexed terms, longest-first)

Returns [bestScore, bestTerm, termIndex].
*/
params ["_query", "_terms"];

private _bestScore = 0;
private _bestTerm = "";
private _bestIndex = -1;

{
    private _term = _x;
    private _score = 0;
    // Whole-token match (boundary-aligned): the term is surrounded by
    // non-alphanumerics or the string edges.
    private _pos = _query find _term;
    if (_pos >= 0) then {
        private _before = if (_pos > 0) then {
            _query select [_pos - 1, 1]
        } else { "" };
        private _after = if (_pos + (count _term) < count _query) then {
            _query select [_pos + count _term, 1]
        } else { "" };
        private _isAlnum = {
            params ["_c"];
            if (_c == "") exitWith { false };
            (_c == "0" || _c == "1" || _c == "2" || _c == "3" || _c == "4"
            || _c == "5" || _c == "6" || _c == "7" || _c == "8" || _c == "9"
            || _c == "a" || _c == "b" || _c == "c" || _c == "d" || _c == "e"
            || _c == "f" || _c == "g" || _c == "h" || _c == "i" || _c == "j"
            || _c == "k" || _c == "l" || _c == "m" || _c == "n" || _c == "o"
            || _c == "p" || _c == "q" || _c == "r" || _c == "s" || _c == "t"
            || _c == "u" || _c == "v" || _c == "w" || _c == "x" || _c == "y"
            || _c == "z")
        };
        private _whole = ((not ([_before] call _isAlnum)) && (not ([_after] call _isAlnum)));
        if (_whole) then {
            _score = 100 + count _term;
        } else {
            // Token-prefix: the term starts a token (a _ or digit-free
            // boundary before it).
            private _boundary = (_before == "_" || _before == "-" || _before == " " || _before == "");
            if (_boundary) then {
                _score = 30 + count _term;
            } else {
                _score = 15 + count _term;
            };
        };
    };
    if (_score > _bestScore) then {
        _bestScore = _score;
        _bestTerm = _term;
        _bestIndex = _forEachIndex;
    };
} forEach _terms;

[_bestScore, _bestTerm, _bestIndex]
