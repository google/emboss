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

"""Routines to generate a shift-reduce parser from the module_ir module."""

from compiler.front_end import lr1
from compiler.front_end import module_ir
from compiler.front_end import tokenizer
from compiler.util import parser_types
from compiler.util import resources
from compiler.util import simple_memoizer


class ParserGenerationError(Exception):
    """An error occurred during parser generation."""

    pass


def parse_error_examples(error_example_text):
    """Parses error examples from error_example_text.

    Arguments:
      error_example_text: The text of an error example file.

    Returns:
      A list of tuples, suitable for passing into generate_parser.

    Raises:
      ParserGenerationError: There is a problem parsing the error examples.
    """
    error_examples = error_example_text.split("\n" + "=" * 80 + "\n")
    result = []
    # Everything before the first "======" line is explanatory text: ignore it.
    for error_example in error_examples[1:]:
        message_and_examples = error_example.split("\n" + "-" * 80 + "\n")
        if len(message_and_examples) != 2:
            raise ParserGenerationError(
                "Expected one error message and one example section in:\n"
                + error_example
            )
        message, example_text = message_and_examples
        examples = example_text.split("\n---\n")
        for example in examples:
            # TODO(bolms): feed a line number into tokenize, so that tokenization
            # failures refer to the correct line within error_example_text.
            tokens, errors = tokenizer.tokenize(example, "")
            if errors:
                raise ParserGenerationError(str(errors))

            for i in range(len(tokens)):
                if tokens[i].symbol == "BadWord" and tokens[i].text == "$ANY":
                    tokens[i] = lr1.ANY_TOKEN

            error_token = None
            for i in range(len(tokens)):
                if tokens[i].symbol == "BadWord" and tokens[i].text == "$ERR":
                    error_token = tokens[i + 1]
                    del tokens[i]
                    break
            else:
                raise ParserGenerationError(
                    "No error token marker '$ERR' in:\n" + error_example
                )

            result.append((tokens, error_token, message.strip(), example))
    return result


def generate_parser(start_symbol, productions, error_examples):
    """Generates a parser from grammar, and applies error_examples.

    Arguments:
        start_symbol: the start symbol of the grammar (a string)
        productions: a list of parser_types.Production in the grammar
        error_examples: A list of (source tokens, error message, source text)
            tuples.

    Returns:
        A parser.

    Raises:
        ParserGenerationError: There is a problem generating the parser.
    """
    parser = lr1.Grammar(start_symbol, productions).parser()
    if parser.conflicts:
        raise ParserGenerationError("\n".join([str(c) for c in parser.conflicts]))
    for example in error_examples:
        mark_result = parser.mark_error(example[0], example[1], example[2])
        if mark_result:
            raise ParserGenerationError(
                "error marking example: {}\nExample:\n{}".format(
                    mark_result, example[3]
                )
            )
    return parser


def build_module_parser():
    """Constructs a new Parser for an Emboss module (complete source file)."""
    error_examples = parse_error_examples(
        resources.load("compiler.front_end", "error_examples")
    )
    return generate_parser(
        module_ir.START_SYMBOL, sorted(module_ir.PRODUCTIONS), error_examples
    )


def build_expression_parser():
    """Constructs a new Parser for an Emboss expression."""
    return generate_parser(
        module_ir.EXPRESSION_START_SYMBOL, sorted(module_ir.PRODUCTIONS), []
    )
