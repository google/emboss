# Copyright 2026 Google LLC
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

"""Tests for expression_printer."""

import unittest

from compiler.util import expression_parser
from compiler.util import expression_printer
from compiler.util import ir_data


def _render(text):
    return expression_printer.render(expression_parser.parse(text))


class RenderTest(unittest.TestCase):

    def test_renders_constants(self):
        self.assertEqual("12", _render("12"))
        self.assertEqual("true", _render("true"))
        self.assertEqual("false", _render("false"))

    def test_renders_references(self):
        self.assertEqual("x", _render("x"))
        self.assertEqual("a.b.c", _render("a.b.c"))
        self.assertEqual("Enum.VALUE", _render("Enum.VALUE"))

    def test_renders_infix_operators(self):
        self.assertEqual("1 + 2", _render("1+2"))
        self.assertEqual("1 - 2", _render("1-2"))
        self.assertEqual("1 * 2", _render("1*2"))
        self.assertEqual("a == b", _render("a==b"))
        self.assertEqual("a != b", _render("a!=b"))
        self.assertEqual("a < b", _render("a<b"))
        self.assertEqual("a <= b", _render("a<=b"))
        self.assertEqual("a > b", _render("a>b"))
        self.assertEqual("a >= b", _render("a>=b"))
        self.assertEqual("a && b", _render("a&&b"))
        self.assertEqual("a || b", _render("a||b"))

    def test_renders_builtin_functions(self):
        self.assertEqual("$max(1, 2, 3)", _render("$max(1, 2, 3)"))
        self.assertEqual("$present(a.b)", _render("$present(a.b)"))
        self.assertEqual("$upper_bound(x)", _render("$upper_bound(x)"))
        self.assertEqual("$lower_bound(x)", _render("$lower_bound(x)"))

    def test_renders_choice(self):
        self.assertEqual("a ? b : c", _render("a ? b : c"))

    def test_renders_negation(self):
        self.assertEqual("-x", _render("-x"))
        self.assertEqual("-(a + b)", _render("-(a+b)"))

    def test_omits_unnecessary_parentheses(self):
        self.assertEqual("1 + 2 * 3", _render("1 + (2 * 3)"))
        self.assertEqual("1 + 2 - 3", _render("(1 + 2) - 3"))

    def test_keeps_necessary_parentheses(self):
        self.assertEqual("(1 + 2) * 3", _render("(1 + 2) * 3"))
        self.assertEqual("1 - (2 - 3)", _render("1 - (2 - 3)"))
        self.assertEqual("1 - (2 + 3)", _render("1 - (2 + 3)"))
        self.assertEqual("a || (b && c)", _render("a || (b && c)"))
        self.assertEqual("(a || b) && c", _render("(a || b) && c"))
        self.assertEqual("(a && b) || c", _render("(a && b) || c"))
        self.assertEqual("a && b && c", _render("a && b && c"))
        self.assertEqual("a ? b : (c ? d : e)", _render("a ? b : (c ? d : e)"))
        self.assertEqual("(a == b) == c", _render("(a == b) == c"))
        self.assertEqual("a + (b ? c : d)", _render("a + (b ? c : d)"))

    def test_round_trips(self):
        for text in (
            "1",
            "x",
            "a.b.c",
            "1 + 2 * 3 - 4",
            "(1 + 2) * (3 - 4)",
            "(a && b) || (c && d)",
            "a || (b && c)",
            "$max(1, x + 2, $upper_bound(y))",
            "a ? b + 1 : c * 2",
            "-x + 3",
            "-(x + 3)",
            "1 - (2 - 3)",
            "$present(a.b) && x == Enum.VALUE",
        ):
            with self.subTest(text=text):
                once = _render(text)
                twice = expression_printer.render(expression_parser.parse(once))
                self.assertEqual(once, twice)

    def test_rejects_empty_expression(self):
        with self.assertRaises(ValueError):
            expression_printer.render(ir_data.Expression())


if __name__ == "__main__":
    unittest.main()
