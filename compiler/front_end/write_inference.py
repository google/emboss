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

"""Adds auto-generated virtual fields to the IR."""

from compiler.front_end import attributes
from compiler.front_end import expression_bounds
from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import ir_util
from compiler.util import traverse_ir


def _find_field_reference_path(expression):
    """Returns a path to a field reference, or None.

    If the provided expression contains exactly one field_reference,
    _find_field_reference_path will return a list of indexes, such that
    recursively reading the index'th element of expression.function.args will find
    the field_reference.  For example, for:

        5 + (x * 2)

    _find_field_reference_path will return [1, 0]: from the top-level `+`
    expression, arg 1 is the `x * 2` expression, and `x` is arg 0 of the `*`
    expression.

    Arguments:
      expression: an ir_data.Expression to walk

    Returns:
      A list of indexes to find a field_reference, or None.
    """
    found, indexes = _recursively_find_field_reference_path(expression)
    if found == 1:
        return indexes
    else:
        return None


def _recursively_find_field_reference_path(expression):
    """Recursive implementation of _find_field_reference_path."""
    if expression.WhichOneof("expression") == "field_reference":
        return 1, []
    elif expression.WhichOneof("expression") == "function":
        field_count = 0
        path = []
        for index in range(len(expression.function.args)):
            arg = expression.function.args[index]
            arg_result = _recursively_find_field_reference_path(arg)
            arg_field_count, arg_path = arg_result
            if arg_field_count == 1 and field_count == 0:
                path = [index] + arg_path
            field_count += arg_field_count
        if field_count == 1:
            return field_count, path
        else:
            return field_count, []
    else:
        return 0, []


def _invert_expression(expression, ir):
    """For the given expression, searches for an algebraic inverse expression.

    That is, it takes the notional equation:

        $logical_value = expression

    and, if there is exactly one `field_reference` in `expression`, it will
    attempt to solve the equation for that field.  For example, if the expression
    is `x + 1`, it will iteratively transform:

        $logical_value = x + 1
        $logical_value - 1 = x + 1 - 1
        $logical_value - 1 = x

    and finally return `x` and `$logical_value - 1`.

    The purpose of this transformation is to find an assignment statement that can
    be used to write back through certain virtual fields.  E.g., given:

        struct Foo:
          0 [+1]  UInt  raw_value
          let actual_value = raw_value + 100

    it should be possible to write a value to the `actual_value` field, and have
    it set `raw_value` to the appropriate value.

    Arguments:
      expression: an ir_data.Expression to be inverted.
      ir: the full IR, for looking up symbols.

    Returns:
      (field_reference, inverse_expression) if expression can be inverted,
      otherwise None.
    """
    reference_path = _find_field_reference_path(expression)
    if reference_path is None:
        return None
    subexpression = expression
    result = ir_data.Expression(
        builtin_reference=ir_data.Reference(
            canonical_name=ir_data.CanonicalName(
                module_file="", object_path=["$logical_value"]
            ),
            source_name=[
                ir_data.Word(
                    text="$logical_value",
                    source_location=ir_data.Location(is_synthetic=True),
                )
            ],
            source_location=ir_data.Location(is_synthetic=True),
        ),
        type=expression.type,
        source_location=ir_data.Location(is_synthetic=True),
    )

    # This loop essentially starts with:
    #
    #     f(g(x)) == $logical_value
    #
    # and ends with
    #
    #     x == g_inv(f_inv($logical_value))
    #
    # At each step, `subexpression` has one layer removed, and `result` has a
    # corresponding inverse function applied.  So, for example, it might start
    # with:
    #
    #     2 + ((3 - x) - 10)  ==  $logical_value
    #
    # On each iteration, `subexpression` and `result` will become:
    #
    #     (3 - x) - 10  ==  $logical_value - 2    [subtract 2 from both sides]
    #     (3 - x)  ==  ($logical_value - 2) + 10  [add 10 to both sides]
    #     x  ==  3 - (($logical_value - 2) + 10)  [subtract both sides from 3]
    #
    # This is an extremely limited algebraic solver, but it covers common-enough
    # cases.
    #
    # Note that any equation that can be solved here becomes part of Emboss's
    # contract, forever, so be conservative in expanding its solving capabilities!
    for index in reference_path:
        if subexpression.function.function == ir_data.FunctionMapping.ADDITION:
            result = ir_data.Expression(
                function=ir_data.Function(
                    function=ir_data.FunctionMapping.SUBTRACTION,
                    args=[
                        result,
                        subexpression.function.args[1 - index],
                    ],
                ),
                type=ir_data.ExpressionType(integer=ir_data.IntegerType()),
            )
        elif subexpression.function.function == ir_data.FunctionMapping.SUBTRACTION:
            if index == 0:
                result = ir_data.Expression(
                    function=ir_data.Function(
                        function=ir_data.FunctionMapping.ADDITION,
                        args=[
                            result,
                            subexpression.function.args[1],
                        ],
                    ),
                    type=ir_data.ExpressionType(integer=ir_data.IntegerType()),
                )
            else:
                result = ir_data.Expression(
                    function=ir_data.Function(
                        function=ir_data.FunctionMapping.SUBTRACTION,
                        args=[
                            subexpression.function.args[0],
                            result,
                        ],
                    ),
                    type=ir_data.ExpressionType(integer=ir_data.IntegerType()),
                )
        else:
            return None
        subexpression = subexpression.function.args[index]
    expression_bounds.compute_constraints_of_expression(result, ir)
    return subexpression, result


