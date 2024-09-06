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

"""Tests for tokenizer."""

import unittest
from compiler.front_end import tokenizer
from compiler.util import error
from compiler.util import parser_types


def _token_symbols(token_list):
    """Given a list of tokens, returns a list of their symbol names."""
    return [token.symbol for token in token_list]


class TokenizerTest(unittest.TestCase):
    """Tests for the tokenizer.tokenize function."""

    def test_bad_indent_tab_versus_space(self):
        # A bad indent is one that doesn't match a previous unmatched indent.
        tokens, errors = tokenizer.tokenize(" a\n\tb", "file")
        self.assertFalse(tokens)
        self.assertEqual(
            [
                [
                    error.error(
                        "file",
                        parser_types.make_location((2, 1), (2, 2)),
                        "Bad indentation",
                    )
                ]
            ],
            errors,
        )

    def test_bad_indent_tab_versus_eight_spaces(self):
        tokens, errors = tokenizer.tokenize("        a\n\tb", "file")
        self.assertFalse(tokens)
        self.assertEqual(
            [
                [
                    error.error(
                        "file",
                        parser_types.make_location((2, 1), (2, 2)),
                        "Bad indentation",
                    )
                ]
            ],
            errors,
        )

    def test_bad_indent_tab_versus_four_spaces(self):
        tokens, errors = tokenizer.tokenize("    a\n\tb", "file")
        self.assertFalse(tokens)
        self.assertEqual(
            [
                [
                    error.error(
                        "file",
                        parser_types.make_location((2, 1), (2, 2)),
                        "Bad indentation",
                    )
                ]
            ],
            errors,
        )

    def test_bad_indent_two_spaces_versus_one_space(self):
        tokens, errors = tokenizer.tokenize("  a\n b", "file")
        self.assertFalse(tokens)
        self.assertEqual(
            [
                [
                    error.error(
                        "file",
                        parser_types.make_location((2, 1), (2, 2)),
                        "Bad indentation",
                    )
                ]
            ],
            errors,
        )

    def test_bad_indent_matches_closed_indent(self):
        tokens, errors = tokenizer.tokenize(" a\nb\n  c\n d", "file")
        self.assertFalse(tokens)
        self.assertEqual(
            [
                [
                    error.error(
                        "file",
                        parser_types.make_location((4, 1), (4, 2)),
                        "Bad indentation",
                    )
                ]
            ],
            errors,
        )

    def test_bad_string_after_string_with_escaped_backslash_at_end(self):
        tokens, errors = tokenizer.tokenize(r'"\\""', "name")
        self.assertFalse(tokens)
        self.assertEqual(
            [
                [
                    error.error(
                        "name",
                        parser_types.make_location((1, 5), (1, 6)),
                        "Unrecognized token",
                    )
                ]
            ],
            errors,
        )


