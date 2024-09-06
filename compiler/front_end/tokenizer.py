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

"""Tokenization for the Emboss definition language.

This module exports the tokenize function and various errors.

In addition, a couple of lists are exported for the use of
generate_grammar_md.py:

LITERAL_TOKEN_PATTERNS: A list of literal strings which are matched against
  input.
REGEX_TOKEN_PATTERNS: A list of regexes used for tokenization.
  REGEX_TOKEN_PATTERNS[n].regex is an re.RegexObject
  (REGEX_TOKEN_PATTERNS[n].regex.pattern contains the text of the pattern), and
  REGEX_TOKEN_PATTERNS[n].symbol is the name of the symbol assigned to tokens
  which match the pattern.
"""

import collections
import re

from compiler.util import error
from compiler.util import parser_types


def tokenize(text, file_name):
    # TODO(bolms): suppress end-of-line, indent, and dedent tokens between matched
    # delimiters ([], (), and {}).
    """Tokenizes its argument.

    Arguments:
      text: The raw text of a .emb file.
      file_name: The name of the file to use in errors.

    Returns:
      A tuple of:
        a list of parser_types.Tokens or None
        a possibly-empty list of errors.
    """
    tokens = []
    indent_stack = [""]
    line_number = 0
    for line in text.splitlines():
        line_number += 1

        # _tokenize_line splits the actual text into tokens.
        line_tokens, errors = _tokenize_line(line, line_number, file_name)
        if errors:
            return None, errors

        # Lines with only whitespace and comments are not used for Indent/Dedent
        # calculation, and do not produce end-of-line tokens.
        for token in line_tokens:
            if token.symbol != "Comment":
                break
        else:
            tokens.extend(line_tokens)
            tokens.append(
                parser_types.Token(
                    '"\\n"',
                    "\n",
                    parser_types.make_location(
                        (line_number, len(line) + 1), (line_number, len(line) + 1)
                    ),
                )
            )
            continue

        # Leading whitespace is whatever .lstrip() removes.
        leading_whitespace = line[0 : len(line) - len(line.lstrip())]
        if leading_whitespace == indent_stack[-1]:
            # If the current leading whitespace is equal to the last leading
            # whitespace, do not emit an Indent or Dedent token.
            pass
        elif leading_whitespace.startswith(indent_stack[-1]):
            # If the current leading whitespace is longer than the last leading
            # whitespace, emit an Indent token.  For the token text, take the new
            # part of the whitespace.
            tokens.append(
                parser_types.Token(
                    "Indent",
                    leading_whitespace[len(indent_stack[-1]) :],
                    parser_types.make_location(
                        (line_number, len(indent_stack[-1]) + 1),
                        (line_number, len(leading_whitespace) + 1),
                    ),
                )
            )
            indent_stack.append(leading_whitespace)
        else:
            # Otherwise, search for the unclosed indentation level that matches
            # the current indentation level.  Emit a Dedent token for each
            # newly-closed indentation level.
            for i in range(len(indent_stack) - 1, -1, -1):
                if leading_whitespace == indent_stack[i]:
                    break
                tokens.append(
                    parser_types.Token(
                        "Dedent",
                        "",
                        parser_types.make_location(
                            (line_number, len(leading_whitespace) + 1),
                            (line_number, len(leading_whitespace) + 1),
                        ),
                    )
                )
                del indent_stack[i]
            else:
                return None, [
                    [
                        error.error(
                            file_name,
                            parser_types.make_location(
                                (line_number, 1),
                                (line_number, len(leading_whitespace) + 1),
                            ),
                            "Bad indentation",
                        )
                    ]
                ]

        tokens.extend(line_tokens)

        # Append an end-of-line token (for non-whitespace lines).
        tokens.append(
            parser_types.Token(
                '"\\n"',
                "\n",
                parser_types.make_location(
                    (line_number, len(line) + 1), (line_number, len(line) + 1)
                ),
            )
        )
    for i in range(len(indent_stack) - 1):
        tokens.append(
            parser_types.Token(
                "Dedent",
                "",
                parser_types.make_location((line_number + 1, 1), (line_number + 1, 1)),
            )
        )
    return tokens, []


