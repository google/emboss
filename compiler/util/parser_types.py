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

"""Various types shared through multiple passes of parsing.

This module contains types used as interfaces between parts of the Emboss front
end.  These types do not really "belong" to either the producers or consumers,
and in a few cases placing them in one or the other creates unnecessary
dependencies, so they are defined here.
"""

import collections
from compiler.util import ir_data


def _make_position(line, column):
    """Makes an ir_data.Position from line, column ints."""
    if not isinstance(line, int):
        raise ValueError("Bad line {!r}".format(line))
    elif not isinstance(column, int):
        raise ValueError("Bad column {!r}".format(column))
    return ir_data.Position(line=line, column=column)


def _parse_position(text):
    """Parses an ir_data.Position from "line:column" (e.g., "1:2")."""
    line, column = text.split(":")
    return _make_position(int(line), int(column))


def format_position(position):
    """formats an ir_data.Position to "line:column" form."""
    return "{}:{}".format(position.line, position.column)


def make_location(start, end, is_synthetic=False):
    """Makes an ir_data.Location from (line, column) tuples or ir_data.Positions."""
    if isinstance(start, tuple):
        start = _make_position(*start)
    if isinstance(end, tuple):
        end = _make_position(*end)
    if not isinstance(start, ir_data.Position):
        raise ValueError("Bad start {!r}".format(start))
    elif not isinstance(end, ir_data.Position):
        raise ValueError("Bad end {!r}".format(end))
    elif start.line > end.line or (
        start.line == end.line and start.column > end.column
    ):
        raise ValueError(
            "Start {} is after end {}".format(
                format_position(start), format_position(end)
            )
        )
    return ir_data.Location(start=start, end=end, is_synthetic=is_synthetic)


def format_location(location):
    """Formats an ir_data.Location in format "1:2-3:4" ("start-end")."""
    return "{}-{}".format(
        format_position(location.start), format_position(location.end)
    )


def parse_location(text):
    """Parses an ir_data.Location from format "1:2-3:4" ("start-end")."""
    start, end = text.split("-")
    return make_location(_parse_position(start), _parse_position(end))


class Token(collections.namedtuple("Token", ["symbol", "text", "source_location"])):
    """A Token is a chunk of text from a source file, and a classification.

    Attributes:
      symbol: The name of this token ("Indent", "SnakeWord", etc.)
      text: The original text ("1234", "some_name", etc.)
      source_location: Where this token came from in the original source file.
    """

    def __str__(self):
        return "{} {} {}".format(
            self.symbol, repr(self.text), format_location(self.source_location)
        )


class Production(collections.namedtuple("Production", ["lhs", "rhs"])):
    """A Production is a simple production from a context-free grammar.

    A Production takes the form:

      nonterminal -> symbol*

    where "nonterminal" is an implicitly non-terminal symbol in the language,
    and "symbol*" is zero or more terminal or non-terminal symbols which form the
    non-terminal on the left.

    Attributes:
      lhs: The non-terminal symbol on the left-hand-side of the production.
      rhs: The sequence of symbols on the right-hand-side of the production.
    """

    def __str__(self):
        return str(self.lhs) + " -> " + " ".join([str(r) for r in self.rhs])

    @staticmethod
    def parse(production_text):
        """Parses a Production from a "symbol -> symbol symbol symbol" string."""
        words = production_text.split()
        if words[1] != "->":
            raise SyntaxError
        return Production(words[0], tuple(words[2:]))
