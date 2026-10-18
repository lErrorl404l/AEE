#!/usr/bin/env python3
"""Locks the SQF max/min precedence the engine uses.

Source: BIKI "Order of Precedence"
(community.bistudio.com/wiki/Order_of_Precedence, revision 376136, of
2025-09-02), mirrored at a3ref.github.io/topics/Order_of_Precedence.html.
Precedence 6 holds number addition and subtraction, array and string
addition, and the min and max commands.  Associativity inside one
precedence level runs left to right.

The harness parsed max/min as right-associative postfix commands, so
`a max b min c` evaluated as `a max (b min c)`.  The engine evaluates
`(a max b) min c`.  The clamp idiom `_x max 0 min 1` is the common case:
the old grouping returned `_x max 0` and never applied the upper bound, so
a kernel value that runs out of range in the engine passed the suite here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import unittest

from sqf_lite import MaxMin, SqfParser, SqfRuntime, tokenize


def _eval(src: str):
    return SqfRuntime({}).run(SqfParser(tokenize(src)).parse_program())


def _expr(src: str):
    return SqfParser(tokenize(src)).parse_program()[0].expr


class TestMaxMinPrecedence(unittest.TestCase):
    def test_chain_groups_left(self):
        node = _expr("_x max 2 min 8")
        self.assertIsInstance(node, MaxMin)
        self.assertEqual(node.op, "min")
        self.assertIsInstance(node.left, MaxMin)
        self.assertEqual(node.left.op, "max")

    def test_reverse_chain_groups_left(self):
        node = _expr("_x min 8 max 2")
        self.assertEqual(node.op, "max")
        self.assertEqual(node.left.op, "min")

    def test_upper_bound_applies(self):
        # (10 max 0) min 1 = 1.  The old grouping gave 10 max (0 min 1) = 10.
        self.assertEqual(_eval("10 max 0 min 1"), 1.0)

    def test_lower_bound_applies(self):
        # (10 max 20) min 30 = 20.
        self.assertEqual(_eval("10 max 20 min 30"), 20.0)

    def test_reverse_clamp(self):
        # (1 min 5) max 3 = 3.  The old grouping gave 1 min (5 max 3) = 1.
        self.assertEqual(_eval("1 min 5 max 3"), 3.0)

    def test_negative_operand_clamps(self):
        self.assertEqual(_eval("-5 max 0 min 1"), 0.0)

    def test_maxmin_shares_the_additive_level(self):
        # Precedence 6, left to right: (5 - 1) max 3 = 4.  The old postfix
        # form bound max inside the right operand: 5 - (1 max 3) = 2.
        self.assertEqual(_eval("5 - 1 max 3"), 4.0)

    def test_multiplication_still_binds_tighter(self):
        # Precedence 7 above 6: 2 * 3 max 4 = (2 * 3) max 4 = 6.
        self.assertEqual(_eval("2 * 3 max 4"), 6.0)
        self.assertEqual(_eval("1 + 2 * 3"), 7.0)

    def test_unary_minus_binds_tighter(self):
        # Precedence 10 above 6: (-2) max (-1) = -1.  The old form gave
        # -(2 max -1) = -2.
        self.assertEqual(_eval("-2 max -1"), -1.0)

    def test_parenthesised_clamp_unchanged(self):
        self.assertEqual(_eval("(10 max 0) min 1"), 1.0)
        self.assertEqual(_eval("(10 max 0) min 20"), 10.0)


if __name__ == "__main__":
    unittest.main()
