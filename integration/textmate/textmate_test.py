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

import json
import os
import re
import unittest


class TextmateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        json_path = os.path.join(os.path.dirname(__file__), "emboss.tmLanguage.json")
        with open(json_path, encoding="utf-8") as f:
            cls.data = json.load(f)

    def test_valid_json(self):
        self.assertEqual(self.data.get("name"), "Emboss")
        self.assertEqual(self.data.get("scopeName"), "source.emboss")
        self.assertIn("emb", self.data.get("fileTypes", []))

    def test_all_includes_exist_and_regexes_compile(self):
        repository = self.data.get("repository", {})

        def check_pattern(pattern):
            if "include" in pattern:
                include = pattern["include"]
                if include.startswith("#"):
                    self.assertIn(include[1:], repository)
            for regex_key in ("match", "begin", "end"):
                if regex_key in pattern:
                    re.compile(pattern[regex_key])
            if "patterns" in pattern:
                for p in pattern["patterns"]:
                    check_pattern(p)

        if "patterns" in self.data:
            for p in self.data["patterns"]:
                check_pattern(p)
        for val in repository.values():
            check_pattern(val)


if __name__ == "__main__":
    unittest.main()
