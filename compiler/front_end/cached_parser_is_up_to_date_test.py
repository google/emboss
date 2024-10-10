# Copyright 2024 Google LLC
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

"""Tests that compiler/front_end/generated/cached_parser.py is up to date."""

import pkgutil
import unittest

from compiler.front_end import generate_cached_parser


class CachedParserIsUpToDateTest(unittest.TestCase):
    """Tests that the generated, checked-in parser is up to date."""

    def test_grammar_md(self):
        cached_parser_text = pkgutil.get_data(
            "compiler.front_end.generated", "cached_parser.py"
        ).decode(encoding="UTF-8")
        correct_parser_text = generate_cached_parser.generate_parser_file_text()
        self.assertEqual(
            cached_parser_text,
            correct_parser_text,
            msg="Run\n\nbazel run //compiler/front_end:generate_cached_parser > compiler/front_end/generated/cached_parser.py",
        )


if __name__ == "__main__":
    unittest.main()
