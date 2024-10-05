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

"""module_ir contains code for generating module-level IRs from parse trees.

The primary export is build_ir(), which takes a parse tree (as returned by a
parser from lr1.py), and returns a module-level intermediate representation
("module IR").

This module also notably exports PRODUCTIONS and START_SYMBOL, which should be
fed to lr1.Grammar in order to create a parser for the Emboss language.
"""

import re
import sys

from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import name_conversion
from compiler.util import parser_types


# Intermediate types; should not be found in the final IR.
class _List(object):
    """A list with source location information."""

    __slots__ = ("list", "source_location")

    def __init__(self, l):
        assert isinstance(l, list), "_List object must wrap list, not '%r'" % l
        self.list = l
        self.source_location = ir_data.Location()


class _ExpressionTail(object):
    """A fragment of an expression with an operator and right-hand side.

    _ExpressionTail is the tail of an expression, consisting of an operator and
    the right-hand argument to the operator; for example, in the expression (6+8),
    the _ExpressionTail would be "+8".

    This is used as a temporary object while converting the right-recursive
    "expression" and "times-expression" productions into left-associative
    Expressions.

    Attributes:
      operator: An ir_data.Word of the operator's name.
      expression: The expression on the right side of the operator.
      source_location: The source location of the operation fragment.
    """

    __slots__ = ("operator", "expression", "source_location")

    def __init__(self, operator, expression):
        self.operator = operator
        self.expression = expression
        self.source_location = ir_data.Location()


class _FieldWithType(object):
    """A field with zero or more types defined inline with that field."""

    __slots__ = ("field", "subtypes", "source_location")

    def __init__(self, field, subtypes=None):
        self.field = field
        self.subtypes = subtypes or []
        self.source_location = ir_data.Location()


def build_ir(parse_tree, used_productions=None):
    r"""Builds a module-level intermediate representation from a valid parse tree.

  The parse tree is precisely dictated by the exact productions in the grammar
  used by the parser, with no semantic information.  _really_build_ir transforms
  this "raw" form into a stable, cooked representation, thereby isolating
  subsequent steps from the exact details of the grammar.

  (Probably incomplete) list of transformations:

  *   ParseResult and Token nodes are replaced with Module, Attribute, Struct,
      Type, etc. objects.

  *   Purely syntactic tokens ('"["', '"struct"', etc.) are discarded.

  *   Repeated elements are transformed from tree form to list form:

          a*
         / \
        b   a*
           / \
          c   a*
             / \
            d   a*

      (where b, c, and d are nodes of type "a") becomes [b, c, d].

  *   The values of numeric constants (Number, etc. tokens) are parsed.

  *   Different classes of names (snake_names, CamelNames, ShoutyNames) are
      folded into a single "Name" type, since they are guaranteed to appear in
      the correct places in the parse tree.


  Arguments:
    parse_tree: A parse tree.  Each leaf node should be a parser_types.Token
      object, and each non-leaf node should have a 'symbol' attribute specifying
      which grammar symbol it represents, and a 'children' attribute containing
      a list of child nodes.  This is the format returned by the parsers
      produced by the lr1 module, when run against tokens from the tokenizer
      module.
    used_productions: If specified, used_productions.add() will be called with
      each production actually used in parsing.  This can be useful when
      developing the grammar and writing tests; in particular, it can be used to
      figure out which productions are *not* used when parsing a particular
      file.

  Returns:
    A module-level intermediate representation (module IR) for an Emboss module
    (source file).  This IR will not have symbols resolved; that must be done on
    a forest of module IRs so that names from other modules can be resolved.
  """

    # TODO(b/140259131): Refactor _really_build_ir to be less recursive/use an
    # explicit stack.
    old_recursion_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(16 * 1024)  # ~8000 top-level entities in one module.
    try:
        result = _really_build_ir(parse_tree, used_productions)
    finally:
        sys.setrecursionlimit(old_recursion_limit)
    return result


def _really_build_ir(parse_tree, used_productions):
    """Real implementation of build_ir()."""
    if used_productions is None:
        used_productions = set()
    if hasattr(parse_tree, "children"):
        parsed_children = [
            _really_build_ir(child, used_productions) for child in parse_tree.children
        ]
        used_productions.add(parse_tree.production)
        result = _handlers[parse_tree.production](*parsed_children)
        if parse_tree.source_location is not None:
            if result.source_location:
                ir_data_utils.update(result.source_location, parse_tree.source_location)
            else:
                result.source_location = ir_data_utils.copy(parse_tree.source_location)
        return result
    else:
        # For leaf nodes, the temporary "IR" is just the token.  Higher-level rules
        # will translate it to a real IR.
        assert isinstance(parse_tree, parser_types.Token), str(parse_tree)
        return parse_tree


# Map of productions to their handlers.
_handlers = {}

_anonymous_name_counter = 0


def _get_anonymous_field_name():
    global _anonymous_name_counter
    _anonymous_name_counter += 1
    return "emboss_reserved_anonymous_field_{}".format(_anonymous_name_counter)


def _handles(production_text):
    """_handles marks a function as the handler for a particular production."""
    production = parser_types.Production.parse(production_text)

    def handles(f):
        _handlers[production] = f
        return f

    return handles


def _make_prelude_import(position):
    """Helper function to construct a synthetic ir_data.Import for the prelude."""
    location = parser_types.make_location(position, position)
    return ir_data.Import(
        file_name=ir_data.String(text="", source_location=location),
        local_name=ir_data.Word(text="", source_location=location),
        source_location=location,
    )


def _text_to_operator(text):
    """Converts an operator's textual name to its corresponding enum."""
    operations = {
        "+": ir_data.FunctionMapping.ADDITION,
        "-": ir_data.FunctionMapping.SUBTRACTION,
        "*": ir_data.FunctionMapping.MULTIPLICATION,
        "==": ir_data.FunctionMapping.EQUALITY,
        "!=": ir_data.FunctionMapping.INEQUALITY,
        "&&": ir_data.FunctionMapping.AND,
        "||": ir_data.FunctionMapping.OR,
        ">": ir_data.FunctionMapping.GREATER,
        ">=": ir_data.FunctionMapping.GREATER_OR_EQUAL,
        "<": ir_data.FunctionMapping.LESS,
        "<=": ir_data.FunctionMapping.LESS_OR_EQUAL,
    }
    return operations[text]


