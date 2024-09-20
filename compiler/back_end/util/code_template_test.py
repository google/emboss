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

"""Tests for code_template."""

import string
import unittest
from compiler.back_end.util import code_template


def _format_template_str(template: str, **kwargs) -> str:
    return code_template.format_template(string.Template(template), **kwargs)


class FormatTest(unittest.TestCase):
    """Tests for code_template.format."""

    def test_no_replacement_fields(self):
        self.assertEqual("foo", _format_template_str("foo"))
        self.assertEqual("{foo}", _format_template_str("{foo}"))
        self.assertEqual("${foo}", _format_template_str("$${foo}"))

    def test_one_replacement_field(self):
        self.assertEqual("foo", _format_template_str("${bar}", bar="foo"))
        self.assertEqual("bazfoo", _format_template_str("baz${bar}", bar="foo"))
        self.assertEqual("foobaz", _format_template_str("${bar}baz", bar="foo"))
        self.assertEqual("bazfooqux", _format_template_str("baz${bar}qux", bar="foo"))

    def test_one_replacement_field_with_formatting(self):
        # Basic string.Templates don't support formatting values.
        self.assertRaises(ValueError, _format_template_str, "${bar:.6f}", bar=1)

    def test_one_replacement_field_value_missing(self):
        self.assertRaises(KeyError, _format_template_str, "${bar}")

    def test_multiple_replacement_fields(self):
        self.assertEqual(
            " aaa  bbb   ",
            _format_template_str(" ${bar}  ${baz}   ", bar="aaa", baz="bbb"),
        )


class ParseTemplatesTest(unittest.TestCase):
    """Tests for code_template.parse_templates."""

    def assertTemplatesEqual(self, expected, actual):  # pylint:disable=invalid-name
        """Compares the results of a parse_templates."""
        # Extract the name and template from the result tuple
        actual = {k: v.template for k, v in actual._asdict().items()}
        self.assertEqual(expected, actual)

    def test_handles_no_template_case(self):
        self.assertTemplatesEqual({}, code_template.parse_templates(""))
        self.assertTemplatesEqual(
            {}, code_template.parse_templates("this is not a template")
        )

    def test_handles_one_template_at_start(self):
        self.assertTemplatesEqual(
            {"foo": "bar"}, code_template.parse_templates("** foo **\nbar")
        )

    def test_handles_one_template_after_start(self):
        self.assertTemplatesEqual(
            {"foo": "bar"}, code_template.parse_templates("text\n** foo **\nbar")
        )

    def test_handles_delimiter_with_other_text(self):
        self.assertTemplatesEqual(
            {"foo": "bar"},
            code_template.parse_templates("text\n// ** foo ** ////\nbar"),
        )
        self.assertTemplatesEqual(
            {"foo": "bar"},
            code_template.parse_templates("text\n# ** foo ** #####\nbar"),
        )

    def test_handles_multiple_delimiters(self):
        self.assertTemplatesEqual(
            {"foo": "bar", "baz": "qux"},
            code_template.parse_templates("** foo **\nbar\n** baz **\nqux"),
        )

    def test_returns_object_with_attributes(self):
        self.assertEqual(
            "bar",
            code_template.parse_templates(
                "** foo **\nbar\n** baz **\nqux"
            ).foo.template,
        )


if __name__ == "__main__":
    unittest.main()
