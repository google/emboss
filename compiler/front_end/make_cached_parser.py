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

import collections
import sys

from compiler.front_end import lr1
from compiler.front_end import parser
from compiler.util import parser_types


def as_py_source(parser, function_name):
    counter = [1]
    symbols = {}
    symbol_uses = {}
    symbol_rs = []
    reserved_identifiers = "P S R A E prods act got defa if in".split()
    header = []
    body = []
    header.append(
        f"def {function_name}():\n"  #
        " P = parser_types.Production\n"
        " S = lambda x: lr1.Shift(x, ())\n"
        " R = lr1.Reduce\n"
        " A = lr1.Accept\n"
        " E = lr1.Error\n"
    )

    def identifier(i):
        idleads = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        idchars = idleads + "0123456789_"
        header = idleads[i % len(idleads)]
        i //= len(idleads)
        while i:
            header += idchars[i % len(idchars)]
            i //= len(idchars)
        return header

    S = collections.namedtuple("S", "temp_ident")

    def sym(s):
        if s not in symbols:
            ident = S(counter[0])
            counter[0] += 1
            symbols[s] = ident
            symbol_uses[s] = 0
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
            symbol_rs.extend(r)
        symbol_uses[s] += 1
        return symbols[s]

    body.append(" prods = {\n")
    for production in parser.productions:
        body += ["  ", sym(production), ",\n"]
    body.append(" }\n")
    body.append(" got = {\n")
    for key_state in parser.goto:
        body.append(f"  {key_state}:" "{")
        goto_body = []
        for key_symbol, goto_state in parser.goto[key_state].items():
            body += [sym(key_symbol), f":{goto_state}", ","]
        del body[-1]
        body.append("},\n")
    body.append(" }\n")
    body.append(" act = {\n")
    for key_state in parser.action:
        body.append(f"  {key_state}:" "{")
        for key_symbol, value in parser.action[key_state].items():
            body += [sym(key_symbol), ":"]
            if isinstance(value, lr1.Shift):
                # The `items` are not used for actual parsing.
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
    body.append(" defe = {\n")
    for key, value in parser.default_errors.items():
        body += [f"  {key}:", sym(value), ",\n"]
    body.append(" }\n")
    body.append(
        " return lr1.Parser(\n"  #
        "  item_sets=None,\n"
        "  goto=got,\n"
        "  action=act,\n"
        f"  conflicts={repr(parser.conflicts)},\n"
        "  terminals=None,\n"
        "  nonterminals=None,\n"
        "  productions=prods,\n"
        "  default_errors=defe,\n"
        " )"
    )
    symbol_idents = {}
    ident_counter = 0
    for count, _, symbol in sorted(
        (-v, str(type(k)), k) for k, v in symbol_uses.items()
    ):
        while True:
            ident = identifier(ident_counter)
            ident_counter += 1
            if ident not in reserved_identifiers:
                break
        symbol_idents[symbols[symbol]] = ident
    for l in (symbol_rs, body):
        for i in range(len(l)):
            if isinstance(l[i], S):
                l[i] = symbol_idents[l[i]]
    return "".join(header + symbol_rs + body)


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

from compiler.front_end import lr1
from compiler.util import parser_types
""".strip()


def make_parser_file_text():
    module_parser = parser.build_module_parser()
    expression_parser = parser.build_expression_parser()
    return "\n".join(
        [
            _HEADER,
            as_py_source(module_parser, "module_parser"),
            as_py_source(expression_parser, "expression_parser"),
        ]
    )


def main(argv):
    print(make_parser_file_text())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