def _add_write_method(field, ir):
    """Adds an appropriate write_method to field, if applicable.

    Currently, the "alias" write_method will be added for virtual fields of the
    form `let v = some_field_reference` when `some_field_reference` is a physical
    field or a writeable alias.  The "physical" write_method will be added for
    physical fields.  The "transform" write_method will be added when the virtual
    field's value is an easily-invertible function of a single writeable field.
    All other fields will have the "read_only" write_method; i.e., they will not
    be writeable.

    Arguments:
      field: an ir_data.Field to which to add a write_method.
      ir: The IR in which to look up field_references.

    Returns:
      None
    """
    if field.HasField("write_method"):
        # Do not recompute anything.
        return

    if not ir_util.field_is_virtual(field):
        # If the field is not virtual, writes are physical.
        ir_data_utils.builder(field).write_method.physical = True
        return

    field_checker = ir_data_utils.reader(field)
    field_builder = ir_data_utils.builder(field)

    # A virtual field cannot be a direct alias if it has an additional
    # requirement.
    requires_attr = ir_util.get_attribute(field.attribute, attributes.REQUIRES)
    if (
        field_checker.read_transform.WhichOneof("expression") != "field_reference"
        or requires_attr is not None
    ):
        inverse = _invert_expression(field.read_transform, ir)
        if inverse:
            field_reference, function_body = inverse
            referenced_field = ir_util.find_object(
                field_reference.field_reference.path[-1], ir
            )
            if not isinstance(referenced_field, ir_data.Field):
                reference_is_read_only = True
            else:
                _add_write_method(referenced_field, ir)
                reference_is_read_only = referenced_field.write_method.read_only
            if not reference_is_read_only:
                field_builder.write_method.transform.destination.CopyFrom(
                    field_reference.field_reference
                )
                field_builder.write_method.transform.function_body.CopyFrom(
                    function_body
                )
            else:
                # If the virtual field's expression is invertible, but its target field
                # is read-only, it is also read-only.
                field_builder.write_method.read_only = True
        else:
            # If the virtual field's expression is not invertible, it is
            # read-only.
            field_builder.write_method.read_only = True
        return

    referenced_field = ir_util.find_object(
        field.read_transform.field_reference.path[-1], ir
    )
    if not isinstance(referenced_field, ir_data.Field):
        # If the virtual field aliases a non-field (i.e., a parameter), it is
        # read-only.
        field_builder.write_method.read_only = True
        return

    _add_write_method(referenced_field, ir)
    if referenced_field.write_method.read_only:
        # If the virtual field directly aliases a read-only field, it is read-only.
        field_builder.write_method.read_only = True
        return

    # Otherwise, it can be written as a direct alias.
    field_builder.write_method.alias.CopyFrom(field.read_transform.field_reference)


def set_write_methods(ir):
    """Sets the write_method member of all ir_data.Fields in ir.

    Arguments:
        ir: The IR to which to add write_methods.

    Returns:
        A list of errors, or an empty list.
    """
    traverse_ir.fast_traverse_ir_top_down(ir, [ir_data.Field], _add_write_method)
    return []
