# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for parser_types."""

import unittest
from compiler.util import ir_data
from compiler.util import parser_types


class PositionTest(unittest.TestCase):
    """Tests for SourcePosition-related functions in parser_types."""


class LocationTest(unittest.TestCase):
    """Tests for SourceLocation-related functions in parser_types."""

    def test_location_new(self):
        self.assertEqual(
            parser_types.SourceLocation(
                start=parser_types.SourcePosition(line=1, column=2),
                end=parser_types.SourcePosition(line=3, column=4),
                is_synthetic=False,
            ),
            parser_types.SourceLocation((1, 2), (3, 4)),
        )
        self.assertEqual(
            parser_types.SourceLocation(
                start=parser_types.SourcePosition(line=1, column=2),
                end=parser_types.SourcePosition(line=3, column=4),
                is_synthetic=False,
            ),
            parser_types.SourceLocation(
                parser_types.SourcePosition(line=1, column=2),
                parser_types.SourcePosition(line=3, column=4),
            ),
        )

    def test_make_synthetic_location(self):
        self.assertEqual(
            parser_types.SourceLocation(
                start=parser_types.SourcePosition(line=1, column=2),
                end=parser_types.SourcePosition(line=3, column=4),
                is_synthetic=True,
            ),
            parser_types.SourceLocation((1, 2), (3, 4), is_synthetic=True),
        )
        self.assertEqual(
            parser_types.SourceLocation(
                start=parser_types.SourcePosition(line=1, column=2),
                end=parser_types.SourcePosition(line=3, column=4),
                is_synthetic=True,
            ),
            parser_types.SourceLocation(
                parser_types.SourcePosition(line=1, column=2),
                parser_types.SourcePosition(line=3, column=4),
                is_synthetic=True,
            ),
        )

    def test_location_str(self):
        self.assertEqual(
            "1:2-3:4",
            str(parser_types.SourceLocation((1, 2), (3, 4))),
        )

    def test_location_from_str(self):
        self.assertEqual(
            parser_types.SourceLocation((1, 2), (3, 4)),
            parser_types.SourceLocation.from_str("1:2-3:4"),
        )
        self.assertEqual(
            parser_types.SourceLocation((1, 2), (3, 4)),
            parser_types.SourceLocation.from_str("  1  :  2  -    3 :   4  "),
        )


class TokenTest(unittest.TestCase):
    """Tests for parser_types.Token."""

    def test_str(self):
        self.assertEqual(
            "FOO 'bar' 1:2-3:4",
            str(
                parser_types.Token(
                    "FOO", "bar", parser_types.SourceLocation((1, 2), (3, 4))
                )
            ),
        )


class ProductionTest(unittest.TestCase):
    """Tests for parser_types.Production."""

    def test_parse(self):
        self.assertEqual(
            parser_types.Production(lhs="A", rhs=("B", "C")),
            parser_types.Production.parse("A -> B C"),
        )
        self.assertEqual(
            parser_types.Production(lhs="A", rhs=("B",)),
            parser_types.Production.parse("A -> B"),
        )
        self.assertEqual(
            parser_types.Production(lhs="A", rhs=("B", "C")),
            parser_types.Production.parse("  A   ->   B   C  "),
        )
        self.assertEqual(
            parser_types.Production(lhs="A", rhs=tuple()),
            parser_types.Production.parse("A ->"),
        )
        self.assertEqual(
            parser_types.Production(lhs="A", rhs=tuple()),
            parser_types.Production.parse("A ->  "),
        )
        self.assertEqual(
            parser_types.Production(lhs="FOO", rhs=('"B"', "x*")),
            parser_types.Production.parse('FOO -> "B" x*'),
        )
        self.assertRaises(SyntaxError, parser_types.Production.parse, "F-> A B")
        self.assertRaises(SyntaxError, parser_types.Production.parse, "F B -> A B")
        self.assertRaises(SyntaxError, parser_types.Production.parse, "-> A B")

    def test_str(self):
        self.assertEqual(
            str(parser_types.Production(lhs="A", rhs=("B", "C"))), "A -> B C"
        )
        self.assertEqual(str(parser_types.Production(lhs="A", rhs=("B",))), "A -> B")
        self.assertEqual(str(parser_types.Production(lhs="A", rhs=tuple())), "A -> ")
        self.assertEqual(
            str(parser_types.Production(lhs="FOO", rhs=('"B"', "x*"))), 'FOO -> "B" x*'
        )


if __name__ == "__main__":
    unittest.main()