def _text_to_function(text):
    """Converts a function's textual name to its corresponding enum."""
    functions = {
        "$max": ir_data.FunctionMapping.MAXIMUM,
        "$present": ir_data.FunctionMapping.PRESENCE,
        "$upper_bound": ir_data.FunctionMapping.UPPER_BOUND,
        "$lower_bound": ir_data.FunctionMapping.LOWER_BOUND,
    }
    return functions[text]


################################################################################
# Grammar & parse tree to IR translation.
#
# From here to (almost) the end of the file are functions which recursively
# build an IR.  The @_handles annotations indicate the exact grammar
# production(s) handled by each function.  The handler function should take
# exactly one argument for each symbol in the production's RHS.
#
# The actual Emboss grammar is extracted directly from the @_handles
# annotations, so this is also the grammar definition.  For convenience, the
# grammar can be viewed separately in g3doc/grammar.md.
#
# At the end, symbols whose names end in "*", "+", or "?" are extracted from the
# grammar, and appropriate productions are added for zero-or-more, one-or-more,
# or zero-or-one lists, respectively.  (This is analogous to the *, +, and ?
# operators in regex.)  It is necessary for this to happen here (and not in
# lr1.py) because the generated productions must be associated with
# IR-generation functions.


# A module file is a list of documentation, then imports, then top-level
# attributes, then type definitions.  Any section may be missing.
# TODO(bolms): Should Emboss disallow completely empty files?
@_handles(
    "module -> comment-line* doc-line* import-line* attribute-line*"
    "          type-definition*"
)
def _file(leading_newlines, docs, imports, attributes, type_definitions):
    """Assembles the top-level IR for a module."""
    del leading_newlines  # Unused.
    # Figure out the best synthetic source_location for the synthesized prelude
    # import.
    if imports.list:
        position = imports.list[0].source_location.start
    elif docs.list:
        position = docs.list[0].source_location.end
    elif attributes.list:
        position = attributes.list[0].source_location.start
    elif type_definitions.list:
        position = type_definitions.list[0].source_location.start
    else:
        position = 1, 1

    # If the source file is completely empty, build_ir won't automatically
    # populate the source_location attribute for the module.
    if (
        not docs.list
        and not imports.list
        and not attributes.list
        and not type_definitions.list
    ):
        module_source_location = parser_types.make_location((1, 1), (1, 1))
    else:
        module_source_location = None

    return ir_data.Module(
        documentation=docs.list,
        foreign_import=[_make_prelude_import(position)] + imports.list,
        attribute=attributes.list,
        type=type_definitions.list,
        source_location=module_source_location,
    )


@_handles("import-line ->" '    "import" string-constant "as" snake-word Comment? eol')
def _import(import_, file_name, as_, local_name, comment, eol):
    del import_, as_, comment, eol  # Unused
    return ir_data.Import(file_name=file_name, local_name=local_name)


@_handles("doc-line -> doc Comment? eol")
def _doc_line(doc, comment, eol):
    del comment, eol  # Unused.
    return doc


@_handles("doc -> Documentation")
def _doc(documentation):
    # As a special case, an empty documentation string may omit the trailing
    # space.
    if documentation.text == "--":
        doc_text = "-- "
    else:
        doc_text = documentation.text
    assert doc_text[0:3] == "-- ", "Documentation token '{}' in unknown format.".format(
        documentation.text
    )
    return ir_data.Documentation(text=doc_text[3:])


# A attribute-line is just a attribute on its own line.
@_handles("attribute-line -> attribute Comment? eol")
def _attribute_line(attr, comment, eol):
    del comment, eol  # Unused.
    return attr


# A attribute is [name = value].
@_handles(
    'attribute -> "[" attribute-context? "$default"?'
    '             snake-word ":" attribute-value "]"'
)
def _attribute(
    open_bracket,
    context_specifier,
    default_specifier,
    name,
    colon,
    attribute_value,
    close_bracket,
):
    """Assembles an attribute IR node."""
    del open_bracket, colon, close_bracket  # Unused.
    if context_specifier.list:
        return ir_data.Attribute(
            name=name,
            value=attribute_value,
            is_default=bool(default_specifier.list),
            back_end=context_specifier.list[0],
        )
    else:
        return ir_data.Attribute(
            name=name, value=attribute_value, is_default=bool(default_specifier.list)
        )


@_handles('attribute-context -> "(" snake-word ")"')
def _attribute_context(open_paren, context_name, close_paren):
    del open_paren, close_paren  # Unused.
    return context_name


@_handles("attribute-value -> expression")
def _attribute_value_expression(expression):
    return ir_data.AttributeValue(expression=expression)


@_handles("attribute-value -> string-constant")
def _attribute_value_string(string):
    return ir_data.AttributeValue(string_constant=string)


@_handles("boolean-constant -> BooleanConstant")
def _boolean_constant(boolean):
    return ir_data.BooleanConstant(value=(boolean.text == "true"))


@_handles("string-constant -> String")
def _string_constant(string):
    """Turns a String token into an ir_data.String, with proper unescaping.

    Arguments:
      string: A String token.

    Returns:
      An ir_data.String with the "text" field set to the unescaped value of
      string.text.
    """
    # TODO(bolms): If/when this logic becomes more complex (e.g., to handle \NNN
    # or \xNN escapes), extract this into a separate module with separate tests.
    assert string.text[0] == '"'
    assert string.text[-1] == '"'
    assert len(string.text) >= 2
    result = []
    for substring in re.split(r"(\\.)", string.text[1:-1]):
        if substring and substring[0] == "\\":
            assert len(substring) == 2
            result.append({"\\": "\\", '"': '"', "n": "\n"}[substring[1]])
        else:
            result.append(substring)
    return ir_data.String(text="".join(result))


# In Emboss, '&&' and '||' may not be mixed without parentheses.  These are all
# fine:
#
#     x && y && z
#     x || y || z
#     (x || y) && z
#     x || (y && z)
#
# These are syntax errors:
#
#     x || y && z
#     x && y || z
#
# This is accomplished by making && and || separate-but-equal in the precedence
# hierarchy.  Instead of the more traditional:
#
#     logical-expression   -> or-expression
#     or-expression        -> and-expression or-expression-right*
#     or-expression-right  -> '||' and-expression
#     and-expression       -> equality-expression and-expression-right*
#     and-expression-right -> '&&' equality-expression
#
# Or, using yacc-style precedence specifiers:
#
#     %left "||"
#     %left "&&"
#     expression -> expression
#                 | expression '||' expression
#                 | expression '&&' expression
#
# Emboss uses a slightly more complex grammar, in which '&&' and '||' are
# parallel, but unmixable:
#
#     logical-expression   -> and-expression
#                           | or-expression
#                           | equality-expression
#     or-expression        -> equality-expression or-expression-right+
#     or-expression-right  -> '||' equality-expression
#     and-expression       -> equality-expression and-expression-right+
#     and-expression-right -> '&&' equality-expression
#
# In either case, explicit parenthesization is handled elsewhere in the grammar.
@_handles("logical-expression -> and-expression")
@_handles("logical-expression -> or-expression")
@_handles("logical-expression -> comparison-expression")
@_handles("choice-expression -> logical-expression")
@_handles("expression -> choice-expression")
def _expression(expression):
    return expression


