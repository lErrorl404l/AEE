#include "..\script_component.hpp"

/*
Missile seeker state machine (pure).

Advances the seeker state one step.  The states (issue #131):

    0  PRE_LAUNCH   on the rail, seeker slaved
    1  BOOST        motor burning, guidance still settling
    2  MIDCOURSE    tracking toward the target
    3  TERMINAL     inside the terminal range, final guidance
    4  IMPACT       range closed to the impact radius
    5  BALLISTIC    lock lost, round coasts unguided
    6  LOST         lock lost in the terminal phase (usually permanent)

Transitions:
  PRE_LAUNCH -> BOOST   the driver sets BOOST on launch; this kernel does not
                        launch, so a PRE_LAUNCH input returns PRE_LAUNCH.
  BOOST -> MIDCOURSE    boost elapsed reaches the boost time.
  MIDCOURSE -> TERMINAL range closes to the terminal range.
  MIDCOURSE -> BALLISTIC lock lost before the terminal phase (the round still
                        flies, so it coasts).
  TERMINAL -> IMPACT    range closes to the impact radius.
  TERMINAL -> LOST      lock lost in the terminal phase.
  IMPACT/BALLISTIC/LOST are absorbing.

The lock-loss rule reflects the issue's note that "lost lock usually
permanent": a terminal lock loss is LOST, a midcourse lock loss is BALLISTIC
(the round coasts).  The impact and terminal ranges are caller parameters
(engine-scale tuning), not sourced constants.

Arguments:
  0: _state          (NUMBER) current state 0..6
  1: _rangeM         (NUMBER) slant range to the target, m
  2: _tracked        (BOOL)   seeker is tracking this tick
  3: _boostElapsedS  (NUMBER) time since launch, s
  4: _boostTimeS     (NUMBER) boost duration, s
  5: _terminalRangeM (NUMBER) range at which TERMINAL begins, m
  6: _impactRangeM   (NUMBER) range at which IMPACT occurs, m

Return Value: NUMBER - the next state, 0..6.
Public: No
*/

params [
    ["_state", 0, [0]],
    ["_rangeM", 0, [0]],
    ["_tracked", false, [false]],
    ["_boostElapsedS", 0, [0]],
    ["_boostTimeS", 0, [0]],
    ["_terminalRangeM", 0, [0]],
    ["_impactRangeM", 0, [0]]
];

// Absorbing states.
if (_state >= 4) exitWith { _state };

// On the rail until the driver launches.
if (_state == 0) exitWith { 0 };

// Impact check first: it outranks the phase transitions.
if (_impactRangeM > 0 && _rangeM <= _impactRangeM) exitWith { 4 };

if (_state == 1) exitWith {
    [1, 2] select (_boostElapsedS >= _boostTimeS)
};

if (_state == 2) exitWith {
    if (!_tracked) exitWith { 5 };
    [2, 3] select ((_terminalRangeM > 0) && (_rangeM <= _terminalRangeM))
};

// _state == 3 (TERMINAL)
if (!_tracked) exitWith { 6 };

3