def _make_short_token_match_tests():
    """Makes tests for short, simple tokenization cases."""
    eol = '"\\n"'
    cases = {
        "Cam": ["CamelWord", eol],
        "Ca9": ["CamelWord", eol],
        "CanB": ["CamelWord", eol],
        "CanBee": ["CamelWord", eol],
        "CBa": ["CamelWord", eol],
        "cam": ["SnakeWord", eol],
        "ca9": ["SnakeWord", eol],
        "can_b": ["SnakeWord", eol],
        "can_bee": ["SnakeWord", eol],
        "c_ba": ["SnakeWord", eol],
        "cba_": ["SnakeWord", eol],
        "c_b_a_": ["SnakeWord", eol],
        "CAM": ["ShoutyWord", eol],
        "CA9": ["ShoutyWord", eol],
        "CAN_B": ["ShoutyWord", eol],
        "CAN_BEE": ["ShoutyWord", eol],
        "C_BA": ["ShoutyWord", eol],
        "C": ["BadWord", eol],
        "C1": ["BadWord", eol],
        "c": ["SnakeWord", eol],
        "$": ["BadWord", eol],
        "_": ["BadWord", eol],
        "_a": ["BadWord", eol],
        "_A": ["BadWord", eol],
        "Cb_A": ["BadWord", eol],
        "aCb": ["BadWord", eol],
        "a  b": ["SnakeWord", "SnakeWord", eol],
        "a\tb": ["SnakeWord", "SnakeWord", eol],
        "a \t b ": ["SnakeWord", "SnakeWord", eol],
        " \t ": [eol],
        "a #b": ["SnakeWord", "Comment", eol],
        "a#": ["SnakeWord", "Comment", eol],
        "# b": ["Comment", eol],
        "    # b": ["Comment", eol],
        "    #": ["Comment", eol],
        "": [],
        "\n": [eol],
        "\na": [eol, "SnakeWord", eol],
        "a--example": ["SnakeWord", "BadDocumentation", eol],
        "a ---- example": ["SnakeWord", "BadDocumentation", eol],
        "a --- example": ["SnakeWord", "BadDocumentation", eol],
        "a-- example": ["SnakeWord", "Documentation", eol],
        "a --    -- example": ["SnakeWord", "Documentation", eol],
        "a -- - example": ["SnakeWord", "Documentation", eol],
        "--": ["Documentation", eol],
        "-- ": ["Documentation", eol],
        "--  ": ["Documentation", eol],
        "$default": ['"$default"', eol],
        "$defaultx": ["BadWord", eol],
        "$def": ["BadWord", eol],
        "x$default": ["BadWord", eol],
        "9$default": ["BadWord", eol],
        "struct": ['"struct"', eol],
        "external": ['"external"', eol],
        "bits": ['"bits"', eol],
        "enum": ['"enum"', eol],
        "as": ['"as"', eol],
        "import": ['"import"', eol],
        "true": ["BooleanConstant", eol],
        "false": ["BooleanConstant", eol],
        "truex": ["SnakeWord", eol],
        "falsex": ["SnakeWord", eol],
        "structx": ["SnakeWord", eol],
        "bitsx": ["SnakeWord", eol],
        "enumx": ["SnakeWord", eol],
        "0b": ["BadNumber", eol],
        "0x": ["BadNumber", eol],
        "0b011101": ["Number", eol],
        "0b0": ["Number", eol],
        "0b0111_1111_0000": ["Number", eol],
        "0b00_000_00": ["BadNumber", eol],
        "0b0_0_0": ["BadNumber", eol],
        "0b0111012": ["BadNumber", eol],
        "0b011101x": ["BadWord", eol],
        "0b011101b": ["BadNumber", eol],
        "0B0": ["BadNumber", eol],
        "0X0": ["BadNumber", eol],
        "0b_": ["BadNumber", eol],
        "0x_": ["BadNumber", eol],
        "0b__": ["BadNumber", eol],
        "0x__": ["BadNumber", eol],
        "0b_0000": ["Number", eol],
        "0b0000_": ["BadNumber", eol],
        "0b00_____00": ["BadNumber", eol],
        "0x00_000_00": ["BadNumber", eol],
        "0x0_0_0": ["BadNumber", eol],
        "0b____0____": ["BadNumber", eol],
        "0b00000000000000000000": ["Number", eol],
        "0b_00000000": ["Number", eol],
        "0b0000_0000_0000": ["Number", eol],
        "0b000_0000_0000": ["Number", eol],
        "0b00_0000_0000": ["Number", eol],
        "0b0_0000_0000": ["Number", eol],
        "0b_0000_0000_0000": ["Number", eol],
        "0b_000_0000_0000": ["Number", eol],
        "0b_00_0000_0000": ["Number", eol],
        "0b_0_0000_0000": ["Number", eol],
        "0b00000000_00000000_00000000": ["Number", eol],
        "0b0000000_00000000_00000000": ["Number", eol],
        "0b000000_00000000_00000000": ["Number", eol],
        "0b00000_00000000_00000000": ["Number", eol],
        "0b0000_00000000_00000000": ["Number", eol],
        "0b000_00000000_00000000": ["Number", eol],
        "0b00_00000000_00000000": ["Number", eol],
        "0b0_00000000_00000000": ["Number", eol],
        "0b_00000000_00000000_00000000": ["Number", eol],
        "0b_0000000_00000000_00000000": ["Number", eol],
        "0b_000000_00000000_00000000": ["Number", eol],
        "0b_00000_00000000_00000000": ["Number", eol],
        "0b_0000_00000000_00000000": ["Number", eol],
        "0b_000_00000000_00000000": ["Number", eol],
        "0b_00_00000000_00000000": ["Number", eol],
        "0b_0_00000000_00000000": ["Number", eol],
        "0x0": ["Number", eol],
        "0x00000000000000000000": ["Number", eol],
        "0x_0000": ["Number", eol],
        "0x_00000000": ["Number", eol],
        "0x0000_0000_0000": ["Number", eol],
        "0x000_0000_0000": ["Number", eol],
        "0x00_0000_0000": ["Number", eol],
        "0x0_0000_0000": ["Number", eol],
        "0x_0000_0000_0000": ["Number", eol],
        "0x_000_0000_0000": ["Number", eol],
        "0x_00_0000_0000": ["Number", eol],
        "0x_0_0000_0000": ["Number", eol],
        "0x00000000_00000000_00000000": ["Number", eol],
        "0x0000000_00000000_00000000": ["Number", eol],
        "0x000000_00000000_00000000": ["Number", eol],
        "0x00000_00000000_00000000": ["Number", eol],
        "0x0000_00000000_00000000": ["Number", eol],
        "0x000_00000000_00000000": ["Number", eol],
        "0x00_00000000_00000000": ["Number", eol],
        "0x0_00000000_00000000": ["Number", eol],
        "0x_00000000_00000000_00000000": ["Number", eol],
        "0x_0000000_00000000_00000000": ["Number", eol],
        "0x_000000_00000000_00000000": ["Number", eol],
        "0x_00000_00000000_00000000": ["Number", eol],
        "0x_0000_00000000_00000000": ["Number", eol],
        "0x_000_00000000_00000000": ["Number", eol],
        "0x_00_00000000_00000000": ["Number", eol],
        "0x_0_00000000_00000000": ["Number", eol],
        "0x__00000000_00000000": ["BadNumber", eol],
        "0x00000000_00000000_0000": ["BadNumber", eol],
        "0x00000000_0000_0000": ["BadNumber", eol],
        "0x_00000000000000000000": ["BadNumber", eol],
        "0b_00000000000000000000": ["BadNumber", eol],
        "0b00000000_00000000_0000": ["BadNumber", eol],
        "0b00000000_0000_0000": ["BadNumber", eol],
        "0x0000_": ["BadNumber", eol],
        "0x00_____00": ["BadNumber", eol],
        "0x____0____": ["BadNumber", eol],
        "EmbossReserved": ["BadWord", eol],
        "EmbossReservedA": ["BadWord", eol],
        "EmbossReserved_": ["BadWord", eol],
        "EMBOSS_RESERVED": ["BadWord", eol],
        "EMBOSS_RESERVED_": ["BadWord", eol],
        "EMBOSS_RESERVEDA": ["BadWord", eol],
        "emboss_reserved": ["BadWord", eol],
        "emboss_reserved_": ["BadWord", eol],
        "emboss_reserveda": ["BadWord", eol],
        "0x0123456789abcdefABCDEF": ["Number", eol],
        "0": ["Number", eol],
        "1": ["Number", eol],
        "1a": ["BadNumber", eol],
        "1g": ["BadWord", eol],
        "1234567890": ["Number", eol],
        "1_234_567_890": ["Number", eol],
        "234_567_890": ["Number", eol],
        "34_567_890": ["Number", eol],
        "4_567_890": ["Number", eol],
        "1_2_3_4_5_6_7_8_9_0": ["BadNumber", eol],
        "1234567890_": ["BadNumber", eol],
        "1__234567890": ["BadNumber", eol],
        "_1234567890": ["BadWord", eol],
        "[]": ['"["', '"]"', eol],
        "()": ['"("', '")"', eol],
        "..": ['"."', '"."', eol],
        "...": ['"."', '"."', '"."', eol],
        "....": ['"."', '"."', '"."', '"."', eol],
        '"abc"': ["String", eol],
        '""': ["String", eol],
        r'"\\"': ["String", eol],
        r'"\""': ["String", eol],
        r'"\n"': ["String", eol],
        r'"\\n"': ["String", eol],
        r'"\\xyz"': ["String", eol],
        r'"\\\\"': ["String", eol],
    }
    for c in (
        "[ ] ( ) ? : = + - * . == != < <= > >= && || , $max $present "
        "$upper_bound $lower_bound $size_in_bits $size_in_bytes "
        "$max_size_in_bits $max_size_in_bytes $min_size_in_bits "
        "$min_size_in_bytes "
        "$default struct bits enum external import as if let"
    ).split():
        cases[c] = ['"' + c + '"', eol]

    def make_test_case(case):

        def test_case(self):
            tokens, errors = tokenizer.tokenize(case, "name")
            symbols = _token_symbols(tokens)
            self.assertFalse(errors)
            self.assertEqual(symbols, cases[case])

        return test_case

    for c in cases:
        setattr(TokenizerTest, "testShortTokenMatch{!r}".format(c), make_test_case(c))