# The `logical-expression`s here means that ?: can't be chained without
# parentheses.  `x < 0 ? -1 : (x == 0 ? 0 : 1)` is OK, but `x < 0 ? -1 : x == 0
# ? 0 : 1` is not.  Parentheses are also needed in the middle: `x <= 0 ? x < 0 ?
# -1 : 0 : 1` is not syntactically valid.
@_handles(
    'choice-expression -> logical-expression "?" logical-expression'
    '                                        ":" logical-expression'
)
def _choice_expression(condition, question, if_true, colon, if_false):
    """Constructs an IR node for a choice operator (`?:`) expression."""
    location = parser_types.make_location(
        condition.source_location.start, if_false.source_location.end
    )
    operator_location = parser_types.make_location(
        question.source_location.start, colon.source_location.end
    )
    # The function_name is a bit weird, but should suffice for any error
    # messages that might need it.
    return ir_data.Expression(
        function=ir_data.Function(
            function=ir_data.FunctionMapping.CHOICE,
            args=[condition, if_true, if_false],
            function_name=ir_data.Word(text="?:", source_location=operator_location),
            source_location=location,
        )
    )


@_handles("comparison-expression -> additive-expression")
def _no_op_comparative_expression(expression):
    return expression


@_handles(
    "comparison-expression ->"
    "    additive-expression inequality-operator additive-expression"
)
def _comparative_expression(left, operator, right):
    location = parser_types.make_location(
        left.source_location.start, right.source_location.end
    )
    return ir_data.Expression(
        function=ir_data.Function(
            function=_text_to_operator(operator.text),
            args=[left, right],
            function_name=operator,
            source_location=location,
        )
    )


@_handles("additive-expression -> times-expression additive-expression-right*")
@_handles("times-expression -> negation-expression times-expression-right*")
@_handles("and-expression -> comparison-expression and-expression-right+")
@_handles("or-expression -> comparison-expression or-expression-right+")
def _binary_operator_expression(expression, expression_right):
    """Builds the IR for a chain of equal-precedence left-associative operations.

    _binary_operator_expression transforms a right-recursive list of expression
    tails into a left-associative Expression tree.  For example, given the
    arguments:

        6, (Tail("+", 7), Tail("-", 8), Tail("+", 10))

    _expression produces a structure like:

       Expression(Expression(Expression(6, "+", 7), "-", 8), "+", 10)

    This transformation is necessary because strict LR(1) grammars do not allow
    left recursion.

    Note that this method is used for several productions; each of those
    productions handles a different precedence level, but are identical in form.

    Arguments:
      expression: An ir_data.Expression which is the head of the (expr, operator,
          expr, operator, expr, ...) list.
      expression_right: A list of _ExpressionTails corresponding to the (operator,
          expr, operator, expr, ...) list that comes after expression.

    Returns:
      An ir_data.Expression with the correct recursive structure to represent a
      list of left-associative operations.
    """
    e = expression
    for right in expression_right.list:
        location = parser_types.make_location(
            e.source_location.start, right.source_location.end
        )
        e = ir_data.Expression(
            function=ir_data.Function(
                function=_text_to_operator(right.operator.text),
                args=[e, right.expression],
                function_name=right.operator,
                source_location=location,
            ),
            source_location=location,
        )
    return e


@_handles(
    "comparison-expression ->" "    additive-expression equality-expression-right+"
)
@_handles(
    "comparison-expression ->" "    additive-expression less-expression-right-list"
)
@_handles(
    "comparison-expression ->" "    additive-expression greater-expression-right-list"
)
def _chained_comparison_expression(expression, expression_right):
    """Builds the IR for a chain of comparisons, like a == b == c.

    Like _binary_operator_expression, _chained_comparison_expression transforms a
    right-recursive list of expression tails into a left-associative Expression
    tree.  Unlike _binary_operator_expression, extra AND nodes are added.  For
    example, the following expression:

        0 <= b <= 64

    must be translated to the conceptually-equivalent expression:

        0 <= b && b <= 64

    (The middle subexpression is duplicated -- this would be a problem in a
    programming language like C where expressions like `x++` have side effects,
    but side effects do not make sense in a data definition language like Emboss.)

    _chained_comparison_expression receives a left-hand head expression and a list
    of tails, like:

        6, (Tail("<=", b), Tail("<=", 64))

    which it translates to a structure like:

        Expression(Expression(6, "<=", b), "&&", Expression(b, "<=", 64))

    The Emboss grammar is constructed such that sequences of "<", "<=", and "=="
    comparisons may be chained, and sequences of ">", ">=", and "==" can be
    chained, but greater and less-than comparisons may not; e.g., "b < 64 > a" is
    not allowed.

    Arguments:
      expression: An ir_data.Expression which is the head of the (expr, operator,
          expr, operator, expr, ...) list.
      expression_right: A list of _ExpressionTails corresponding to the (operator,
          expr, operator, expr, ...) list that comes after expression.

    Returns:
      An ir_data.Expression with the correct recursive structure to represent a
      chain of left-associative comparison operations.
    """
    sequence = [expression]
    for right in expression_right.list:
        sequence.append(right.operator)
        sequence.append(right.expression)
    comparisons = []
    for i in range(0, len(sequence) - 1, 2):
        left, operator, right = sequence[i : i + 3]
        location = parser_types.make_location(
            left.source_location.start, right.source_location.end
        )
        comparisons.append(
            ir_data.Expression(
                function=ir_data.Function(
                    function=_text_to_operator(operator.text),
                    args=[left, right],
                    function_name=operator,
                    source_location=location,
                ),
                source_location=location,
            )
        )
    e = comparisons[0]
    for comparison in comparisons[1:]:
        location = parser_types.make_location(
            e.source_location.start, comparison.source_location.end
        )
        e = ir_data.Expression(
            function=ir_data.Function(
                function=ir_data.FunctionMapping.AND,
                args=[e, comparison],
                function_name=ir_data.Word(
                    text="&&",
                    source_location=comparison.function.args[0].source_location,
                ),
                source_location=location,
            ),
            source_location=location,
        )
    return e


