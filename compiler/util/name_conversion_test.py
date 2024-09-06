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

"""Tests for util.name_conversion."""

import unittest
from compiler.util import name_conversion


class NameConversionTest(unittest.TestCase):

    def test_snake_to_camel(self):
        self.assertEqual("", name_conversion.snake_to_camel(""))
        self.assertEqual("Abc", name_conversion.snake_to_camel("abc"))
        self.assertEqual("AbcDef", name_conversion.snake_to_camel("abc_def"))
        self.assertEqual("AbcDef89", name_conversion.snake_to_camel("abc_def89"))
        self.assertEqual("AbcDef89", name_conversion.snake_to_camel("abc_def_89"))
        self.assertEqual("Abc89Def", name_conversion.snake_to_camel("abc_89_def"))
        self.assertEqual("Abc89def", name_conversion.snake_to_camel("abc_89def"))

    def test_shouty_to_camel(self):
        self.assertEqual("Abc", name_conversion.snake_to_camel("ABC"))
        self.assertEqual("AbcDef", name_conversion.snake_to_camel("ABC_DEF"))
        self.assertEqual("AbcDef89", name_conversion.snake_to_camel("ABC_DEF89"))
        self.assertEqual("AbcDef89", name_conversion.snake_to_camel("ABC_DEF_89"))
        self.assertEqual("Abc89Def", name_conversion.snake_to_camel("ABC_89_DEF"))
        self.assertEqual("Abc89def", name_conversion.snake_to_camel("ABC_89DEF"))

    def test_camel_to_k_camel(self):
        self.assertEqual("kFoo", name_conversion.camel_to_k_camel("Foo"))
        self.assertEqual("kFooBar", name_conversion.camel_to_k_camel("FooBar"))
        self.assertEqual("kAbc123", name_conversion.camel_to_k_camel("Abc123"))

    def test_snake_to_k_camel(self):
        self.assertEqual("kAbc", name_conversion.snake_to_k_camel("abc"))
        self.assertEqual("kAbcDef", name_conversion.snake_to_k_camel("abc_def"))
        self.assertEqual("kAbcDef89", name_conversion.snake_to_k_camel("abc_def89"))
        self.assertEqual("kAbcDef89", name_conversion.snake_to_k_camel("abc_def_89"))
        self.assertEqual("kAbc89Def", name_conversion.snake_to_k_camel("abc_89_def"))
        self.assertEqual("kAbc89def", name_conversion.snake_to_k_camel("abc_89def"))

    def test_shouty_to_k_camel(self):
        self.assertEqual("kAbc", name_conversion.snake_to_k_camel("ABC"))
        self.assertEqual("kAbcDef", name_conversion.snake_to_k_camel("ABC_DEF"))
        self.assertEqual("kAbcDef89", name_conversion.snake_to_k_camel("ABC_DEF89"))
        self.assertEqual("kAbcDef89", name_conversion.snake_to_k_camel("ABC_DEF_89"))
        self.assertEqual("kAbc89Def", name_conversion.snake_to_k_camel("ABC_89_DEF"))
        self.assertEqual("kAbc89def", name_conversion.snake_to_k_camel("ABC_89DEF"))

    def test_convert_case(self):
        self.assertEqual(
            "foo_bar_123",
            name_conversion.convert_case("snake_case", "snake_case", "foo_bar_123"),
        )
        self.assertEqual(
            "FOO_BAR_123",
            name_conversion.convert_case("SHOUTY_CASE", "SHOUTY_CASE", "FOO_BAR_123"),
        )
        self.assertEqual(
            "kFooBar123",
            name_conversion.convert_case("kCamelCase", "kCamelCase", "kFooBar123"),
        )
        self.assertEqual(
            "FooBar123",
            name_conversion.convert_case("CamelCase", "CamelCase", "FooBar123"),
        )
        self.assertEqual(
            "kAbcDef",
            name_conversion.convert_case("snake_case", "kCamelCase", "abc_def"),
        )
        self.assertEqual(
            "AbcDef", name_conversion.convert_case("snake_case", "CamelCase", "abc_def")
        )
        self.assertEqual(
            "kAbcDef",
            name_conversion.convert_case("SHOUTY_CASE", "kCamelCase", "ABC_DEF"),
        )
        self.assertEqual(
            "AbcDef",
            name_conversion.convert_case("SHOUTY_CASE", "CamelCase", "ABC_DEF"),
        )


if __name__ == "__main__":
    unittest.main()
