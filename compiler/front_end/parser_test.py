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
from compiler.front_end import lr1
from compiler.front_end import parser
from compiler.front_end import tokenizer
from compiler.util import parser_types


# TODO(bolms): This is repeated in lr1_test.py; separate into test utils?
def _parse_productions(*productions):
    """Parses text into a grammar by calling Production.parse on each line."""
    return [parser_types.Production.parse(p) for p in productions]


_EXAMPLE_DIVIDER = "\n" + "=" * 80 + "\n"
_MESSAGE_ERROR_DIVIDER = "\n" + "-" * 80 + "\n"
_ERROR_DIVIDER = "\n---\n"


class ParserGeneratorTest(unittest.TestCase):
    """Tests parser.parse_error_examples and generate_parser."""

    def test_parse_good_error_examples(self):
        errors = parser.parse_error_examples(
            _EXAMPLE_DIVIDER  # ======...
            + "structure names must be Camel"  # Message.
            + _MESSAGE_ERROR_DIVIDER  # ------...
            + "struct $ERR FOO"  # First example.
            + _ERROR_DIVIDER  # ---
            + "struct $ERR foo"  # Second example.
            + _EXAMPLE_DIVIDER  # ======...
            + '   \n   struct must be followed by ":"   \n\n'  # Second message.
            + _MESSAGE_ERROR_DIVIDER  # ------...
            + "struct Foo $ERR"
        )  # Example for second message.
        self.assertEqual(tokenizer.tokenize("struct      FOO", "")[0], errors[0][0])
        self.assertEqual("structure names must be Camel", errors[0][2])
        self.assertEqual(tokenizer.tokenize("struct      foo", "")[0], errors[1][0])
        self.assertEqual("structure names must be Camel", errors[1][2])
        self.assertEqual(tokenizer.tokenize("struct Foo     ", "")[0], errors[2][0])
        self.assertEqual('struct must be followed by ":"', errors[2][2])

    def test_parse_good_wildcard_example(self):
        errors = parser.parse_error_examples(
            _EXAMPLE_DIVIDER  # ======...
            + '   \n   struct must be followed by ":"   \n\n'  # Second message.
            + _MESSAGE_ERROR_DIVIDER  # ------...
            + "struct Foo $ERR $ANY"
        )
        tokens = tokenizer.tokenize("struct Foo          ", "")[0]
        # The $ANY token should come just before the end-of-line token in the parsed
        # result.
        tokens.insert(-1, lr1.ANY_TOKEN)
        self.assertEqual(tokens, errors[0][0])
        self.assertEqual('struct must be followed by ":"', errors[0][2])

    def test_parse_with_no_error_marker(self):
        self.assertRaises(
            parser.ParserGenerationError,
            parser.parse_error_examples,
            _EXAMPLE_DIVIDER + "msg" + _MESSAGE_ERROR_DIVIDER + "-- doc",
        )

    def test_that_no_error_example_fails(self):
        self.assertRaises(
            parser.ParserGenerationError,
            parser.parse_error_examples,
            _EXAMPLE_DIVIDER
            + "msg"
            + _EXAMPLE_DIVIDER
            + "msg"
            + _MESSAGE_ERROR_DIVIDER
            + "example",
        )

    def test_that_message_example_divider_must_be_on_its_own_line(self):
        self.assertRaises(
            parser.ParserGenerationError,
            parser.parse_error_examples,
            _EXAMPLE_DIVIDER + "msg" + "-" * 80 + "example",
        )
        self.assertRaises(
            parser.ParserGenerationError,
            parser.parse_error_examples,
            _EXAMPLE_DIVIDER + "msg\n" + "-" * 80 + "example",
        )
        self.assertRaises(
            parser.ParserGenerationError,
            parser.parse_error_examples,
            _EXAMPLE_DIVIDER + "msg" + "-" * 80 + "\nexample",
        )
        self.assertRaises(
            parser.ParserGenerationError,
            parser.parse_error_examples,
            _EXAMPLE_DIVIDER + "msg\n" + "-" * 80 + " \nexample",
        )

    def test_that_example_divider_must_be_on_its_own_line(self):
        self.assertRaises(
            parser.ParserGenerationError,
            parser.parse_error_examples,
            _EXAMPLE_DIVIDER
            + "msg"
            + _MESSAGE_ERROR_DIVIDER
            + "example"
            + "=" * 80
            + "msg"
            + _MESSAGE_ERROR_DIVIDER
            + "example",
        )
        self.assertRaises(
            parser.ParserGenerationError,
            parser.parse_error_examples,
            _EXAMPLE_DIVIDER
            + "msg"
            + _MESSAGE_ERROR_DIVIDER
            + "example\n"
            + "=" * 80
            + "msg"
            + _MESSAGE_ERROR_DIVIDER
            + "example",
        )
        self.assertRaises(
            parser.ParserGenerationError,
            parser.parse_error_examples,
            _EXAMPLE_DIVIDER
            + "msg"
            + _MESSAGE_ERROR_DIVIDER
            + "example"
            + "=" * 80
            + "\nmsg"
            + _MESSAGE_ERROR_DIVIDER
            + "example",
        )
        self.assertRaises(
            parser.ParserGenerationError,
            parser.parse_error_examples,
            _EXAMPLE_DIVIDER
            + "msg"
            + _MESSAGE_ERROR_DIVIDER
            + "example\n"
            + "=" * 80
            + " \nmsg"
            + _MESSAGE_ERROR_DIVIDER
            + "example",
        )

    def test_that_tokenization_failure_results_in_failure(self):
        self.assertRaises(
            parser.ParserGenerationError,
            parser.parse_error_examples,
            _EXAMPLE_DIVIDER + "message" + _MESSAGE_ERROR_DIVIDER + "|",
        )

    def test_generate_parser(self):
        self.assertTrue(parser.generate_parser("C", _parse_productions("C -> s"), []))
        self.assertTrue(
            parser.generate_parser("C", _parse_productions("C -> s", "C -> d"), [])
        )

    def test_generated_parser_error(self):
        test_parser = parser.generate_parser(
            "C",
            _parse_productions("C -> s", "C -> d"),
            [
                (
                    [
                        parser_types.Token("s", "s", None),
                        parser_types.Token("s", "s", None),
                    ],
                    parser_types.Token("s", "s", None),
                    "double s",
                    "ss",
                )
            ],
        )
        parse_result = test_parser.parse(
            [parser_types.Token("s", "s", None), parser_types.Token("s", "s", None)]
        )
        self.assertEqual(None, parse_result.parse_tree)
        self.assertEqual("double s", parse_result.error.code)

    def test_conflict_error(self):
        self.assertRaises(
            parser.ParserGenerationError,
            parser.generate_parser,
            "C",
            _parse_productions("C -> S", "C -> D", "S -> a", "D -> a"),
            [],
        )

    def test_bad_mark_error(self):
        self.assertRaises(
            parser.ParserGenerationError,
            parser.generate_parser,
            "C",
            _parse_productions("C -> s", "C -> d"),
            [
                (
                    [
                        parser_types.Token("s", "s", None),
                        parser_types.Token("s", "s", None),
                    ],
                    parser_types.Token("s", "s", None),
                    "double s",
                    "ss",
                ),
                (
                    [
                        parser_types.Token("s", "s", None),
                        parser_types.Token("s", "s", None),
                    ],
                    parser_types.Token("s", "s", None),
                    "double 's'",
                    "ss",
                ),
            ],
        )
        self.assertRaises(
            parser.ParserGenerationError,
            parser.generate_parser,
            "C",
            _parse_productions("C -> s", "C -> d"),
            [
                (
                    [parser_types.Token("s", "s", None)],
                    parser_types.Token("s", "s", None),
                    "single s",
                    "s",
                )
            ],
        )


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