# _chained_comparison_expression, above, handles three types of chains: `a == b
# == c`, `a < b <= c`, and `a > b >= c`.
#
# This requires a bit of subtlety in the productions for
# `x-expression-right-list`, because the `==` operator may be freely mixed into
# greater-than or less-than chains, like `a < b == c <= d` or `a > b == c >= d`,
# but greater-than and less-than may not be mixed; i.e., `a < b >= c` is
# disallowed.
#
# In order to keep the grammar unambiguous -- that is, in order to ensure that
# every valid input can only be parsed in exactly one way -- the languages
# defined by `equality-expression-right*`, `greater-expression-right-list`, and
# `less-expression-right-list` cannot overlap.
#
# `equality-expression-right*`, by definition, only contains `== n` elements.
# By forcing `greater-expression-right-list` to contain at least one
# `greater-expression-right`, we can ensure that a chain like `== n == m` cannot
# be parsed as a `greater-expression-right-list`.  Similar logic applies in the
# less-than case.
#
# There is another potential source of ambiguity here: if
# `greater-expression-right-list` were
#
#     greater-expression-right-list ->
#         equality-or-greater-expression-right* greater-expression-right
#         equality-or-greater-expression-right*
#
# then a sequence like '> b > c > d' could be parsed as any of:
#
#     () (> b) ((> c) (> d))
#     ((> b)) (> c) ((> d))
#     ((> b) (> c)) (> d) ()
#
# By using `equality-expression-right*` for the first symbol, only the first
# parse is possible.
@_handles(
    "greater-expression-right-list ->"
    "    equality-expression-right* greater-expression-right"
    "    equality-or-greater-expression-right*"
)
@_handles(
    "less-expression-right-list ->"
    "    equality-expression-right* less-expression-right"
    "    equality-or-less-expression-right*"
)
def _chained_comparison_tails(start, middle, end):
    return _List(start.list + [middle] + end.list)


@_handles("equality-or-greater-expression-right -> equality-expression-right")
@_handles("equality-or-greater-expression-right -> greater-expression-right")
@_handles("equality-or-less-expression-right -> equality-expression-right")
@_handles("equality-or-less-expression-right -> less-expression-right")
def _equality_or_less_or_greater(right):
    return right


@_handles("and-expression-right -> and-operator comparison-expression")
@_handles("or-expression-right -> or-operator comparison-expression")
@_handles("additive-expression-right -> additive-operator times-expression")
@_handles("equality-expression-right -> equality-operator additive-expression")
@_handles("greater-expression-right -> greater-operator additive-expression")
@_handles("less-expression-right -> less-operator additive-expression")
@_handles("times-expression-right ->" "    multiplicative-operator negation-expression")
def _expression_right_production(operator, expression):
    return _ExpressionTail(operator, expression)


# This supports a single layer of unary plus/minus, so "+5" and "-value" are
# allowed, but "+-5" or "-+-something" are not.
@_handles("negation-expression -> additive-operator bottom-expression")
def _negation_expression_with_operator(operator, expression):
    phantom_zero_location = ir_data.Location(
        start=operator.source_location.start, end=operator.source_location.start
    )
    return ir_data.Expression(
        function=ir_data.Function(
            function=_text_to_operator(operator.text),
            args=[
                ir_data.Expression(
                    constant=ir_data.NumericConstant(
                        value="0", source_location=phantom_zero_location
                    ),
                    source_location=phantom_zero_location,
                ),
                expression,
            ],
            function_name=operator,
            source_location=ir_data.Location(
                start=operator.source_location.start, end=expression.source_location.end
            ),
        )
    )


@_handles("negation-expression -> bottom-expression")
def _negation_expression(expression):
    return expression


@_handles('bottom-expression -> "(" expression ")"')
def _bottom_expression_parentheses(open_paren, expression, close_paren):
    del open_paren, close_paren  # Unused.
    return expression


@_handles('bottom-expression -> function-name "(" argument-list ")"')
def _bottom_expression_function(function, open_paren, arguments, close_paren):
    del open_paren  # Unused.
    return ir_data.Expression(
        function=ir_data.Function(
            function=_text_to_function(function.text),
            args=arguments.list,
            function_name=function,
            source_location=ir_data.Location(
                start=function.source_location.start,
                end=close_paren.source_location.end,
            ),
        )
    )


@_handles('comma-then-expression -> "," expression')
def _comma_then_expression(comma, expression):
    del comma  # Unused.
    return expression


@_handles("argument-list -> expression comma-then-expression*")
def _argument_list(head, tail):
    tail.list.insert(0, head)
    return tail


@_handles("argument-list ->")
def _empty_argument_list():
    return _List([])


@_handles("bottom-expression -> numeric-constant")
def _bottom_expression_from_numeric_constant(constant):
    return ir_data.Expression(constant=constant)


@_handles("bottom-expression -> constant-reference")
def _bottom_expression_from_constant_reference(reference):
    return ir_data.Expression(constant_reference=reference)


@_handles("bottom-expression -> builtin-reference")
def _bottom_expression_from_builtin(reference):
    return ir_data.Expression(builtin_reference=reference)


@_handles("bottom-expression -> boolean-constant")
def _bottom_expression_from_boolean_constant(boolean):
    return ir_data.Expression(boolean_constant=boolean)


@_handles("bottom-expression -> field-reference")
def _bottom_expression_from_reference(reference):
    return reference


@_handles("field-reference -> snake-reference field-reference-tail*")
def _indirect_field_reference(field_reference, field_references):
    if field_references.source_location.HasField("end"):
        end_location = field_references.source_location.end
    else:
        end_location = field_reference.source_location.end
    return ir_data.Expression(
        field_reference=ir_data.FieldReference(
            path=[field_reference] + field_references.list,
            source_location=parser_types.make_location(
                field_reference.source_location.start, end_location
            ),
        )
    )


# If "Type.field" ever becomes syntactically valid, it will be necessary to
# check that enum values are compile-time constants.
@_handles('field-reference-tail -> "." snake-reference')
def _field_reference_tail(dot, reference):
    del dot  # Unused.
    return reference


@_handles("numeric-constant -> Number")
def _numeric_constant(number):
    # All types of numeric constant tokenize to the same symbol, because they are
    # interchangeable in source code.
    if number.text[0:2] == "0b":
        n = int(number.text.replace("_", "")[2:], 2)
    elif number.text[0:2] == "0x":
        n = int(number.text.replace("_", "")[2:], 16)
    else:
        n = int(number.text.replace("_", ""), 10)
    return ir_data.NumericConstant(value=str(n))


