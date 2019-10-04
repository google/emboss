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

import unittest
from compiler.back_end.util import code_template


class FormatTest(unittest.TestCase):
  """Tests for code_template.format."""

  def test_no_replacement_fields(self):
    self.assertEqual("foo", code_template.format_template("foo"))
    self.assertEqual("{foo}", code_template.format_template("{foo}"))
    self.assertEqual("$foo$", code_template.format_template("$foo$"))
    self.assertEqual("$_foo$", code_template.format_template("$_foo$"))
    self.assertEqual("$foo_$", code_template.format_template("$foo_$"))

  def test_one_replacement_field(self):
    self.assertEqual("foo", code_template.format_template("$_bar_$", bar="foo"))
    self.assertEqual("bazfoo",
                     code_template.format_template("baz$_bar_$", bar="foo"))
    self.assertEqual("foobaz",
                     code_template.format_template("$_bar_$baz", bar="foo"))
    self.assertEqual("bazfooqux",
                     code_template.format_template("baz$_bar_$qux", bar="foo"))

  def test_one_replacement_field_with_formatting(self):
    self.assertEqual("1.000000",
                     code_template.format_template("$_bar:.6f_$", bar=1))
    self.assertEqual("'foo'",
                     code_template.format_template("$_bar!r_$", bar="foo"))
    self.assertEqual("==foo==",
                     code_template.format_template("$_bar:=^7_$", bar="foo"))
    self.assertEqual("=='foo'==",
                     code_template.format_template("$_bar!r:=^9_$", bar="foo"))
    self.assertEqual("xx=='foo'==yy",
                     code_template.format_template("xx$_bar!r:=^9_$yy",
                                                   bar="foo"))

  def test_one_replacement_field_value_missing(self):
    self.assertRaises(KeyError, code_template.format_template, "$_bar_$")

  def test_multiple_replacement_fields(self):
    self.assertEqual(" aaa  bbb   ",
                     code_template.format_template(" $_bar_$  $_baz_$   ",
                                                   bar="aaa",
                                                   baz="bbb"))


class ParseTemplatesTest(unittest.TestCase):
  """Tests for code_template.parse_templates."""

  def test_handles_no_template_case(self):
    self.assertEqual({}, code_template.parse_templates("")._asdict())
    self.assertEqual({}, code_template.parse_templates(
        "this is not a template")._asdict())

  def test_handles_one_template_at_start(self):
    self.assertEqual({"foo": "bar"},
                     code_template.parse_templates("** foo **\nbar")._asdict())

  def test_handles_one_template_after_start(self):
    self.assertEqual(
        {"foo": "bar"},
        code_template.parse_templates("text\n** foo **\nbar")._asdict())

  def test_handles_delimiter_with_other_text(self):
    self.assertEqual(
        {"foo": "bar"},
        code_template.parse_templates("text\n// ** foo ** ////\nbar")._asdict())
    self.assertEqual(
        {"foo": "bar"},
        code_template.parse_templates("text\n# ** foo ** #####\nbar")._asdict())

  def test_handles_multiple_delimiters(self):
    self.assertEqual({"foo": "bar",
                      "baz": "qux"}, code_template.parse_templates(
                          "** foo **\nbar\n** baz **\nqux")._asdict())

  def test_returns_object_with_attributes(self):
    self.assertEqual("bar", code_template.parse_templates(
        "** foo **\nbar\n** baz **\nqux").foo)

if __name__ == "__main__":
  unittest.main()
