# Copyright 2026 Google LLC
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

"""Renders an `ir_data.Expression` back to Emboss source text.

This is the inverse of `compiler.util.expression_parser.parse`: the text it
produces re-parses to an equivalent expression.  Back ends that report
expressions to a human -- documentation, reflection metadata -- want the
expression the way the author wrote it, not the way a target language spells
it, which is what `back_end/cpp/header_generator.py` produces.

Parentheses are emitted only where the Emboss grammar requires them.
"""

from compiler.util import ir_data

# Binding strength of each operator, loosest to tightest.  Atoms bind tighter
# than anything, so they are never parenthesized.
_CHOICE_PRECEDENCE = 1
_BOOLEAN_PRECEDENCE = 2
_COMPARISON_PRECEDENCE = 3
_ADDITIVE_PRECEDENCE = 4
_MULTIPLICATIVE_PRECEDENCE = 5
_NEGATION_PRECEDENCE = 6
_ATOM_PRECEDENCE = 7

_PRECEDENCES = {
    ir_data.FunctionMapping.CHOICE: _CHOICE_PRECEDENCE,
    ir_data.FunctionMapping.OR: _BOOLEAN_PRECEDENCE,
    ir_data.FunctionMapping.AND: _BOOLEAN_PRECEDENCE,
    ir_data.FunctionMapping.EQUALITY: _COMPARISON_PRECEDENCE,
    ir_data.FunctionMapping.INEQUALITY: _COMPARISON_PRECEDENCE,
    ir_data.FunctionMapping.LESS: _COMPARISON_PRECEDENCE,
    ir_data.FunctionMapping.LESS_OR_EQUAL: _COMPARISON_PRECEDENCE,
    ir_data.FunctionMapping.GREATER: _COMPARISON_PRECEDENCE,
    ir_data.FunctionMapping.GREATER_OR_EQUAL: _COMPARISON_PRECEDENCE,
    ir_data.FunctionMapping.ADDITION: _ADDITIVE_PRECEDENCE,
    ir_data.FunctionMapping.SUBTRACTION: _ADDITIVE_PRECEDENCE,
    ir_data.FunctionMapping.MULTIPLICATION: _MULTIPLICATIVE_PRECEDENCE,
}

# Operators written between their two arguments.
_INFIX_OPERATORS = {
    ir_data.FunctionMapping.ADDITION: "+",
    ir_data.FunctionMapping.SUBTRACTION: "-",
    ir_data.FunctionMapping.MULTIPLICATION: "*",
    ir_data.FunctionMapping.EQUALITY: "==",
    ir_data.FunctionMapping.INEQUALITY: "!=",
    ir_data.FunctionMapping.AND: "&&",
    ir_data.FunctionMapping.OR: "||",
    ir_data.FunctionMapping.LESS: "<",
    ir_data.FunctionMapping.LESS_OR_EQUAL: "<=",
    ir_data.FunctionMapping.GREATER: ">",
    ir_data.FunctionMapping.GREATER_OR_EQUAL: ">=",
}

# Operators written as `$name(arg, ...)`.
_CALL_OPERATORS = {
    ir_data.FunctionMapping.MAXIMUM: "$max",
    ir_data.FunctionMapping.PRESENCE: "$present",
    ir_data.FunctionMapping.UPPER_BOUND: "$upper_bound",
    ir_data.FunctionMapping.LOWER_BOUND: "$lower_bound",
}

# `&&` and `||` may not be mixed without parentheses: the grammar derives
# `and-expression` and `or-expression` as siblings, each from
# `comparison-expression`.  Chains of one operator are fine.
_BOOLEAN_OPERATORS = frozenset(
    {ir_data.FunctionMapping.AND, ir_data.FunctionMapping.OR}
)

# Comparisons do not re-associate, so a comparison inside a comparison is
# always parenthesized.
_COMPARISON_OPERATORS = frozenset(
    {
        ir_data.FunctionMapping.EQUALITY,
        ir_data.FunctionMapping.INEQUALITY,
        ir_data.FunctionMapping.LESS,
        ir_data.FunctionMapping.LESS_OR_EQUAL,
        ir_data.FunctionMapping.GREATER,
        ir_data.FunctionMapping.GREATER_OR_EQUAL,
    }
)


def render(expression):
    """Renders `expression` as Emboss source text.

    Arguments:
      expression: an `ir_data.Expression`.

    Returns:
      A string which parses back to an equivalent expression.

    Raises:
      ValueError: if `expression` has no value set.
    """
    return _render(expression)[0]


