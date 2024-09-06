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

"""Tests for lr1."""

import collections
import unittest

from compiler.front_end import lr1
from compiler.util import parser_types


def _make_items(text):
    """Makes a list of lr1.Items from the lines in text."""
    return frozenset([lr1.Item.parse(line.strip()) for line in text.splitlines()])


Token = collections.namedtuple("Token", ["symbol", "source_location"])


def _tokenize(text):
    """ "Tokenizes" text by making each character into a token."""
    result = []
    for i in range(len(text)):
        result.append(
            Token(text[i], parser_types.make_location((1, i + 1), (1, i + 2)))
        )
    return result


def _parse_productions(text):
    """Parses text into a grammar by calling Production.parse on each line."""
    return [parser_types.Production.parse(line) for line in text.splitlines()]


# Example grammar 4.54 from Aho, Sethi, Lam, Ullman (ASLU) p263.
_alsu_grammar = lr1.Grammar(
    "S",
    _parse_productions(
        """S -> C C
                                                      C -> c C
                                                      C -> d"""
    ),
)

# Item sets corresponding to the above grammar, ASLU pp263-264.
_alsu_items = [
    _make_items(
        """S' -> . S, $
                  S -> . C C, $
                  C -> . c C, c
                  C -> . c C, d
                  C -> . d, c
                  C -> . d, d"""
    ),
    _make_items("""S' -> S ., $"""),
    _make_items(
        """S -> C . C, $
                  C -> . c C, $
                  C -> . d, $"""
    ),
    _make_items(
        """C -> c . C, c
                  C -> c . C, d
                  C -> . c C, c
                  C -> . c C, d
                  C -> . d, c
                  C -> . d, d"""
    ),
    _make_items(
        """C -> d ., c
                  C -> d ., d"""
    ),
    _make_items("""S -> C C ., $"""),
    _make_items(
        """C -> c . C, $
                  C -> . c C, $
                  C -> . d, $"""
    ),
    _make_items("""C -> d ., $"""),
    _make_items(
        """C -> c C ., c
                  C -> c C ., d"""
    ),
    _make_items("""C -> c C ., $"""),
]

# ACTION table corresponding to the above grammar, ASLU p266.
_alsu_action = {
    (0, "c"): lr1.Shift(3, _alsu_items[3]),
    (0, "d"): lr1.Shift(4, _alsu_items[4]),
    (1, lr1.END_OF_INPUT): lr1.Accept(),
    (2, "c"): lr1.Shift(6, _alsu_items[6]),
    (2, "d"): lr1.Shift(7, _alsu_items[7]),
    (3, "c"): lr1.Shift(3, _alsu_items[3]),
    (3, "d"): lr1.Shift(4, _alsu_items[4]),
    (4, "c"): lr1.Reduce(parser_types.Production("C", ("d",))),
    (4, "d"): lr1.Reduce(parser_types.Production("C", ("d",))),
    (5, lr1.END_OF_INPUT): lr1.Reduce(parser_types.Production("S", ("C", "C"))),
    (6, "c"): lr1.Shift(6, _alsu_items[6]),
    (6, "d"): lr1.Shift(7, _alsu_items[7]),
    (7, lr1.END_OF_INPUT): lr1.Reduce(parser_types.Production("C", ("d",))),
    (8, "c"): lr1.Reduce(parser_types.Production("C", ("c", "C"))),
    (8, "d"): lr1.Reduce(parser_types.Production("C", ("c", "C"))),
    (9, lr1.END_OF_INPUT): lr1.Reduce(parser_types.Production("C", ("c", "C"))),
}

# GOTO table corresponding to the above grammar, ASLU p266.
_alsu_goto = {
    (0, "S"): 1,
    (0, "C"): 2,
    (2, "C"): 5,
    (3, "C"): 8,
    (6, "C"): 9,
}


def _normalize_table(items, table):
    """Returns a canonical-form version of items and table, for comparisons."""
    item_to_original_index = {}
    for i in range(len(items)):
        item_to_original_index[items[i]] = i
    sorted_items = items[0:1] + sorted(items[1:], key=sorted)
    original_index_to_index = {}
    for i in range(len(sorted_items)):
        original_index_to_index[item_to_original_index[sorted_items[i]]] = i
    updated_table = {}
    for k in table:
        new_k = original_index_to_index[k[0]], k[1]
        new_value = table[k]
        if isinstance(new_value, int):
            new_value = original_index_to_index[new_value]
        elif isinstance(new_value, lr1.Shift):
            new_value = lr1.Shift(
                original_index_to_index[new_value.state], new_value.items
            )
        updated_table[new_k] = new_value
    return sorted_items, updated_table


