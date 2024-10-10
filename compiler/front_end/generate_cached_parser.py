#!/usr/bin/python3
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

import keyword
import collections
import sys

from compiler.front_end import lr1
from compiler.front_end import make_parser
from compiler.util import parser_types


def _identifier(i):
    """Turns a number into a Python identifier.

    Does not account for reserved words: your code will need to do so.

    Args:
        i: the number to translate

    Returns:
        A Python identifier word.
    """
    idleads = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    idchars = idleads + "0123456789_"
    header = idleads[i % len(idleads)]
    i //= len(idleads)
    while i:
        header += idchars[i % len(idchars)]
        i //= len(idchars)
    return header


def as_py_source(parser, function_name):
    """Turns a Parser into Python source code.

    Returns a string that is a definition of a Python function that will
    recreate the given Parser, minus data that is only used for debugging.

    This function does some work to make the source smaller, but specifically
    does not do anything that would require real processing when the function
    runs, such as decompressing a text stream.

    Args:
        parser: the Parser to serialize
        function_name: the name of the function that should recreate `parser`

    Returns:
        Source to a Python function that recreates the given Parser.
    """
    header = [
        f"def {function_name}():\n"  #
        " P = parser_types.Production\n"
        " S = lambda x: lr1.Shift(x, ())\n"
        " R = lr1.Reduce\n"
        " A = lr1.Accept\n"
        " E = lr1.Error\n"
    ]
    body = []

    S = collections.namedtuple("S", "temp_ident")

    def declaration(ident, s):
        """Returns a declaration of s with symbol-based compression."""
        if isinstance(s, parser_types.Production):
            r = [" ", ident, "=P(", sym(s.lhs), ","]
            if len(s.rhs) == 0:
                r += ["()"]
            elif len(s.rhs) == 1:
                r += ["(", sym(s.rhs[0]), ",)"]
            else:
                r += ["("]
                for rhss in s.rhs:
                    r += [sym(rhss), ","]
                del r[-1]
                r += [")"]
            r += [")\n"]
        else:
            r = [" ", ident, "=", repr(s), "\n"]
        return r

    # Bookkkeeping for sym()
    counter = 0  # Next available ID.
    symbols = {}  # Map of object => S() placeholder
    symbol_uses = {}  # Map of object => count of uses
    symbol_defs = []  # Map of object => declaration (may have placeholders)

    def sym(s):
        """Returns a placeholder for s."""
        nonlocal counter
        if s not in symbols:
            ident = S(counter)
            counter += 1
            symbols[s] = ident
            symbol_uses[s] = 0
            symbol_defs.extend(declaration(ident, s))
        symbol_uses[s] += 1
        return symbols[s]

    # Serialize parser.productions.  This is only used to sanity check the
    # parser when it gets loaded: if the cached parser's production list does
    # not match the production list from module_ir at load time, the cached
    # parser will be ignored and a new parser will be generated at runtime.
    #
    # This is convenient when making changes to the Emboss grammar.
    body.append(" prods = {\n")
    for production in parser.productions:
        body += ["  ", sym(production), ",\n"]
    body.append(" }\n")

    # Serialize the GOTO table, one state per line.
    body.append(" goto = {\n")
    for key_state in sorted(parser.goto.keys()):
        body.append(f"  {key_state}:" "{")
        goto_body = []
        for key_symbol, goto_state in sorted(parser.goto[key_state].items()):
            body += [sym(key_symbol), f":{goto_state}", ","]
        del body[-1]
        body.append("},\n")
    body.append(" }\n")

    # Serialize the ACTION table, one state per line.
    body.append(" act = {\n")
    for key_state in sorted(parser.action.keys()):
        body.append(f"  {key_state}:" "{")
        for key_symbol, value in sorted(parser.action[key_state].items()):
            body += [sym(key_symbol), ":"]
            if isinstance(value, lr1.Shift):
                # The `items` are not used for actual parsing, so they are
                # discarded here.
                body.append(f"S({value.state})")
            elif isinstance(value, lr1.Reduce):
                body += ["R(", sym(value.rule), ")"]
            elif isinstance(value, lr1.Accept):
                body.append("A()")
            elif isinstance(value, lr1.Error):
                body += ["E(", sym(value.code), ")"]
            body.append(",")
        del body[-1]
        body.append("},\n")
    body.append(" }\n")

    # Serialize the default errors map.
    body.append(" defe = {\n")
    for key, value in sorted(parser.default_errors.items()):
        body += [f"  {key}:", sym(value), ",\n"]
    body.append(" }\n")

    # Finally, Parser construction.
    body.append(
        " return lr1.Parser(\n"  #
        "  item_sets=None,\n"
        "  goto=goto,\n"
        "  action=act,\n"
        f"  conflicts={repr(parser.conflicts)},\n"
        "  terminals=None,\n"
        "  nonterminals=None,\n"
        "  productions=prods,\n"
        "  default_errors=defe,\n"
        " )"
    )

    # Postprocess the output to swap the symbol placeholders for proper
    # symbols.
    #
    # Symbol assignment is done late (here) so that one-character symbols can
    # be used for the most frequently-reference objects.
    #
    # It would be possible to inline objects that are only used once, but there
    # do not seem to be very many of those, and it would be necessary to track
    # symbol definitions individually, instead of just concatenating them all
    # together in symbol_defs.
    symbol_idents = {}  # Map of placeholder => final identifier
    ident_counter = 0  # Counter used for generating identifiers
    reserved_identifiers = "P S R A E prods act goto defe".split()

    # Iterate through the symbols from most common to least common.
    for _, _, symbol in sorted(
        ((v, str(type(k)), k) for k, v in symbol_uses.items()), reverse=True
    ):
        # Find the next available identifier, skipping identifiers that are
        # used by the skeleton and identifiers that are actually Python
        # keywords.
        while True:
            ident = _identifier(ident_counter)
            ident_counter += 1
            if ident not in reserved_identifiers and not keyword.iskeyword(ident):
                break
        # Assign the final symbol to the placeholder.
        symbol_idents[symbols[symbol]] = ident

    # Iterate through the text fragments looking for any placeholders (S's),
    # and replace the placeholders with their final symbol.
    for l in (symbol_defs, body):
        for i in range(len(l)):
            if isinstance(l[i], S):
                l[i] = symbol_idents[l[i]]

    # Return the final result.
    return "".join(header + symbol_defs + body)


_HEADER = """
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

# GENERATED CODE.  DO NOT MANUALLY EDIT.  TO UPDATE, RUN:
#
#     bazel run //compiler/front_end:generate_cached_parser > compiler/front_end/generated/cached_parser.py

from compiler.front_end import lr1
from compiler.util import parser_types
""".strip()


def generate_parser_file_text():
    module_parser = make_parser.build_module_parser()
    expression_parser = make_parser.build_expression_parser()
    return "".join(
        [
            _HEADER,
            "\n",
            as_py_source(module_parser, "module_parser"),
            "\n",
            as_py_source(expression_parser, "expression_parser"),
            "\n",
        ]
    )


def main(argv):
    print(generate_parser_file_text(), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