@_handles("type-definition -> struct")
@_handles("type-definition -> bits")
@_handles("type-definition -> enum")
@_handles("type-definition -> external")
def _type_definition(type_definition):
    return type_definition


# struct StructureName:
#   ... fields ...
# bits BitName:
#   ... fields ...
@_handles(
    'struct -> "struct" type-name delimited-parameter-definition-list?'
    '          ":" Comment? eol struct-body'
)
@_handles(
    'bits -> "bits" type-name delimited-parameter-definition-list? ":"'
    "        Comment? eol bits-body"
)
def _structure(struct, name, parameters, colon, comment, newline, struct_body):
    """Composes the top-level IR for an Emboss structure."""
    del colon, comment, newline  # Unused.
    ir_data_utils.builder(struct_body.structure).source_location.start.CopyFrom(
        struct.source_location.start
    )
    ir_data_utils.builder(struct_body.structure).source_location.end.CopyFrom(
        struct_body.source_location.end
    )
    if struct_body.name:
        ir_data_utils.update(struct_body.name, name)
    else:
        struct_body.name = ir_data_utils.copy(name)
    if parameters.list:
        struct_body.runtime_parameter.extend(parameters.list[0].list)
    return struct_body


@_handles(
    "delimited-parameter-definition-list ->" '    "(" parameter-definition-list ")"'
)
def _delimited_parameter_definition_list(open_paren, parameters, close_paren):
    del open_paren, close_paren  # Unused
    return parameters


@_handles('parameter-definition -> snake-name ":" type')
def _parameter_definition(name, double_colon, parameter_type):
    del double_colon  # Unused
    return ir_data.RuntimeParameter(name=name, physical_type_alias=parameter_type)


@_handles('parameter-definition-list-tail -> "," parameter-definition')
def _parameter_definition_list_tail(comma, parameter):
    del comma  # Unused.
    return parameter


@_handles(
    "parameter-definition-list -> parameter-definition"
    "                             parameter-definition-list-tail*"
)
def _parameter_definition_list(head, tail):
    tail.list.insert(0, head)
    return tail


@_handles("parameter-definition-list ->")
def _empty_parameter_definition_list():
    return _List([])


# The body of a struct: basically, the part after the first line.
@_handles(
    "struct-body -> Indent doc-line* attribute-line*"
    "               type-definition* struct-field-block Dedent"
)
def _struct_body(indent, docs, attributes, types, fields, dedent):
    del indent, dedent  # Unused.
    return _structure_body(
        docs, attributes, types, fields, ir_data.AddressableUnit.BYTE
    )


def _structure_body(docs, attributes, types, fields, addressable_unit):
    """Constructs the body of a structure (bits or struct) definition."""
    return ir_data.TypeDefinition(
        structure=ir_data.Structure(field=[field.field for field in fields.list]),
        documentation=docs.list,
        attribute=attributes.list,
        subtype=types.list
        + [subtype for field in fields.list for subtype in field.subtypes],
        addressable_unit=addressable_unit,
    )


@_handles("struct-field-block ->")
@_handles("bits-field-block ->")
@_handles("anonymous-bits-field-block ->")
def _empty_field_block():
    return _List([])


@_handles(
    "struct-field-block ->" "    conditional-struct-field-block struct-field-block"
)
@_handles("bits-field-block ->" "    conditional-bits-field-block bits-field-block")
@_handles(
    "anonymous-bits-field-block -> conditional-anonymous-bits-field-block"
    "                              anonymous-bits-field-block"
)
def _conditional_block_plus_field_block(conditional_block, block):
    return _List(conditional_block.list + block.list)


@_handles("struct-field-block ->" "    unconditional-struct-field struct-field-block")
@_handles("bits-field-block ->" "    unconditional-bits-field bits-field-block")
@_handles(
    "anonymous-bits-field-block ->"
    "    unconditional-anonymous-bits-field anonymous-bits-field-block"
)
def _unconditional_block_plus_field_block(field, block):
    """Prepends an unconditional field to block."""
    ir_data_utils.builder(field.field).existence_condition.source_location.CopyFrom(
        field.source_location
    )
    ir_data_utils.builder(
        field.field
    ).existence_condition.boolean_constant.source_location.CopyFrom(
        field.source_location
    )
    ir_data_utils.builder(field.field).existence_condition.boolean_constant.value = True
    return _List([field] + block.list)


# Struct "fields" are regular fields, inline enums, bits, or structs, anonymous
# inline bits, or virtual fields.
@_handles("unconditional-struct-field -> field")
@_handles("unconditional-struct-field -> inline-enum-field-definition")
@_handles("unconditional-struct-field -> inline-bits-field-definition")
@_handles("unconditional-struct-field -> inline-struct-field-definition")
@_handles("unconditional-struct-field -> anonymous-bits-field-definition")
@_handles("unconditional-struct-field -> virtual-field")
# Bits fields are "regular" fields, inline enums or bits, or virtual fields.
#
# Inline structs and anonymous inline bits are not allowed inside of bits:
# anonymous inline bits are pointless, and inline structs do not make sense,
# since a struct cannot be a part of a bits.
#
# Anonymous inline bits may not include virtual fields; instead, the virtual
# field should be a direct part of the enclosing structure.
@_handles("unconditional-anonymous-bits-field -> field")
@_handles("unconditional-anonymous-bits-field -> inline-enum-field-definition")
@_handles("unconditional-anonymous-bits-field -> inline-bits-field-definition")
@_handles("unconditional-bits-field -> unconditional-anonymous-bits-field")
@_handles("unconditional-bits-field -> virtual-field")
def _unconditional_field(field):
    """Handles the unifying grammar production for a struct or bits field."""
    return field


# TODO(bolms): Add 'elif' and 'else' support.
# TODO(bolms): Should nested 'if' blocks be allowed?
@_handles(
    "conditional-struct-field-block ->"
    '    "if" expression ":" Comment? eol'
    "        Indent unconditional-struct-field+ Dedent"
)
@_handles(
    "conditional-bits-field-block ->"
    '    "if" expression ":" Comment? eol'
    "        Indent unconditional-bits-field+ Dedent"
)
@_handles(
    "conditional-anonymous-bits-field-block ->"
    '    "if" expression ":" Comment? eol'
    "        Indent unconditional-anonymous-bits-field+ Dedent"
)
def _conditional_field_block(
    if_keyword, expression, colon, comment, newline, indent, fields, dedent
):
    """Applies an existence_condition to each element of fields."""
    del if_keyword, newline, colon, comment, indent, dedent  # Unused.
    for field in fields.list:
        condition = ir_data_utils.builder(field.field).existence_condition
        condition.CopyFrom(expression)
        condition.source_location.is_disjoint_from_parent = True
    return fields


