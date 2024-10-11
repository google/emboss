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

"""Routines to load a shift-reduce parser for the module_ir module."""

import collections

from compiler.front_end.generated import cached_parser
from compiler.front_end import lr1
from compiler.front_end import make_parser
from compiler.front_end import module_ir
from compiler.util import parser_types
from compiler.util import simple_memoizer

ParserAndIsCached = collections.namedtuple(
    "ParserAndIsCached",
    [
        "parser",
        "cache_mismatch",
    ],
)


@simple_memoizer.memoize
def _load_module_parser():
    module_parser = cached_parser.module_parser()
    module_ir_productions = set(module_ir.PRODUCTIONS) | {
        parser_types.Production(lr1.START_PRIME, (module_ir.START_SYMBOL,))
    }
    if module_parser.productions == module_ir_productions:
        return ParserAndIsCached(module_parser, (set(), set()))
    return ParserAndIsCached(
        make_parser.build_module_parser(),
        (
            module_parser.productions - module_ir_productions,
            module_ir_productions - module_parser.productions,
        ),
    )


@simple_memoizer.memoize
def _load_expression_parser():
    expression_parser = cached_parser.expression_parser()
    module_ir_productions = set(module_ir.PRODUCTIONS) | {
        parser_types.Production(lr1.START_PRIME, (module_ir.EXPRESSION_START_SYMBOL,))
    }
    if expression_parser.productions == module_ir_productions:
        return ParserAndIsCached(
            expression_parser,
            (set(), set()),
        )
    return ParserAndIsCached(
        make_parser.build_expression_parser(),
        (
            expression_parser.productions - module_ir_productions,
            module_ir_productions - expression_parser.productions,
        ),
    )


def module_parser_cache_mismatch():
    return _load_module_parser().cache_mismatch


def module_parser():
    return _load_module_parser().parser
      

def parse_module(tokens):
    """Parses the provided Emboss token list into an Emboss module parse tree."""
    return _load_module_parser().parser.parse(tokens)


def parse_expression(tokens):
    """Parses the provided Emboss token list into an expression parse tree."""
    return _load_expression_parser().parser.parse(tokens)