class Lr1Test(unittest.TestCase):
    """Tests for lr1."""

    def test_parse_lr1item(self):
        self.assertEqual(
            lr1.Item.parse("S' -> . S, $"),
            lr1.Item(
                parser_types.Production(lr1.START_PRIME, ("S",)),
                0,
                lr1.END_OF_INPUT,
                "S",
            ),
        )

    def test_symbol_extraction(self):
        self.assertEqual(_alsu_grammar.terminals, set(["c", "d", lr1.END_OF_INPUT]))
        self.assertEqual(_alsu_grammar.nonterminals, set(["S", "C", lr1.START_PRIME]))
        self.assertEqual(
            _alsu_grammar.symbols,
            set(["c", "d", "S", "C", lr1.END_OF_INPUT, lr1.START_PRIME]),
        )

    def test_items(self):
        self.assertEqual(set(_alsu_grammar._items()[0]), frozenset(_alsu_items))

    def test_terminal_nonterminal_production_tables(self):
        parser = _alsu_grammar.parser()
        self.assertEqual(parser.terminals, _alsu_grammar.terminals)
        self.assertEqual(parser.nonterminals, _alsu_grammar.nonterminals)
        self.assertEqual(parser.productions, _alsu_grammar.productions)

    def test_action_table(self):
        parser = _alsu_grammar.parser()
        norm_items, norm_action = _normalize_table(parser.item_sets, parser.action)
        test_items, test_action = _normalize_table(_alsu_items, _alsu_action)
        self.assertEqual(norm_items, test_items)
        self.assertEqual(norm_action, test_action)

    def test_goto_table(self):
        parser = _alsu_grammar.parser()
        norm_items, norm_goto = _normalize_table(parser.item_sets, parser.goto)
        test_items, test_goto = _normalize_table(_alsu_items, _alsu_goto)
        self.assertEqual(norm_items, test_items)
        self.assertEqual(norm_goto, test_goto)

    def test_successful_parse(self):
        parser = _alsu_grammar.parser()
        loc = parser_types.parse_location
        s_to_c_c = parser_types.Production.parse("S -> C C")
        c_to_c_c = parser_types.Production.parse("C -> c C")
        c_to_d = parser_types.Production.parse("C -> d")
        self.assertEqual(
            lr1.Reduction(
                "S",
                [
                    lr1.Reduction(
                        "C",
                        [
                            Token("c", loc("1:1-1:2")),
                            lr1.Reduction(
                                "C",
                                [
                                    Token("c", loc("1:2-1:3")),
                                    lr1.Reduction(
                                        "C",
                                        [
                                            Token("c", loc("1:3-1:4")),
                                            lr1.Reduction(
                                                "C",
                                                [Token("d", loc("1:4-1:5"))],
                                                c_to_d,
                                                loc("1:4-1:5"),
                                            ),
                                        ],
                                        c_to_c_c,
                                        loc("1:3-1:5"),
                                    ),
                                ],
                                c_to_c_c,
                                loc("1:2-1:5"),
                            ),
                        ],
                        c_to_c_c,
                        loc("1:1-1:5"),
                    ),
                    lr1.Reduction(
                        "C",
                        [
                            Token("c", loc("1:5-1:6")),
                            lr1.Reduction(
                                "C",
                                [Token("d", loc("1:6-1:7"))],
                                c_to_d,
                                loc("1:6-1:7"),
                            ),
                        ],
                        c_to_c_c,
                        loc("1:5-1:7"),
                    ),
                ],
                s_to_c_c,
                loc("1:1-1:7"),
            ),
            parser.parse(_tokenize("cccdcd")).parse_tree,
        )
        self.assertEqual(
            lr1.Reduction(
                "S",
                [
                    lr1.Reduction(
                        "C", [Token("d", loc("1:1-1:2"))], c_to_d, loc("1:1-1:2")
                    ),
                    lr1.Reduction(
                        "C", [Token("d", loc("1:2-1:3"))], c_to_d, loc("1:2-1:3")
                    ),
                ],
                s_to_c_c,
                loc("1:1-1:3"),
            ),
            parser.parse(_tokenize("dd")).parse_tree,
        )

    def test_parse_with_no_source_information(self):
        parser = _alsu_grammar.parser()
        s_to_c_c = parser_types.Production.parse("S -> C C")
        c_to_d = parser_types.Production.parse("C -> d")
        self.assertEqual(
            lr1.Reduction(
                "S",
                [
                    lr1.Reduction("C", [Token("d", None)], c_to_d, None),
                    lr1.Reduction("C", [Token("d", None)], c_to_d, None),
                ],
                s_to_c_c,
                None,
            ),
            parser.parse([Token("d", None), Token("d", None)]).parse_tree,
        )

    def test_failed_parses(self):
        parser = _alsu_grammar.parser()
        self.assertEqual(None, parser.parse(_tokenize("d")).parse_tree)
        self.assertEqual(None, parser.parse(_tokenize("cccd")).parse_tree)
        self.assertEqual(None, parser.parse(_tokenize("")).parse_tree)
        self.assertEqual(None, parser.parse(_tokenize("cccdc")).parse_tree)

    def test_mark_error(self):
        parser = _alsu_grammar.parser()
        self.assertIsNone(parser.mark_error(_tokenize("cccdc"), None, "missing last d"))
        self.assertIsNone(parser.mark_error(_tokenize("d"), None, "missing last C"))
        # Marking an already-marked error with the same error code should succeed.
        self.assertIsNone(parser.mark_error(_tokenize("d"), None, "missing last C"))
        # Marking an already-marked error with a different error code should fail.
        self.assertRegexpMatches(
            parser.mark_error(_tokenize("d"), None, "different message"),
            r"^Attempted to overwrite existing error code 'missing last C' with "
            r"new error code 'different message' for state \d+, terminal \$$",
        )
        self.assertEqual(
            "Input successfully parsed.",
            parser.mark_error(_tokenize("dd"), None, "good parse"),
        )
        self.assertEqual(
            parser.mark_error(_tokenize("x"), None, "wrong location"),
            "error occurred on x token, not end of input.",
        )
        self.assertEqual(
            parser.mark_error([], _tokenize("x")[0], "wrong location"),
            "error occurred on $ token, not x token.",
        )
        self.assertIsNone(
            parser.mark_error([lr1.ANY_TOKEN], lr1.ANY_TOKEN, "default error")
        )
        # Marking an already-marked error with the same error code should succeed.
        self.assertIsNone(
            parser.mark_error([lr1.ANY_TOKEN], lr1.ANY_TOKEN, "default error")
        )
        # Marking an already-marked error with a different error code should fail.
        self.assertRegexpMatches(
            parser.mark_error([lr1.ANY_TOKEN], lr1.ANY_TOKEN, "default error 2"),
            r"^Attempted to overwrite existing default error code 'default error' "
            r"with new error code 'default error 2' for state \d+$",
        )

        self.assertEqual("missing last d", parser.parse(_tokenize("cccdc")).error.code)
        self.assertEqual("missing last d", parser.parse(_tokenize("dc")).error.code)
        self.assertEqual("missing last C", parser.parse(_tokenize("d")).error.code)
        self.assertEqual("default error", parser.parse(_tokenize("z")).error.code)
        self.assertEqual("missing last C", parser.parse(_tokenize("ccccd")).error.code)
        self.assertEqual(None, parser.parse(_tokenize("ccc")).error.code)

    def test_grammar_with_empty_rhs(self):
        grammar = lr1.Grammar(
            "S",
            _parse_productions(
                """S -> A B
                                                    A -> a A
                                                    A ->
                                                    B -> b"""
            ),
        )
        parser = grammar.parser()
        self.assertFalse(parser.conflicts)
        self.assertTrue(parser.parse(_tokenize("ab")).parse_tree)
        self.assertTrue(parser.parse(_tokenize("b")).parse_tree)
        self.assertTrue(parser.parse(_tokenize("aab")).parse_tree)

    def test_grammar_with_reduce_reduce_conflicts(self):
        grammar = lr1.Grammar(
            "S",
            _parse_productions(
                """S -> A c
                                                    S -> B c
                                                    A -> a
                                                    B -> a"""
            ),
        )
        parser = grammar.parser()
        self.assertEqual(len(parser.conflicts), 1)
        # parser.conflicts is a set
        for conflict in parser.conflicts:
            for action in conflict.actions:
                self.assertTrue(isinstance(action, lr1.Reduce))

    def test_grammar_with_shift_reduce_conflicts(self):
        grammar = lr1.Grammar(
            "S",
            _parse_productions(
                """S -> A B
                                                    A -> a
                                                    A ->
                                                    B -> a
                                                    B ->"""
            ),
        )
        parser = grammar.parser()
        self.assertEqual(len(parser.conflicts), 1)
        # parser.conflicts is a set
        for conflict in parser.conflicts:
            reduces = 0
            shifts = 0
            for action in conflict.actions:
                if isinstance(action, lr1.Reduce):
                    reduces += 1
                elif isinstance(action, lr1.Shift):
                    shifts += 1
            self.assertEqual(1, reduces)
            self.assertEqual(1, shifts)

    def test_item_str(self):
        self.assertEqual(
            "a -> b c ., d",
            str(lr1.make_item(parser_types.Production.parse("a -> b c"), 2, "d")),
        )
        self.assertEqual(
            "a -> b . c, d",
            str(lr1.make_item(parser_types.Production.parse("a -> b c"), 1, "d")),
        )
        self.assertEqual(
            "a -> . b c, d",
            str(lr1.make_item(parser_types.Production.parse("a -> b c"), 0, "d")),
        )
        self.assertEqual(
            "a -> ., d",
            str(lr1.make_item(parser_types.Production.parse("a ->"), 0, "d")),
        )

    def test_conflict_str(self):
        self.assertEqual(
            "Conflict for 'A' in state 12: R vs S",
            str(lr1.Conflict(12, "'A'", ["R", "S"])),
        )
        self.assertEqual(
            "Conflict for 'A' in state 12: R vs S vs T",
            str(lr1.Conflict(12, "'A'", ["R", "S", "T"])),
        )


if __name__ == "__main__":
    unittest.main()