# The body of a bit field definition: basically, the part after the first line.
@_handles(
    "bits-body -> Indent doc-line* attribute-line*"
    "             type-definition* bits-field-block Dedent"
)
def _bits_body(indent, docs, attributes, types, fields, dedent):
    del indent, dedent  # Unused.
    return _structure_body(docs, attributes, types, fields, ir_data.AddressableUnit.BIT)


# Inline bits (defined as part of a field) are more restricted than standalone
# bits.
@_handles(
    "anonymous-bits-body ->"
    "    Indent attribute-line* anonymous-bits-field-block Dedent"
)
def _anonymous_bits_body(indent, attributes, fields, dedent):
    del indent, dedent  # Unused.
    return _structure_body(
        _List([]), attributes, _List([]), fields, ir_data.AddressableUnit.BIT
    )


# A field is:
#     range  type  name  (abbr)  [attr: value] [attr2: value] -- doc
#         -- doc
#         -- doc
#         [attr3: value]
#         [attr4: value]
@_handles(
    "field ->"
    "    field-location type snake-name abbreviation? attribute* doc?"
    "    Comment? eol field-body?"
)
def _field(
    location,
    field_type,
    name,
    abbreviation,
    attributes,
    doc,
    comment,
    newline,
    field_body,
):
    """Constructs an ir_data.Field from the given components."""
    del comment  # Unused
    field_ir = ir_data.Field(
        location=location,
        type=field_type,
        name=name,
        attribute=attributes.list,
        documentation=doc.list,
    )
    field = ir_data_utils.builder(field_ir)
    if field_body.list:
        field.attribute.extend(field_body.list[0].attribute)
        field.documentation.extend(field_body.list[0].documentation)
    if abbreviation.list:
        field.abbreviation.CopyFrom(abbreviation.list[0])
    field.source_location.start.CopyFrom(location.source_location.start)
    if field_body.source_location.HasField("end"):
        field.source_location.end.CopyFrom(field_body.source_location.end)
    else:
        field.source_location.end.CopyFrom(newline.source_location.end)
    return _FieldWithType(field=field_ir)


# A "virtual field" is:
#     let name = value
#         -- doc
#         -- doc
#         [attr1: value]
#         [attr2: value]
@_handles(
    "virtual-field ->" '    "let" snake-name "=" expression Comment? eol field-body?'
)
def _virtual_field(let, name, equals, value, comment, newline, field_body):
    """Constructs an ir_data.Field from the given components."""
    del equals, comment  # Unused
    field_ir = ir_data.Field(read_transform=value, name=name)
    field = ir_data_utils.builder(field_ir)
    if field_body.list:
        field.attribute.extend(field_body.list[0].attribute)
        field.documentation.extend(field_body.list[0].documentation)
    field.source_location.start.CopyFrom(let.source_location.start)
    if field_body.source_location.HasField("end"):
        field.source_location.end.CopyFrom(field_body.source_location.end)
    else:
        field.source_location.end.CopyFrom(newline.source_location.end)
    return _FieldWithType(field=field_ir)


# An inline enum is:
#     range  "enum"  name  (abbr):
#         -- doc
#         -- doc
#         [attr3: value]
#         [attr4: value]
#         NAME = 10
#         NAME2 = 20
@_handles(
    "inline-enum-field-definition ->"
    '    field-location "enum" snake-name abbreviation? ":" Comment? eol'
    "    enum-body"
)
def _inline_enum_field(
    location, enum, name, abbreviation, colon, comment, newline, enum_body
):
    """Constructs an ir_data.Field for an inline enum field."""
    del enum, colon, comment, newline  # Unused.
    return _inline_type_field(location, name, abbreviation, enum_body)


@_handles(
    "inline-struct-field-definition ->"
    '    field-location "struct" snake-name abbreviation? ":" Comment? eol'
    "    struct-body"
)
def _inline_struct_field(
    location, struct, name, abbreviation, colon, comment, newline, struct_body
):
    del struct, colon, comment, newline  # Unused.
    return _inline_type_field(location, name, abbreviation, struct_body)


@_handles(
    "inline-bits-field-definition ->"
    '    field-location "bits" snake-name abbreviation? ":" Comment? eol'
    "    bits-body"
)
def _inline_bits_field(
    location, bits, name, abbreviation, colon, comment, newline, bits_body
):
    del bits, colon, comment, newline  # Unused.
    return _inline_type_field(location, name, abbreviation, bits_body)


def _inline_type_field(location, name, abbreviation, body):
    """Shared implementation of _inline_enum_field and _anonymous_bit_field."""
    field_ir = ir_data.Field(
        location=location,
        name=name,
        attribute=body.attribute,
        documentation=body.documentation,
    )
    field = ir_data_utils.builder(field_ir)
    # All attributes should be attached to the field, not the type definition: if
    # the user wants to use type attributes, they should create a separate type
    # definition and reference it.
    del body.attribute[:]
    type_name = ir_data_utils.copy(name)
    ir_data_utils.builder(type_name).name.text = name_conversion.snake_to_camel(
        type_name.name.text
    )
    field.type.atomic_type.reference.source_name.extend([type_name.name])
    field.type.atomic_type.reference.source_location.CopyFrom(type_name.source_location)
    field.type.atomic_type.reference.is_local_name = True
    field.type.atomic_type.source_location.CopyFrom(type_name.source_location)
    field.type.source_location.CopyFrom(type_name.source_location)
    if abbreviation.list:
        field.abbreviation.CopyFrom(abbreviation.list[0])
    field.source_location.start.CopyFrom(location.source_location.start)
    ir_data_utils.builder(body.source_location).start.CopyFrom(
        location.source_location.start
    )
    if body.HasField("enumeration"):
        ir_data_utils.builder(body.enumeration).source_location.CopyFrom(
            body.source_location
        )
    else:
        assert body.HasField("structure")
        ir_data_utils.builder(body.structure).source_location.CopyFrom(
            body.source_location
        )
    ir_data_utils.builder(body).name.CopyFrom(type_name)
    field.source_location.end.CopyFrom(body.source_location.end)
    subtypes = [body] + list(body.subtype)
    del body.subtype[:]
    return _FieldWithType(field=field_ir, subtypes=subtypes)