def _make_bad_char_tests():
    """Makes tests that an error is returned for bad characters."""

    def make_test_case(case):

        def test_case(self):
            tokens, errors = tokenizer.tokenize(case, "name")
            self.assertFalse(tokens)
            self.assertEqual(
                [
                    [
                        error.error(
                            "name",
                            parser_types.make_location((1, 1), (1, 2)),
                            "Unrecognized token",
                        )
                    ]
                ],
                errors,
            )

        return test_case

    for c in "~`!@%^&\\|;'\"/{}":
        setattr(TokenizerTest, "testBadChar{!r}".format(c), make_test_case(c))


def _make_bad_string_tests():
    """Makes tests that an error is returned for bad strings."""
    bad_strings = (r'"\"', '"\\\n"', r'"\\\"', r'"', r'"\q"', r'"\\\q"')

    def make_test_case(string):

        def test_case(self):
            tokens, errors = tokenizer.tokenize(string, "name")
            self.assertFalse(tokens)
            self.assertEqual(
                [
                    [
                        error.error(
                            "name",
                            parser_types.make_location((1, 1), (1, 2)),
                            "Unrecognized token",
                        )
                    ]
                ],
                errors,
            )

        return test_case

    for s in bad_strings:
        setattr(TokenizerTest, "testBadString{!r}".format(s), make_test_case(s))


