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

    def test_position_str(self):
        self.assertEqual("1:2", str(parser_types.SourcePosition(line=1, column=2)))

    def test_position_bool(self):
        self.assertFalse(parser_types.SourcePosition())
        self.assertFalse(parser_types.SourcePosition(0, 0))
        self.assertTrue(parser_types.SourcePosition(1, 1))

    def test_position_from_str(self):
        self.assertEqual(
            parser_types.SourcePosition(1, 2),
            parser_types.SourcePosition.from_str("1:2"),
        )
        self.assertEqual(
            parser_types.SourcePosition(0, 0),
            parser_types.SourcePosition.from_str("0:0"),
        )
        self.assertRaises(ValueError, parser_types.SourcePosition.from_str, "0xa:9")
        self.assertRaises(ValueError, parser_types.SourcePosition.from_str, "9")
        if __debug__:
            self.assertRaises(ValueError, parser_types.SourcePosition.from_str, "0:-1")
            self.assertRaises(ValueError, parser_types.SourcePosition.from_str, "-1:0")

    def test_position_new(self):
        self.assertEqual(
            parser_types.SourcePosition(1, 2),
            parser_types.SourcePosition(line=1, column=2),
        )
        if __debug__:
            self.assertRaises(AssertionError, parser_types.SourcePosition, -1, 1)
            self.assertRaises(AssertionError, parser_types.SourcePosition, 1, -1)
            self.assertRaises(AssertionError, parser_types.SourcePosition, None, 1)
            self.assertRaises(AssertionError, parser_types.SourcePosition, 1, None)
            self.assertRaises(AssertionError, parser_types.SourcePosition, 1.1, 1)
            self.assertRaises(AssertionError, parser_types.SourcePosition, 1, 1.1)
            self.assertRaises(AssertionError, parser_types.SourcePosition, 0, 1)
            self.assertRaises(AssertionError, parser_types.SourcePosition, 1, 0)

    def test_position_attributes(self):
        self.assertEqual(1, parser_types.SourcePosition(1, 2).line)
        self.assertEqual(2, parser_types.SourcePosition(1, 2).column)

    def test_position_order(self):
        self.assertTrue(
            parser_types.SourcePosition(1, 2) < parser_types.SourcePosition(2, 2)
        )
        self.assertTrue(
            parser_types.SourcePosition(2, 1) < parser_types.SourcePosition(2, 2)
        )
        self.assertFalse(
            parser_types.SourcePosition(2, 1) < parser_types.SourcePosition(2, 1)
        )
        self.assertFalse(
            parser_types.SourcePosition(2, 2) < parser_types.SourcePosition(2, 1)
        )


class LocationTest(unittest.TestCase):
    """Tests for SourceLocation-related functions in parser_types."""

    def test_location_new(self):
        self.assertEqual(
            parser_types.SourceLocation(
                start=parser_types.SourcePosition(line=1, column=2),
                end=parser_types.SourcePosition(line=3, column=4),
                is_synthetic=False,
                is_disjoint_from_parent=False,
            ),
            parser_types.SourceLocation((1, 2), (3, 4)),
        )
        self.assertFalse(parser_types.SourceLocation(is_synthetic=False).is_synthetic)
        self.assertTrue(parser_types.SourceLocation(is_synthetic=True).is_synthetic)
        self.assertFalse(
            parser_types.SourceLocation(
                is_disjoint_from_parent=False
            ).is_disjoint_from_parent
        )
        self.assertTrue(
            parser_types.SourceLocation(
                is_disjoint_from_parent=True
            ).is_disjoint_from_parent
        )
        self.assertRaises(TypeError, parser_types.SourceLocation, None, (3, 4))
        self.assertRaises(TypeError, parser_types.SourceLocation, (1, 2), None)
        if __debug__:
            self.assertRaises(
                AssertionError, parser_types.SourceLocation, (3, 4), (1, 2)
            )
            self.assertRaises(
                AssertionError, parser_types.SourceLocation, (3, 4), (3, 2)
            )
            self.assertRaises(
                AssertionError,
                parser_types.SourceLocation,
                parser_types.SourcePosition(),
                (1, 2),
            )
            self.assertRaises(
                AssertionError,
                parser_types.SourceLocation,
                (1, 2),
                parser_types.SourcePosition(),
            )

    def test_location_str(self):
        self.assertEqual(
            "1:2-3:4",
            str(parser_types.SourceLocation((1, 2), (3, 4))),
        )
        self.assertEqual(
            "1:2-3:4^",
            str(
                parser_types.SourceLocation(
                    (1, 2), (3, 4), is_disjoint_from_parent=True
                )
            ),
        )
        self.assertEqual(
            "1:2-3:4*",
            str(parser_types.SourceLocation((1, 2), (3, 4), is_synthetic=True)),
        )
        self.assertEqual(
            "1:2-3:4^*",
            str(
                parser_types.SourceLocation(
                    (1, 2), (3, 4), is_synthetic=True, is_disjoint_from_parent=True
                )
            ),
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
        self.assertEqual(
            parser_types.SourceLocation((1, 2), (3, 4), is_disjoint_from_parent=True),
            parser_types.SourceLocation.from_str("1:2-3:4^"),
        )
        self.assertEqual(
            parser_types.SourceLocation((1, 2), (3, 4), is_synthetic=True),
            parser_types.SourceLocation.from_str("1:2-3:4*"),
        )
        self.assertEqual(
            parser_types.SourceLocation(
                (1, 2), (3, 4), is_disjoint_from_parent=True, is_synthetic=True
            ),
            parser_types.SourceLocation.from_str("1:2-3:4^*"),
        )
        self.assertRaises(ValueError, parser_types.SourceLocation.from_str, "1:2-3:")
        if __debug__:
            self.assertRaises(
                ValueError, parser_types.SourceLocation.from_str, "1:2-3:-1"
            )
        self.assertRaises(ValueError, parser_types.SourceLocation.from_str, "1:2-3:1%")

    def test_location_attributes(self):
        self.assertEqual(
            parser_types.SourceLocation((1, 2), (3, 4)).start,
            parser_types.SourcePosition(1, 2),
        )
        self.assertEqual(
            parser_types.SourceLocation((1, 2), (3, 4)).end,
            parser_types.SourcePosition(3, 4),
        )
        self.assertFalse(parser_types.SourceLocation((1, 2), (3, 4)).is_synthetic)
        self.assertFalse(
            parser_types.SourceLocation((1, 2), (3, 4)).is_disjoint_from_parent
        )
        self.assertTrue(
            parser_types.SourceLocation((1, 2), (3, 4), is_synthetic=True).is_synthetic
        )
        self.assertTrue(
            parser_types.SourceLocation(
                (1, 2), (3, 4), is_disjoint_from_parent=True
            ).is_disjoint_from_parent
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