@_handles(
    "anonymous-bits-field-definition ->"
    '    field-location "bits" ":" Comment? eol anonymous-bits-body'
)
def _anonymous_bit_field(location, bits_keyword, colon, comment, newline, bits_body):
    """Constructs an ir_data.Field for an anonymous bit field."""
    del colon, comment, newline  # Unused.
    name = ir_data.NameDefinition(
        name=ir_data.Word(
            text=_get_anonymous_field_name(),
            source_location=bits_keyword.source_location,
        ),
        source_location=bits_keyword.source_location,
        is_anonymous=True,
    )
    return _inline_type_field(location, name, _List([]), bits_body)


@_handles("field-body -> Indent doc-line* attribute-line* Dedent")
def _field_body(indent, docs, attributes, dedent):
    del indent, dedent  # Unused.
    return ir_data.Field(documentation=docs.list, attribute=attributes.list)


# A parenthetically-denoted abbreviation.
@_handles('abbreviation -> "(" snake-word ")"')
def _abbreviation(open_paren, word, close_paren):
    del open_paren, close_paren  # Unused.
    return word


# enum EnumName:
#   ... values ...
@_handles('enum -> "enum" type-name ":" Comment? eol enum-body')
def _enum(enum, name, colon, comment, newline, enum_body):
    del colon, comment, newline  # Unused.
    ir_data_utils.builder(enum_body.enumeration).source_location.start.CopyFrom(
        enum.source_location.start
    )
    ir_data_utils.builder(enum_body.enumeration).source_location.end.CopyFrom(
        enum_body.source_location.end
    )
    ir_data_utils.builder(enum_body).name.CopyFrom(name)
    return enum_body


# [enum Foo:]
#   name = value
#   name = value
@_handles("enum-body -> Indent doc-line* attribute-line* enum-value+ Dedent")
def _enum_body(indent, docs, attributes, values, dedent):
    del indent, dedent  # Unused.
    return ir_data.TypeDefinition(
        enumeration=ir_data.Enum(value=values.list),
        documentation=docs.list,
        attribute=attributes.list,
        addressable_unit=ir_data.AddressableUnit.BIT,
    )


# name = value
@_handles(
    "enum-value -> "
    '    constant-name "=" expression attribute* doc? Comment? eol enum-value-body?'
)
def _enum_value(
    name, equals, expression, attribute, documentation, comment, newline, body
):
    """Constructs an IR node for an enum value statement (`NAME = value`)."""
    del equals, comment, newline  # Unused.
    result = ir_data.EnumValue(
        name=name,
        value=expression,
        documentation=documentation.list,
        attribute=attribute.list,
    )
    if body.list:
        result.documentation.extend(body.list[0].documentation)
        result.attribute.extend(body.list[0].attribute)
    return result


@_handles("enum-value-body -> Indent doc-line* attribute-line* Dedent")
def _enum_value_body(indent, docs, attributes, dedent):
    del indent, dedent  # Unused.
    return ir_data.EnumValue(documentation=docs.list, attribute=attributes.list)


# An external is just a declaration that a type exists and has certain
# attributes.
@_handles('external -> "external" type-name ":" Comment? eol external-body')
def _external(external, name, colon, comment, newline, external_body):
    del colon, comment, newline  # Unused.
    ir_data_utils.builder(external_body.source_location).start.CopyFrom(
        external.source_location.start
    )
    if external_body.name:
        ir_data_utils.update(external_body.name, name)
    else:
        external_body.name = ir_data_utils.copy(name)
    return external_body


# This syntax implicitly requires either a documentation line or a attribute
# line, or it won't parse (because no Indent/Dedent tokens will be emitted).
@_handles("external-body -> Indent doc-line* attribute-line* Dedent")
def _external_body(indent, docs, attributes, dedent):
    return ir_data.TypeDefinition(
        external=ir_data.External(
            # Set source_location here, since it won't be set automatically.
            source_location=ir_data.Location(
                start=indent.source_location.start, end=dedent.source_location.end
            )
        ),
        documentation=docs.list,
        attribute=attributes.list,
    )


@_handles('field-location -> expression "[" "+" expression "]"')
def _field_location(start, open_bracket, plus, size, close_bracket):
    del open_bracket, plus, close_bracket  # Unused.
    return ir_data.FieldLocation(start=start, size=size)


@_handles('delimited-argument-list -> "(" argument-list ")"')
def _type_argument_list(open_paren, arguments, close_paren):
    del open_paren, close_paren  # Unused
    return arguments


# A type is "TypeName" or "TypeName[length]" or "TypeName[length][length]", etc.
# An array type may have an empty length ("Type[]").  This is only valid for the
# outermost length (the last set of brackets), but that must be checked
# elsewhere.
@_handles(
    "type -> type-reference delimited-argument-list? type-size-specifier?"
    "        array-length-specifier*"
)
def _type(reference, parameters, size, array_spec):
    """Builds the IR for a type specifier."""
    base_type_source_location_end = reference.source_location.end
    atomic_type_source_location_end = reference.source_location.end
    if parameters.list:
        base_type_source_location_end = parameters.source_location.end
        atomic_type_source_location_end = parameters.source_location.end
    if size.list:
        base_type_source_location_end = size.source_location.end
    base_type_location = parser_types.make_location(
        reference.source_location.start, base_type_source_location_end
    )
    atomic_type_location = parser_types.make_location(
        reference.source_location.start, atomic_type_source_location_end
    )
    t = ir_data.Type(
        atomic_type=ir_data.AtomicType(
            reference=ir_data_utils.copy(reference),
            source_location=atomic_type_location,
            runtime_parameter=parameters.list[0].list if parameters.list else [],
        ),
        size_in_bits=size.list[0] if size.list else None,
        source_location=base_type_location,
    )
    for length in array_spec.list:
        location = parser_types.make_location(
            t.source_location.start, length.source_location.end
        )
        if isinstance(length, ir_data.Expression):
            t = ir_data.Type(
                array_type=ir_data.ArrayType(
                    base_type=t, element_count=length, source_location=location
                ),
                source_location=location,
            )
        elif isinstance(length, ir_data.Empty):
            t = ir_data.Type(
                array_type=ir_data.ArrayType(
                    base_type=t, automatic=length, source_location=location
                ),
                source_location=location,
            )
        else:
            assert False, "Shouldn't be here."
    return t


# TODO(bolms): Should symbolic names or expressions be allowed?  E.g.,
# UInt:FIELD_SIZE or UInt:(16 + 16)?
@_handles('type-size-specifier -> ":" numeric-constant')
def _type_size_specifier(colon, numeric_constant):
    """handles the ":32" part of a type specifier like "UInt:32"."""
    del colon
    return ir_data.Expression(constant=numeric_constant)


