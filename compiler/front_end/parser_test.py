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

"""Tests for parser."""

import unittest
from compiler.front_end import parser
from compiler.front_end import tokenizer


class ModuleParserTest(unittest.TestCase):
    """Tests for parser.parse_module().

    Correct parses should mostly be checked in conjunction with
    module_ir.build_ir, as the exact data structure returned by
    parser.parse_module() is determined by the grammar defined in module_ir.
    These tests only need to cover errors and sanity checking.
    """

    def test_error_reporting_by_example(self):
        parse_result = parser.parse_module(
            tokenizer.tokenize("struct LogFileStatus:\n" "  0 [+4]    UInt\n", "")[0]
        )
        self.assertEqual(None, parse_result.parse_tree)
        self.assertEqual(
            "A name is required for a struct field.", parse_result.error.code
        )
        self.assertEqual('"\\n"', parse_result.error.token.symbol)
        self.assertEqual(
            set(['"["', "SnakeWord", '"."', '":"', '"("']),
            parse_result.error.expected_tokens,
        )

    def test_error_reporting_without_example(self):
        parse_result = parser.parse_module(
            tokenizer.tokenize(
                "struct LogFileStatus:\n" "  0 [+4]    UInt    foo +\n", ""
            )[0]
        )
        self.assertEqual(None, parse_result.parse_tree)
        self.assertEqual(None, parse_result.error.code)
        self.assertEqual('"+"', parse_result.error.token.symbol)
        self.assertEqual(
            set(['"("', '"\\n"', '"["', "Documentation", "Comment"]),
            parse_result.error.expected_tokens,
        )

    def test_ok_parse(self):
        parse_result = parser.parse_module(
            tokenizer.tokenize(
                "struct LogFileStatus:\n" "  0 [+4]    UInt    foo\n", ""
            )[0]
        )
        self.assertTrue(parse_result.parse_tree)
        self.assertEqual(None, parse_result.error)


if __name__ == "__main__":
    unittest.main()
