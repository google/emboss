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
    """Tests for Position-related functions in parser_types."""

    def test_format_position(self):
        self.assertEqual(
            "1:2", parser_types.format_position(ir_data.Position(line=1, column=2))
        )


class LocationTest(unittest.TestCase):
    """Tests for Location-related functions in parser_types."""

    def test_make_location(self):
        self.assertEqual(
            ir_data.Location(
                start=ir_data.Position(line=1, column=2),
                end=ir_data.Position(line=3, column=4),
                is_synthetic=False,
            ),
            parser_types.make_location((1, 2), (3, 4)),
        )
        self.assertEqual(
            ir_data.Location(
                start=ir_data.Position(line=1, column=2),
                end=ir_data.Position(line=3, column=4),
                is_synthetic=False,
            ),
            parser_types.make_location(
                ir_data.Position(line=1, column=2), ir_data.Position(line=3, column=4)
            ),
        )

    def test_make_synthetic_location(self):
        self.assertEqual(
            ir_data.Location(
                start=ir_data.Position(line=1, column=2),
                end=ir_data.Position(line=3, column=4),
                is_synthetic=True,
            ),
            parser_types.make_location((1, 2), (3, 4), True),
        )
        self.assertEqual(
            ir_data.Location(
                start=ir_data.Position(line=1, column=2),
                end=ir_data.Position(line=3, column=4),
                is_synthetic=True,
            ),
            parser_types.make_location(
                ir_data.Position(line=1, column=2),
                ir_data.Position(line=3, column=4),
                True,
            ),
        )

    def test_make_location_type_checks(self):
        self.assertRaises(ValueError, parser_types.make_location, [1, 2], (1, 2))
        self.assertRaises(ValueError, parser_types.make_location, (1, 2), [1, 2])

    def test_make_location_logic_checks(self):
        self.assertRaises(ValueError, parser_types.make_location, (3, 4), (1, 2))
        self.assertRaises(ValueError, parser_types.make_location, (1, 3), (1, 2))
        self.assertTrue(parser_types.make_location((1, 2), (1, 2)))

    def test_format_location(self):
        self.assertEqual(
            "1:2-3:4",
            parser_types.format_location(parser_types.make_location((1, 2), (3, 4))),
        )

    def test_parse_location(self):
        self.assertEqual(
            parser_types.make_location((1, 2), (3, 4)),
            parser_types.parse_location("1:2-3:4"),
        )
        self.assertEqual(
            parser_types.make_location((1, 2), (3, 4)),
            parser_types.parse_location("  1  :  2  -    3 :   4  "),
        )


class TokenTest(unittest.TestCase):
    """Tests for parser_types.Token."""

    def test_str(self):
        self.assertEqual(
            "FOO 'bar' 1:2-3:4",
            str(
                parser_types.Token(
                    "FOO", "bar", parser_types.make_location((1, 2), (3, 4))
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