# The distinctions between different formats of NameDefinitions, Words, and
# References are enforced during parsing, but not propagated to the IR.
@_handles("type-name -> type-word")
@_handles("snake-name -> snake-word")
@_handles("constant-name -> constant-word")
def _name(word):
    return ir_data.NameDefinition(name=word)


@_handles("type-word -> CamelWord")
@_handles("snake-word -> SnakeWord")
@_handles('builtin-field-word -> "$size_in_bits"')
@_handles('builtin-field-word -> "$size_in_bytes"')
@_handles('builtin-field-word -> "$max_size_in_bits"')
@_handles('builtin-field-word -> "$max_size_in_bytes"')
@_handles('builtin-field-word -> "$min_size_in_bits"')
@_handles('builtin-field-word -> "$min_size_in_bytes"')
@_handles('builtin-word -> "$is_statically_sized"')
@_handles('builtin-word -> "$static_size_in_bits"')
@_handles('builtin-word -> "$next"')
@_handles("constant-word -> ShoutyWord")
@_handles('and-operator -> "&&"')
@_handles('or-operator -> "||"')
@_handles('less-operator -> "<="')
@_handles('less-operator -> "<"')
@_handles('greater-operator -> ">="')
@_handles('greater-operator -> ">"')
@_handles('equality-operator -> "=="')
@_handles('inequality-operator -> "!="')
@_handles('additive-operator -> "+"')
@_handles('additive-operator -> "-"')
@_handles('multiplicative-operator -> "*"')
@_handles('function-name -> "$max"')
@_handles('function-name -> "$present"')
@_handles('function-name -> "$upper_bound"')
@_handles('function-name -> "$lower_bound"')
def _word(word):
    return ir_data.Word(text=word.text)


@_handles("type-reference -> type-reference-tail")
@_handles("constant-reference -> constant-reference-tail")
def _un_module_qualified_type_reference(reference):
    return reference


@_handles("constant-reference-tail -> constant-word")
@_handles("type-reference-tail -> type-word")
@_handles("snake-reference -> snake-word")
@_handles("snake-reference -> builtin-field-word")
def _reference(word):
    return ir_data.Reference(source_name=[word])


@_handles("builtin-reference -> builtin-word")
def _builtin_reference(word):
    return ir_data.Reference(
        source_name=[word],
        canonical_name=ir_data.CanonicalName(object_path=[word.text]),
    )


# Because constant-references ("Enum.NAME") are used in the same contexts as
# field-references ("field.subfield"), module-qualified constant references
# ("module.Enum.VALUE") have to take snake-reference, not snake-word, on the
# left side of the dot.  Otherwise, when a "snake_word" is followed by a "." in
# an expression context, the LR(1) parser cannot determine whether to reduce the
# snake-word to snake-reference (to eventually become field-reference), or to
# shift the dot onto the stack (to eventually become constant-reference).  By
# using snake-reference as the head of both, the parser can always reduce, then
# shift the dot, then determine whether to proceed with constant-reference if it
# sees "snake_name.TypeName" or field-reference if it sees
# "snake_name.snake_name".
@_handles('constant-reference -> snake-reference "." constant-reference-tail')
def _module_qualified_constant_reference(new_head, dot, reference):
    del dot  # Unused.
    new_source_name = list(new_head.source_name) + list(reference.source_name)
    del reference.source_name[:]
    reference.source_name.extend(new_source_name)
    return reference


@_handles('constant-reference-tail -> type-word "." constant-reference-tail')
# module.Type.SubType.name is a reference to something that *must* be a
# constant.
@_handles('constant-reference-tail -> type-word "." snake-reference')
@_handles('type-reference-tail -> type-word "." type-reference-tail')
@_handles('type-reference -> snake-word "." type-reference-tail')
def _qualified_reference(word, dot, reference):
    """Adds a name. or Type. qualification to the head of a reference."""
    del dot  # Unused.
    new_source_name = [word] + list(reference.source_name)
    del reference.source_name[:]
    reference.source_name.extend(new_source_name)
    return reference


# Arrays are properly translated to IR in _type().
@_handles('array-length-specifier -> "[" expression "]"')
def _array_length_specifier(open_bracket, length, close_bracket):
    del open_bracket, close_bracket  # Unused.
    return length


# An array specifier can end with empty brackets ("arr[3][]"), in which case the
# array's size is inferred from the size of its enclosing field.
@_handles('array-length-specifier -> "[" "]"')
def _auto_array_length_specifier(open_bracket, close_bracket):
    # Note that the Void's source_location is the space between the brackets (if
    # any).
    return ir_data.Empty(
        source_location=ir_data.Location(
            start=open_bracket.source_location.end,
            end=close_bracket.source_location.start,
        )
    )


@_handles('eol -> "\\n" comment-line*')
def _eol(eol, comments):
    del comments  # Unused
    return eol


@_handles('comment-line -> Comment? "\\n"')
def _comment_line(comment, eol):
    del comment  # Unused
    return eol


def _finalize_grammar():
    """_Finalize adds productions for foo*, foo+, and foo? symbols."""
    star_symbols = set()
    plus_symbols = set()
    option_symbols = set()
    for production in _handlers:
        for symbol in production.rhs:
            if symbol[-1] == "*":
                star_symbols.add(symbol[:-1])
            elif symbol[-1] == "+":
                # symbol+ relies on the rule for symbol*
                star_symbols.add(symbol[:-1])
                plus_symbols.add(symbol[:-1])
            elif symbol[-1] == "?":
                option_symbols.add(symbol[:-1])
    for symbol in star_symbols:
        _handles("{s}* -> {s} {s}*".format(s=symbol))(lambda e, r: _List([e] + r.list))
        _handles("{s}* ->".format(s=symbol))(lambda: _List([]))
    for symbol in plus_symbols:
        _handles("{s}+ -> {s} {s}*".format(s=symbol))(lambda e, r: _List([e] + r.list))
    for symbol in option_symbols:
        _handles("{s}? -> {s}".format(s=symbol))(lambda e: _List([e]))
        _handles("{s}? ->".format(s=symbol))(lambda: _List([]))


_finalize_grammar()

# End of grammar.
################################################################################

# These export the grammar used by module_ir so that parser_generator can build
# a parser for the same language.
START_SYMBOL = "module"
EXPRESSION_START_SYMBOL = "expression"
PRODUCTIONS = list(_handlers.keys())