def _make_multiline_tests():
    """Makes tests for indent/dedent insertion and eol insertion."""

    c = "Comment"
    eol = '"\\n"'
    sw = "SnakeWord"
    ind = "Indent"
    ded = "Dedent"
    cases = {
        "a\nb\n": [sw, eol, sw, eol],
        "a\n\nb\n": [sw, eol, eol, sw, eol],
        "a\n#foo\nb\n": [sw, eol, c, eol, sw, eol],
        "a\n   #foo\nb\n": [sw, eol, c, eol, sw, eol],
        "a\n b\n": [sw, eol, ind, sw, eol, ded],
        "a\n b\n\n": [sw, eol, ind, sw, eol, eol, ded],
        "a\n b\n  c\n": [sw, eol, ind, sw, eol, ind, sw, eol, ded, ded],
        "a\n b\n c\n": [sw, eol, ind, sw, eol, sw, eol, ded],
        "a\n b\n\n c\n": [sw, eol, ind, sw, eol, eol, sw, eol, ded],
        "a\n b\n    #\n c\n": [sw, eol, ind, sw, eol, c, eol, sw, eol, ded],
        "a\n\tb\n    #\n\tc\n": [sw, eol, ind, sw, eol, c, eol, sw, eol, ded],
        " a\n  b\n   c\n d\n": [
            ind,
            sw,
            eol,
            ind,
            sw,
            eol,
            ind,
            sw,
            eol,
            ded,
            ded,
            sw,
            eol,
            ded,
        ],
    }

    def make_test_case(case):

        def test_case(self):
            tokens, errors = tokenizer.tokenize(case, "file")
            self.assertFalse(errors)
            self.assertEqual(_token_symbols(tokens), cases[case])

        return test_case

    for c in cases:
        setattr(TokenizerTest, "testMultiline{!r}".format(c), make_test_case(c))


def _make_offset_tests():
    """Makes tests that the tokenizer fills in correct source locations."""
    cases = {
        "a+": ["1:1-1:2", "1:2-1:3", "1:3-1:3"],
        "a   +   ": ["1:1-1:2", "1:5-1:6", "1:9-1:9"],
        "a\n\nb": ["1:1-1:2", "1:2-1:2", "2:1-2:1", "3:1-3:2", "3:2-3:2"],
        "a\n  b": ["1:1-1:2", "1:2-1:2", "2:1-2:3", "2:3-2:4", "2:4-2:4", "3:1-3:1"],
        "a\n  b\nc": [
            "1:1-1:2",
            "1:2-1:2",
            "2:1-2:3",
            "2:3-2:4",
            "2:4-2:4",
            "3:1-3:1",
            "3:1-3:2",
            "3:2-3:2",
        ],
        "a\n b\n  c": [
            "1:1-1:2",
            "1:2-1:2",
            "2:1-2:2",
            "2:2-2:3",
            "2:3-2:3",
            "3:2-3:3",
            "3:3-3:4",
            "3:4-3:4",
            "4:1-4:1",
            "4:1-4:1",
        ],
    }

    def make_test_case(case):

        def test_case(self):
            self.assertEqual(
                [
                    parser_types.format_location(l.source_location)
                    for l in tokenizer.tokenize(case, "file")[0]
                ],
                cases[case],
            )

        return test_case

    for c in cases:
        setattr(TokenizerTest, "testOffset{!r}".format(c), make_test_case(c))


_make_short_token_match_tests()
_make_bad_char_tests()
_make_bad_string_tests()
_make_multiline_tests()
_make_offset_tests()

if __name__ == "__main__":
    unittest.main()
