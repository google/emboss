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

"""Tests that doc/grammar.md is up to date."""

import pkgutil

import unittest
from compiler.front_end import generate_grammar_md


class DocsAreUpToDateTest(unittest.TestCase):
    """Tests that auto-generated, checked-in documentation is up to date."""

    def test_grammar_md(self):
        doc_md = pkgutil.get_data("doc", "grammar.md").decode(encoding="UTF-8")
        correct_md = generate_grammar_md.generate_grammar_md()
        msg = "Run:\n\nbazel run //compiler/front_end:generate_grammar_md > doc/grammar.md"
        doc_md_lines = doc_md.splitlines()
        correct_md_lines = correct_md.splitlines()
        for i in range(len(doc_md_lines)):
            self.assertEqual(correct_md_lines[i], doc_md_lines[i], msg=msg)
        self.assertEqual(correct_md, doc_md, msg=msg)


if __name__ == "__main__":
    unittest.main()
