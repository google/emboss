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

"""Utility function to parse text into an ir_data.Expression."""

from compiler.front_end import module_ir
from compiler.front_end import parser
from compiler.front_end import tokenizer


def parse(text):
    """Parses text as an Expression.

    This parses text using the expression subset of the Emboss grammar, and
    returns an ir_data.Expression.  The expression only needs to be syntactically
    valid; it will not go through symbol resolution or type checking.  This
    function is not intended to be called on arbitrary input; it asserts that the
    text successfully parses, but does not return errors.

    Arguments:
      text: The text of an Emboss expression, like "4 + 5" or "$max(1, a, b)".

    Returns:
      An ir_data.Expression corresponding to the textual form.

    Raises:
      AssertionError if text is not a well-formed Emboss expression, and
      assertions are enabled.
    """
    tokens, errors = tokenizer.tokenize(text, "")
    assert not errors, "{!r}".format(errors)
    # tokenizer.tokenize always inserts a newline token at the end, which breaks
    # expression parsing.
    parse_result = parser.parse_expression(tokens[:-1])
    assert not parse_result.error, "{!r}".format(parse_result.error)
    return module_ir.build_ir(parse_result.parse_tree)
