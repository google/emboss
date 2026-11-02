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

"""Checks that the VS Code TextMate grammar agrees with the Emboss tokenizer.

Every literal and every regex example from compiler/front_end/tokenizer.py is
classified with the grammar's top-level rules, and the winning rule must have
the scope family that matches the tokenizer's token symbol.  This catches
drift when the tokenizer gains a new keyword or operator.

This is a light check: it uses Python's re module in place of the Oniguruma
engine that VS Code uses, and only looks at which rule wins at column 0.
"""

import json
import os
import re
import unittest

from compiler.front_end import tokenizer

_GRAMMAR_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "syntaxes", "emboss.tmLanguage.json"
)

_STORAGE_TYPES = frozenset(["struct", "bits", "enum", "external"])
_KEYWORDS = frozenset(["import", "as", "if", "let"])
_SUPPORT_FUNCTIONS = frozenset(["$present", "$max", "$upper_bound", "$lower_bound"])
_PUNCTUATION = frozenset(["[", "]", "(", ")", ":", ".", ","])

# Expected scope prefixes for each REGEX_TOKEN_PATTERNS symbol.
_REGEX_SYMBOL_SCOPES = {
    "String": ("string.quoted.double",),
    "Number": ("constant.numeric",),
    "BooleanConstant": ("constant.language",),
    "SnakeWord": ("variable.other",),
    "ShoutyWord": ("variable.other.constant",),
    "CamelWord": ("entity.name.type", "support.type"),
    "Documentation": ("comment.line.double-dash",),
    "Comment": ("comment.line.number-sign",),
    "BadWord": ("invalid.illegal",),
    "BadNumber": ("invalid.illegal",),
    "BadDocumentation": ("invalid.illegal",),
}


def _load_grammar():
    with open(_GRAMMAR_PATH, encoding="utf-8") as f:
        return json.load(f)


def _flatten_rules(patterns, repository):
    """Returns the rules in `patterns`, in order, with includes resolved."""
    rules = []
    for pattern in patterns:
        if "include" in pattern:
            include = pattern["include"]
            assert include.startswith("#"), "Unsupported include: " + include
            rules.extend(_flatten_rules([repository[include[1:]]], repository))
        elif "match" in pattern or "begin" in pattern:
            rules.append(pattern)
        elif "patterns" in pattern:
            rules.extend(_flatten_rules(pattern["patterns"], repository))
    return rules


def _winning_rule(rules, text):
    """Returns (name, match_length) of the rule TextMate picks at column 0.

    All candidate rules start at column 0, so TextMate picks the earliest one
    in rule order.  match_length is None for begin/end rules.
    """
    for rule in rules:
        if "match" in rule:
            m = re.match(rule["match"], text)
            if m:
                return rule.get("name"), m.end()
        else:
            if re.match(rule["begin"], text):
                return rule.get("name"), None
    return None, None


def _expected_literal_scope(literal):
    if literal in _STORAGE_TYPES:
        return "storage.type"
    if literal in _KEYWORDS:
        return "keyword."
    if literal == "$default":
        return "keyword.other"
    if literal in _SUPPORT_FUNCTIONS:
        return "support.function"
    if literal.startswith("$"):
        return "variable.language"
    if literal in _PUNCTUATION:
        return "punctuation"
    if literal[0].isalpha():
        return "keyword."
    return "keyword.operator"


class GrammarTest(unittest.TestCase):
    """Tests for syntaxes/emboss.tmLanguage.json."""

    def setUp(self):
        self.grammar = _load_grammar()
        self.rules = _flatten_rules(
            self.grammar["patterns"], self.grammar.get("repository", {})
        )

    def test_grammar_scope_name(self):
        self.assertEqual("source.emboss", self.grammar["scopeName"])

    def test_every_literal_token_has_expected_scope(self):
        for literal in tokenizer.LITERAL_TOKEN_PATTERNS:
            with self.subTest(literal=literal):
                name, length = _winning_rule(self.rules, literal)
                expected = _expected_literal_scope(literal)
                self.assertIsNotNone(name, "No named rule matches " + literal)
                self.assertTrue(
                    name.startswith(expected),
                    "{!r} got scope {!r}, want {!r}".format(literal, name, expected),
                )
                if literal in _KEYWORDS:
                    self.assertFalse(name.startswith("keyword.operator"))
                if length is not None:
                    self.assertEqual(len(literal), length)

    def test_every_regex_token_example_has_expected_scope(self):
        for pattern in tokenizer.REGEX_TOKEN_PATTERNS:
            if pattern.symbol is None:
                continue
            with self.subTest(symbol=pattern.symbol, example=pattern.example):
                name, _ = _winning_rule(self.rules, pattern.example)
                expected = _REGEX_SYMBOL_SCOPES[pattern.symbol]
                self.assertIsNotNone(name, "No named rule matches " + pattern.example)
                self.assertTrue(
                    name.startswith(expected),
                    "{!r} ({}) got scope {!r}, want one of {!r}".format(
                        pattern.example, pattern.symbol, name, expected
                    ),
                )
                if pattern.symbol == "SnakeWord":
                    self.assertFalse(name.startswith("variable.other.constant"))


if __name__ == "__main__":
    unittest.main()
