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

"""Tests for front_end.format_emb."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pkgutil
import re
import sys

import unittest
from compiler.front_end import format_emb
from compiler.front_end import module_ir
from compiler.front_end import parser
from compiler.front_end import tokenizer


class SanityCheckerTest(unittest.TestCase):

    def test_text_does_not_tokenize(self):
        self.assertTrue(format_emb.sanity_check_format_result("-- doc", "~ bad"))

    def test_original_text_does_not_tokenize(self):
        self.assertTrue(format_emb.sanity_check_format_result("~ bad", "-- doc"))

    def test_text_matches(self):
        self.assertFalse(format_emb.sanity_check_format_result("-- doc", "-- doc"))

    def test_text_has_extra_eols(self):
        self.assertFalse(
            format_emb.sanity_check_format_result(
                "-- doc\n\n-- doc", "-- doc\n\n\n-- doc"
            )
        )

    def test_text_has_fewer_eols(self):
        self.assertFalse(
            format_emb.sanity_check_format_result("-- doc\n\n-- doc", "-- doc\n-- doc")
        )

    def test_original_text_has_leading_eols(self):
        self.assertFalse(
            format_emb.sanity_check_format_result("\n\n-- doc\n", "-- doc\n")
        )

    def test_original_text_has_extra_doc_whitespace(self):
        self.assertFalse(
            format_emb.sanity_check_format_result("-- doc     \n", "-- doc\n")
        )

    def test_comments_differ(self):
        self.assertTrue(
            format_emb.sanity_check_format_result("#c\n-- doc\n", "#d\n-- doc\n")
        )

    def test_comment_missing(self):
        self.assertTrue(
            format_emb.sanity_check_format_result("#c\n-- doc\n", "\n-- doc\n")
        )

    def test_comment_added(self):
        self.assertTrue(
            format_emb.sanity_check_format_result("\n-- doc\n", "#d\n-- doc\n")
        )

    def test_token_text_differs(self):
        self.assertTrue(
            format_emb.sanity_check_format_result("-- doc\n", "-- bad doc\n")
        )

    def test_token_type_differs(self):
        self.assertTrue(format_emb.sanity_check_format_result("-- doc\n", "abc\n"))

    def test_eol_missing(self):
        self.assertTrue(
            format_emb.sanity_check_format_result("abc\n-- doc\n", "abc -- doc\n")
        )


class FormatEmbTest(unittest.TestCase):
    pass


def _make_golden_file_tests():
    """Generates test cases from the golden files in the resource bundle."""

    package = "testdata.format"
    path_prefix = ""

    def make_test_case(name, unformatted_text, expected_text, indent_width):

        def test_case(self):
            self.maxDiff = 100000
            unformatted_tokens, errors = tokenizer.tokenize(unformatted_text, name)
            self.assertFalse(errors)
            parsed_unformatted = parser.parse_module(unformatted_tokens)
            self.assertFalse(parsed_unformatted.error)
            formatted_text = format_emb.format_emboss_parse_tree(
                parsed_unformatted.parse_tree,
                format_emb.Config(indent_width=indent_width),
            )
            self.assertEqual(expected_text, formatted_text)
            annotated_text = format_emb.format_emboss_parse_tree(
                parsed_unformatted.parse_tree,
                format_emb.Config(indent_width=indent_width, show_line_types=True),
            )
            self.assertEqual(
                expected_text, re.sub(r"^.*?\|", "", annotated_text, flags=re.MULTILINE)
            )
            self.assertFalse(re.search("^[^|]+$", annotated_text, flags=re.MULTILINE))

        return test_case

    all_unformatted_texts = []

    for filename in (
        "abbreviations",
        "anonymous_bits_formatting",
        "arithmetic_expressions",
        "array_length",
        "attributes",
        "choice_expression",
        "comparison_expressions",
        "conditional_field_formatting",
        "conditional_inline_bits_formatting",
        "dotted_names",
        "empty",
        "enum_value_attributes",
        "enum_value_bodies",
        "enum_values_aligned",
        "equality_expressions",
        "external",
        "extra_newlines",
        "fields_aligned",
        "functions",
        "header_and_type",
        "indent",
        "inline_attributes_get_a_column",
        "inline_bits",
        "inline_documentation_gets_a_column",
        "inline_enum",
        "inline_struct",
        "lines_not_spaced_out_with_excess_trailing_noise_lines",
        "lines_not_spaced_out_with_not_enough_noise_lines",
        "lines_spaced_out_with_noise_lines",
        "logical_expressions",
        "multiline_ifs",
        "multiple_header_sections",
        "nested_types_are_columnized_independently",
        "one_type",
        "parameterized_struct",
        "sanity_check",
        "spacing_between_types",
        "trailing_spaces",
        "virtual_fields",
    ):
        for suffix, width in ((".emb.formatted", 2), (".emb.formatted_indent_4", 4)):
            unformatted_name = path_prefix + filename + ".emb"
            expected_name = path_prefix + filename + suffix
            unformatted_text = pkgutil.get_data(package, unformatted_name).decode(
                "utf-8"
            )
            expected_text = pkgutil.get_data(package, expected_name).decode("utf-8")
            setattr(
                FormatEmbTest,
                "test {} indent {}".format(filename, width),
                make_test_case(filename, unformatted_text, expected_text, width),
            )

            all_unformatted_texts.append(unformatted_text)

    def test_all_productions_used(self):
        used_productions = set()
        for unformatted_text in all_unformatted_texts:
            unformatted_tokens, errors = tokenizer.tokenize(unformatted_text, "")
            self.assertFalse(errors)
            parsed_unformatted = parser.parse_module(unformatted_tokens)
            self.assertFalse(parsed_unformatted.error)
            format_emb.format_emboss_parse_tree(
                parsed_unformatted.parse_tree, format_emb.Config(), used_productions
            )
        unused_productions = set(module_ir.PRODUCTIONS) - used_productions
        if unused_productions:
            print("Used production total:", len(used_productions), file=sys.stderr)
            for production in unused_productions:
                print("Unused production:", str(production), file=sys.stderr)
            print("Total:", len(unused_productions), file=sys.stderr)
        self.assertEqual(set(module_ir.PRODUCTIONS), used_productions)

    FormatEmbTest.testAllProductionsUsed = test_all_productions_used


_make_golden_file_tests()

if __name__ == "__main__":
    unittest.main()