def _render(expression):
    """Returns (text, precedence, operator) for `expression`.

    `operator` is the `FunctionMapping` at the root of `expression`, or None if
    the root is not a function.
    """
    which = expression.which_expression
    if which == "constant":
        return expression.constant.value, _ATOM_PRECEDENCE, None
    if which == "boolean_constant":
        return (
            "true" if expression.boolean_constant.value else "false",
            _ATOM_PRECEDENCE,
            None,
        )
    if which == "constant_reference":
        return _render_reference(expression.constant_reference), _ATOM_PRECEDENCE, None
    if which == "builtin_reference":
        return _render_reference(expression.builtin_reference), _ATOM_PRECEDENCE, None
    if which == "field_reference":
        return (
            ".".join(
                _render_reference(reference)
                for reference in expression.field_reference.path
            ),
            _ATOM_PRECEDENCE,
            None,
        )
    if which == "function":
        return _render_function(expression.function)
    raise ValueError("Expression has no value set.")


def _render_reference(reference):
    """Renders a Reference the way it was written, if that is recorded."""
    if reference.source_name:
        return ".".join(word.text for word in reference.source_name)
    # Synthetic references carry no source name; fall back to the absolute name.
    return ".".join(reference.canonical_name.object_path)


def _is_phantom_zero(expression):
    """True if `expression` is the implicit 0 the parser adds to unary +/-.

    `-x` is parsed as `0 - x` (`module_ir._negation_expression_with_operator`),
    with a zero-width source location on the inserted constant.  A `0` the
    author actually typed spans at least one column.
    """
    if expression.which_expression != "constant":
        return False
    if expression.constant.value != "0":
        return False
    location = expression.source_location
    if location is None or location.start is None or location.end is None:
        return False
    return location.start == location.end


def _render_function(function):
    """Returns (text, precedence, operator) for a Function."""
    operator = function.function
    arguments = list(function.args)

    if operator in _CALL_OPERATORS:
        rendered = ", ".join(render(argument) for argument in arguments)
        return f"{_CALL_OPERATORS[operator]}({rendered})", _ATOM_PRECEDENCE, None

    if operator == ir_data.FunctionMapping.CHOICE:
        condition, if_true, if_false = arguments
        # `?:` may not chain, and its three parts are `logical-expression`s, so
        # any `?:` argument needs parentheses.
        floor = _CHOICE_PRECEDENCE + 1
        return (
            "{} ? {} : {}".format(
                _parenthesize(condition, floor, operator),
                _parenthesize(if_true, floor, operator),
                _parenthesize(if_false, floor, operator),
            ),
            _CHOICE_PRECEDENCE,
            operator,
        )

    if (
        operator
        in (ir_data.FunctionMapping.SUBTRACTION, ir_data.FunctionMapping.ADDITION)
        and len(arguments) == 2
        and _is_phantom_zero(arguments[0])
    ):
        sign = "-" if operator == ir_data.FunctionMapping.SUBTRACTION else "+"
        # Unary +/- takes a `bottom-expression`: an atom or a parenthesized
        # expression, nothing looser.
        operand = _parenthesize(arguments[1], _ATOM_PRECEDENCE, operator)
        return f"{sign}{operand}", _NEGATION_PRECEDENCE, None

    if operator in _INFIX_OPERATORS and len(arguments) == 2:
        precedence = _PRECEDENCES[operator]
        left, right = arguments
        # These operators are left-associative, so `a - b - c` is `(a - b) - c`:
        # a same-precedence *right* argument has to be parenthesized to survive
        # a round trip.  Comparisons do not re-associate at all.
        if operator in _COMPARISON_OPERATORS:
            left_floor = precedence + 1
        else:
            left_floor = precedence
        return (
            "{} {} {}".format(
                _parenthesize(left, left_floor, operator),
                _INFIX_OPERATORS[operator],
                _parenthesize(right, precedence + 1, operator),
            ),
            precedence,
            operator,
        )

    # An operator the printer does not know: fall back to the source spelling,
    # which the front end records for every function it builds.
    name = function.function_name.text if function.function_name else "?"
    rendered = ", ".join(render(argument) for argument in arguments)
    return f"{name}({rendered})", _ATOM_PRECEDENCE, None


def _parenthesize(expression, floor, parent_operator):
    """Renders `expression`, adding `()` only where the grammar needs them."""
    text, precedence, operator = _render(expression)
    if precedence < floor:
        return f"({text})"
    if (
        parent_operator in _BOOLEAN_OPERATORS
        and operator in _BOOLEAN_OPERATORS
        and operator != parent_operator
    ):
        return f"({text})"
    return text
