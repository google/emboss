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

"""Generates a Markdown file documenting the raw Emboss grammar."""

from __future__ import print_function

import re
import sys

from compiler.front_end import constraints
from compiler.front_end import module_ir
from compiler.front_end import tokenizer

# Keep the output to less than 80 columns, so that the preformatted sections are
# not cut off.
_MAX_OUTPUT_WIDTH = 80

_HEADER = """
This is the context-free grammar for Emboss.  Terminal symbols are in `"quotes"`
or are named in `CamelCase`; nonterminal symbols are named in `snake_case`.  The
term `<empty>` to the right of the `->` indicates an empty production (a rule
where the left-hand-side may be parsed from an empty string).

This listing is auto-generated from the grammar defined in `module_ir.py`.

Note that, unlike in many languages, comments are included in the grammar.  This
is so that comments can be handled more easily by the autoformatter; comments
are ignored by the compiler.  This is distinct from *documentation*, which is
included in the IR for use by documentation generators.

""".lstrip()

_BOILERPLATE_PRODUCTION_HEADER = """
The following productions are automatically generated to handle zero-or-more,
one-or-more, and zero-or-one repeated lists (`foo*`, `foo+`, and `foo?`
nonterminals) in LR(1).  They are included for completeness, but may be ignored
if you just want to understand the grammar.

"""

_TOKENIZER_RULE_HEADER = """
The following regexes are used to tokenize input into the corresponding symbols.
Note that the `Indent`, `Dedent`, and `EndOfLine` symbols are generated using
separate logic.

"""

_KEYWORDS_HEADER = """
The following {} keywords are reserved, but not used, by Emboss.  They may not
be used as field, type, or enum value names.

"""


def _sort_productions(productions, start_symbol):
    """Sorts the given productions in a human-friendly order."""
    productions_by_lhs = {}
    for p in productions:
        if p.lhs not in productions_by_lhs:
            productions_by_lhs[p.lhs] = set()
        productions_by_lhs[p.lhs].add(p)

    queue = [start_symbol]
    previously_queued_symbols = set(queue)
    main_production_list = []
    # This sorts productions depth-first.  I'm not sure if it is better to sort
    # them breadth-first or depth-first, or with some hybrid.
    while queue:
        symbol = queue.pop(-1)
        if symbol not in productions_by_lhs:
            continue
        for production in sorted(productions_by_lhs[symbol]):
            main_production_list.append(production)
            for symbol in production.rhs:
                # Skip boilerplate productions for now, but include their base
                # production.
                if symbol and symbol[-1] in "*+?":
                    symbol = symbol[0:-1]
                if symbol not in previously_queued_symbols:
                    queue.append(symbol)
                    previously_queued_symbols.add(symbol)

    # It's not particularly important to put boilerplate productions in any
    # particular order.
    boilerplate_production_list = sorted(set(productions) - set(main_production_list))
    for production in boilerplate_production_list:
        assert production.lhs[-1] in "*+?", "Found orphaned production {}".format(
            production.lhs
        )
    assert set(productions) == set(main_production_list + boilerplate_production_list)
    assert len(productions) == len(main_production_list) + len(
        boilerplate_production_list
    )
    return main_production_list, boilerplate_production_list


def _word_wrap_at_column(words, width):
    """Wraps words to the specified width, and returns a list of wrapped lines."""
    result = []
    in_progress = []
    for word in words:
        if len(" ".join(in_progress + [word])) > width:
            result.append(" ".join(in_progress))
            assert len(result[-1]) <= width
            in_progress = []
        in_progress.append(word)
    result.append(" ".join(in_progress))
    assert len(result[-1]) <= width
    return result


