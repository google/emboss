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

"""Types related to the LR(1) parser.

This module contains types used by the LR(1) parser, which are also used in
other parts of the compiler: 

    SourcePosition: a position (zero-width) within a source file.
    SourceLocation: a span within a source file.
    Production: a grammar production.
    Token: a token; lr1.Parser operates on lists of tokens.
"""

import collections

PositionTuple = collections.namedtuple(
    "PositionTuple", ["line", "column"], defaults=[0, 0]
)


class SourcePosition(PositionTuple):
    """A zero-width position within a source file.

    Positions are 1-based (the first character of a source file is (1, 1)).

    The special value (0, 0) indicates a missing or unknown position, and is
    considered falsy.  All other values of SourcePosition are truthy.

    Attributes:
        line: the line within the source file; the first line is 1
        column: the column within the source line; the first character is 1
    """

    # This __new__ just adds asserts around PositionTuple.__new__, so it is
    # unnecessary when running under -O.
    if __debug__:
        def __new__(cls, /, line=0, column=0):
            assert isinstance(line, int), f"line {line} is not int"
            assert isinstance(column, int), f"column {column} is not int"
            assert line >= 0, f"line {line} is negative"
            assert column >= 0, f"column {column} is negative"
            assert (line == 0 and column == 0) or (
                line != 0 and column != 0
            ), f"Cannot have line {line} with column {column}"
            return PositionTuple.__new__(cls, line, column)

    def __str__(self):
        return f"{self.line}:{self.column}"

    @staticmethod
    def from_str(value):
        try:
            l, c = value.split(":")
            return SourcePosition(line=int(l.strip()), column=int(c.strip()))
        except Exception as e:
            raise ValueError(f"{repr(value)} is not a valid SourcePosition.")

    def __bool__(self):
        return bool(self.line)


LocationTuple = collections.namedtuple(
    "LocationTuple",
    ["start", "end", "is_disjoint_from_parent", "is_synthetic"],
    defaults=[SourcePosition(), SourcePosition(), False, False],
)


class SourceLocation(LocationTuple):
    """The source location of a node in the IR, as a half-open start:end range

    Attributes:
        start: the start of the range
        end: one character past the end of the range
        is_disjoint_from_parent: True if this SourceLocation may fall outside
            of the SourceLocation of the parent node
        is_synthetic: True if the associated node was generated from
            user-supplied source code, but is part of a construct that does not
            directly correspond to something that the user wrote (e.g., a
            generated virtual field that is assembled from fragments from
            elsewhere in the IR).

    SourceLocation is falsy if the start and end are falsy.
    """

    def __new__(
        cls,
        /,
        start=SourcePosition(),
        end=SourcePosition(),
        *,
        is_disjoint_from_parent=False,
        is_synthetic=False,
    ):
        if not isinstance(start, SourcePosition):
            start = SourcePosition(*start)
        if not isinstance(end, SourcePosition):
            end = SourcePosition(*end)
        assert start <= end, f"start {start} is after end {end}"
        assert (not start and not end) or (
            start and end
        ), "Cannot have have start {start} with end {end}"
        assert isinstance(
            is_disjoint_from_parent, bool
        ), f"is_disjoint_from_parent {is_disjoint_from_parent} is not bool"
        assert isinstance(
            is_synthetic, bool
        ), f"is_synthetic {is_synthetic} is not bool"
        return LocationTuple.__new__(
            cls, start, end, is_disjoint_from_parent, is_synthetic
        )

    def __str__(self):
        suffix = ""
        if self.is_disjoint_from_parent:
            suffix += "^"
        if self.is_synthetic:
            suffix += "*"
        return f"{self.start}-{self.end}{suffix}"

    @staticmethod
    def from_str(value):
        original_value = value
        try:
            is_synthetic = False
            if value[-1] == "*":
                is_synthetic = True
                value = value[:-1]
            is_disjoint_from_parent = False
            if value[-1] == "^":
                is_disjoint_from_parent = True
                value = value[:-1]
            start, end = value.split("-")
            return SourceLocation(
                start=SourcePosition.from_str(start),
                end=SourcePosition.from_str(end),
                is_synthetic=is_synthetic,
                is_disjoint_from_parent=is_disjoint_from_parent,
            )
        except Exception as e:
            raise ValueError(f"{repr(original_value)} is not a valid SourceLocation.")

    def __bool__(self):
        # Should this check is_synthetic and is_disjoint_from_parent as well?
        return bool(self.start)


def merge_source_locations(*nodes):
    locations = [
        node.source_location
        for node in nodes
        if hasattr(node, "source_location") and node.source_location
    ]
    if not locations:
        return None
    start = locations[0].start
    end = locations[-1].end
    is_synthetic = any(l.is_synthetic for l in locations)
    is_disjoint_from_parent = any(l.is_disjoint_from_parent for l in locations)
    return SourceLocation(
        start=start,
        end=end,
        is_synthetic=is_synthetic,
        is_disjoint_from_parent=is_disjoint_from_parent,
    )


class Token(collections.namedtuple("Token", ["symbol", "text", "source_location"])):
    """A Token is a chunk of text from a source file, and a classification.

    Attributes:
      symbol: The name of this token ("Indent", "SnakeWord", etc.)
      text: The original text ("1234", "some_name", etc.)
      source_location: Where this token came from in the original source file.
    """

    def __str__(self):
        return "{} {} {}".format(
            self.symbol, repr(self.text), str(self.source_location)
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