# Token patterns used by _tokenize_line.
LITERAL_TOKEN_PATTERNS = (
    "[ ] ( ) : = + - * . ? == != && || < > <= >= , "
    "$static_size_in_bits $is_statically_sized "
    "$max $present $upper_bound $lower_bound $next "
    "$size_in_bits $size_in_bytes "
    "$max_size_in_bits $max_size_in_bytes $min_size_in_bits $min_size_in_bytes "
    "$default struct bits enum external import as if let"
).split()
_T = collections.namedtuple("T", ["regex", "symbol"])
REGEX_TOKEN_PATTERNS = [
    # Words starting with variations of "emboss reserved" are reserved for
    # internal use by the Emboss compiler.
    _T(re.compile(r"EmbossReserved[A-Za-z0-9]*"), "BadWord"),
    _T(re.compile(r"emboss_reserved[_a-z0-9]*"), "BadWord"),
    _T(re.compile(r"EMBOSS_RESERVED[_A-Z0-9]*"), "BadWord"),
    _T(re.compile(r'"(?:[^"\n\\]|\\[n\\"])*"'), "String"),
    _T(re.compile("[0-9]+"), "Number"),
    _T(re.compile("[0-9]{1,3}(?:_[0-9]{3})*"), "Number"),
    _T(re.compile("0x[0-9a-fA-F]+"), "Number"),
    _T(re.compile("0x_?[0-9a-fA-F]{1,4}(?:_[0-9a-fA-F]{4})*"), "Number"),
    _T(re.compile("0x_?[0-9a-fA-F]{1,8}(?:_[0-9a-fA-F]{8})*"), "Number"),
    _T(re.compile("0b[01]+"), "Number"),
    _T(re.compile("0b_?[01]{1,4}(?:_[01]{4})*"), "Number"),
    _T(re.compile("0b_?[01]{1,8}(?:_[01]{8})*"), "Number"),
    _T(re.compile("true|false"), "BooleanConstant"),
    _T(re.compile("[a-z][a-z_0-9]*"), "SnakeWord"),
    # Single-letter ShoutyWords (like "A") and single-letter-followed-by-number
    # ShoutyWords ("A100") are disallowed due to ambiguity with CamelWords.  A
    # ShoutyWord must start with an upper case letter and contain at least one
    # more upper case letter or '_'.
    _T(re.compile("[A-Z][A-Z_0-9]*[A-Z_][A-Z_0-9]*"), "ShoutyWord"),
    # A CamelWord starts with A-Z and contains at least one a-z, and no _.
    _T(re.compile("[A-Z][a-zA-Z0-9]*[a-z][a-zA-Z0-9]*"), "CamelWord"),
    _T(re.compile("-- .*"), "Documentation"),
    _T(re.compile("--$"), "Documentation"),
    _T(re.compile("--.*"), "BadDocumentation"),
    _T(re.compile(r"\s+"), None),
    _T(re.compile("#.*"), "Comment"),
    # BadWord and BadNumber are a catch-alls for words and numbers so that
    # something like "abcDef" doesn't tokenize to [SnakeWord, CamelWord].
    #
    # This is preferable to returning an error because the BadWord and BadNumber
    # token types can be used in example-based errors.
    _T(re.compile("[0-9][bxBX]?[0-9a-fA-F_]*"), "BadNumber"),
    _T(re.compile("[a-zA-Z_$0-9]+"), "BadWord"),
]
del _T


def _tokenize_line(line, line_number, file_name):
    """Tokenizes a single line of input.

    Arguments:
      line: The line of text to tokenize.
      line_number: The line number (used when constructing token objects).
      file_name: The name of a file to use in errors.

    Returns:
      A tuple of:
        A list of token objects or None.
        A possibly-empty list of errors.
    """
    tokens = []
    offset = 0
    while offset < len(line):
        best_candidate = ""
        best_candidate_symbol = None
        # Find the longest match.  Ties go to the first match.  This way, keywords
        # ("struct") are matched as themselves, but words that only happen to start
        # with keywords ("structure") are matched as words.
        #
        # There is never a reason to try to match a literal after a regex that
        # could also match that literal, so check literals first.
        for literal in LITERAL_TOKEN_PATTERNS:
            if line[offset:].startswith(literal) and len(literal) > len(best_candidate):
                best_candidate = literal
                # For Emboss, the name of a literal token is just the literal in quotes,
                # so that the grammar can read a little more naturally, e.g.:
                #
                #     expression -> expression "+" expression
                #
                # instead of
                #
                #     expression -> expression Plus expression
                best_candidate_symbol = '"' + literal + '"'
        for pattern in REGEX_TOKEN_PATTERNS:
            match_result = pattern.regex.match(line[offset:])
            if match_result and len(match_result.group(0)) > len(best_candidate):
                best_candidate = match_result.group(0)
                best_candidate_symbol = pattern.symbol
        if not best_candidate:
            return None, [
                [
                    error.error(
                        file_name,
                        parser_types.make_location(
                            (line_number, offset + 1), (line_number, offset + 2)
                        ),
                        "Unrecognized token",
                    )
                ]
            ]
        if best_candidate_symbol:
            tokens.append(
                parser_types.Token(
                    best_candidate_symbol,
                    best_candidate,
                    parser_types.make_location(
                        (line_number, offset + 1),
                        (line_number, offset + len(best_candidate) + 1),
                    ),
                )
            )
        offset += len(best_candidate)
    return tokens, None
