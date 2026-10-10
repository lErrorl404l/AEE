#include "..\script_component.hpp"
/*
The sonar equation (issue #113).

Urick, "Principles of Underwater Sound", 3rd ed., McGraw-Hill 1983,
ISBN 0-07-066087-5.  Corroborated by the US Naval Academy ES310
sonar-propagation notes.

Passive:  SE = SL - TL - NL + DI
Active:   SE = SL - 2 TL + TS - NL + DI

  SL  source level, dB re 1 uPa at 1 m (passive: the target's radiated
      noise; active: the projector's transmit level)
  TL  one-way transmission loss, dB (from fnc_calculateTransmissionLoss)
  NL  ambient noise spectrum level, dB (from fnc_calculateAmbientNoise)
  DI  directivity index of the receiving array, dB
  TS  target strength, dB (active only)
  SE  signal excess, dB

Detection occurs when SE >= DT, the detection threshold (a separate
decision the caller makes).  The active form doubles the transmission loss
because the sound travels out to the target and back.

Input:  [mode, SL, TL, NL, DI, TS]
          mode - "passive" (default) or "active"
Output: signal excess in dB
*/

params [
    ["_mode", "passive", [""]],
    ["_SL", 0, [0]],
    ["_TL", 0, [0]],
    ["_NL", 0, [0]],
    ["_DI", 0, [0]],
    ["_TS", 0, [0]]
];

if (_mode == "active") exitWith {
    _SL - (2 * _TL) + _TS - _NL + _DI
};

_SL - _TL - _NL + _DI