def _format_productions(productions):
    """Formats a list of productions for inclusion in a Markdown document."""
    max_lhs_len = max([len(production.lhs) for production in productions])

    # TODO(bolms): This highlighting is close for now, but not actually right.
    result = ["```shell\n"]
    last_lhs = None
    for production in productions:
        if last_lhs == production.lhs:
            lhs = ""
            delimiter = " |"
        else:
            lhs = production.lhs
            delimiter = "->"
        leader = "{lhs:{width}} {delimiter}".format(
            lhs=lhs, width=max_lhs_len, delimiter=delimiter
        )
        for rhs_block in _word_wrap_at_column(
            production.rhs or ["<empty>"], _MAX_OUTPUT_WIDTH - len(leader)
        ):
            result.append("{leader} {rhs}\n".format(leader=leader, rhs=rhs_block))
            leader = " " * len(leader)
        last_lhs = production.lhs
    result.append("```\n")
    return "".join(result)


def _normalize_literal_patterns(literals):
    """Normalizes a list of strings to a list of (regex, symbol) pairs."""
    return [
        (re.sub(r"(\W)", r"\\\1", literal), '"' + literal + '"') for literal in literals
    ]


def _normalize_regex_patterns(regexes):
    """Normalizes a list of tokenizer regexes to a list of (regex, symbol)."""
    # g3doc breaks up patterns containing '|' when they are inserted into a table,
    # unless they're preceded by '\'.  Note that other special characters,
    # including '\', should *not* be escaped with '\'.
    return [(re.sub(r"\|", r"\\|", r.regex.pattern), r.symbol) for r in regexes]


def _normalize_reserved_word_list(reserved_words):
    """Returns words that would be allowed as names if they were not reserved."""
    interesting_reserved_words = []
    for word in reserved_words:
        tokens, errors = tokenizer.tokenize(word, "")
        assert tokens and not errors, "Failed to tokenize " + word
        if tokens[0].symbol in ["SnakeWord", "CamelWord", "ShoutyWord"]:
            interesting_reserved_words.append(word)
    return sorted(interesting_reserved_words)


def _format_token_rules(token_rules):
    """Formats a list of (pattern, symbol) pairs as a table."""
    pattern_width = max([len(rule[0]) for rule in token_rules])
    pattern_width += 2  # For the `` characters.
    result = [
        "{pat_header:{width}} | Symbol\n"
        "{empty:-<{width}} | {empty:-<30}\n".format(
            pat_header="Pattern", width=pattern_width, empty=""
        )
    ]
    for rule in token_rules:
        if rule[1]:
            symbol_name = "`" + rule[1] + "`"
        else:
            symbol_name = "*no symbol emitted*"
        result.append(
            "{pattern:{width}} | {symbol}\n".format(
                pattern="`" + rule[0] + "`", width=pattern_width, symbol=symbol_name
            )
        )
    return "".join(result)


def _format_keyword_list(reserved_words):
    """formats a list of reserved words."""
    lines = []
    current_line = ""
    for word in reserved_words:
        if len(current_line) + len(word) + 2 > 80:
            lines.append(current_line)
            current_line = ""
        current_line += "`{}` ".format(word)
    return "".join([line[:-1] + "\n" for line in lines])


def generate_grammar_md():
    """Generates up-to-date text for grammar.md."""
    main_productions, boilerplate_productions = _sort_productions(
        module_ir.PRODUCTIONS, module_ir.START_SYMBOL
    )
    result = [
        _HEADER,
        _format_productions(main_productions),
        _BOILERPLATE_PRODUCTION_HEADER,
        _format_productions(boilerplate_productions),
    ]

    main_tokens = _normalize_literal_patterns(tokenizer.LITERAL_TOKEN_PATTERNS)
    main_tokens += _normalize_regex_patterns(tokenizer.REGEX_TOKEN_PATTERNS)
    result.append(_TOKENIZER_RULE_HEADER)
    result.append(_format_token_rules(main_tokens))

    reserved_words = _normalize_reserved_word_list(constraints.get_reserved_word_list())
    result.append(_KEYWORDS_HEADER.format(len(reserved_words)))
    result.append(_format_keyword_list(reserved_words))

    return "".join(result)


def main(argv):
    del argv  # Unused.
    print(generate_grammar_md(), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
