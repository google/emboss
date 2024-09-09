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

"""Functions for checking expression types."""

from compiler.front_end import attributes
from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import ir_util
from compiler.util import traverse_ir


def _type_check_expression(expression, source_file_name, ir, errors):
    """Checks and annotates the type of an expression and all subexpressions."""
    if ir_data_utils.reader(expression).type.WhichOneof("type"):
        # This expression has already been type checked.
        return
    expression_variety = expression.WhichOneof("expression")
    if expression_variety == "constant":
        _type_check_integer_constant(expression)
    elif expression_variety == "constant_reference":
        _type_check_constant_reference(expression, source_file_name, ir, errors)
    elif expression_variety == "function":
        _type_check_operation(expression, source_file_name, ir, errors)
    elif expression_variety == "field_reference":
        _type_check_local_reference(expression, ir, errors)
    elif expression_variety == "boolean_constant":
        _type_check_boolean_constant(expression)
    elif expression_variety == "builtin_reference":
        _type_check_builtin_reference(expression)
    else:
        assert False, "Unknown expression variety {!r}".format(expression_variety)


def _annotate_as_integer(expression):
    ir_data_utils.builder(expression).type.integer.CopyFrom(ir_data.IntegerType())


def _annotate_as_boolean(expression):
    ir_data_utils.builder(expression).type.boolean.CopyFrom(ir_data.BooleanType())


def _type_check(
    expression, source_file_name, errors, type_oneof, type_name, expression_name
):
    if ir_data_utils.reader(expression).type.WhichOneof("type") != type_oneof:
        errors.append(
            [
                error.error(
                    source_file_name,
                    expression.source_location,
                    "{} must be {}.".format(expression_name, type_name),
                )
            ]
        )


def _type_check_integer(expression, source_file_name, errors, expression_name):
    _type_check(
        expression, source_file_name, errors, "integer", "an integer", expression_name
    )


def _type_check_boolean(expression, source_file_name, errors, expression_name):
    _type_check(
        expression, source_file_name, errors, "boolean", "a boolean", expression_name
    )


def _kind_check_field_reference(expression, source_file_name, errors, expression_name):
    if expression.WhichOneof("expression") != "field_reference":
        errors.append(
            [
                error.error(
                    source_file_name,
                    expression.source_location,
                    "{} must be a field.".format(expression_name),
                )
            ]
        )


def _type_check_integer_constant(expression):
    _annotate_as_integer(expression)


def _type_check_constant_reference(expression, source_file_name, ir, errors):
    """Annotates the type of a constant reference."""
    referred_name = expression.constant_reference.canonical_name
    referred_object = ir_util.find_object(referred_name, ir)
    if isinstance(referred_object, ir_data.EnumValue):
        ir_data_utils.builder(expression).type.enumeration.name.CopyFrom(
            expression.constant_reference
        )
        del expression.type.enumeration.name.canonical_name.object_path[-1]
    elif isinstance(referred_object, ir_data.Field):
        if not ir_util.field_is_virtual(referred_object):
            errors.append(
                [
                    error.error(
                        source_file_name,
                        expression.source_location,
                        "Static references to physical fields are not allowed.",
                    ),
                    error.note(
                        referred_name.module_file,
                        referred_object.source_location,
                        "{} is a physical field.".format(referred_name.object_path[-1]),
                    ),
                ]
            )
            return
        _type_check_expression(
            referred_object.read_transform, referred_name.module_file, ir, errors
        )
        ir_data_utils.builder(expression).type.CopyFrom(
            referred_object.read_transform.type
        )
    else:
        assert False, "Unexpected constant reference type."


def _type_check_operation(expression, source_file_name, ir, errors):
    """Type checks a function or operator expression."""
    for arg in expression.function.args:
        _type_check_expression(arg, source_file_name, ir, errors)
    function = expression.function.function
    if function in (
        ir_data.FunctionMapping.EQUALITY,
        ir_data.FunctionMapping.INEQUALITY,
        ir_data.FunctionMapping.LESS,
        ir_data.FunctionMapping.LESS_OR_EQUAL,
        ir_data.FunctionMapping.GREATER,
        ir_data.FunctionMapping.GREATER_OR_EQUAL,
    ):
        _type_check_comparison_operator(expression, source_file_name, errors)
    elif function == ir_data.FunctionMapping.CHOICE:
        _type_check_choice_operator(expression, source_file_name, errors)
    else:
        _type_check_monomorphic_operator(expression, source_file_name, errors)


def _type_check_monomorphic_operator(expression, source_file_name, errors):
    """Type checks an operator that accepts only one set of argument types."""
    args = expression.function.args
    int_args = _type_check_integer
    bool_args = _type_check_boolean
    field_args = _kind_check_field_reference
    int_result = _annotate_as_integer
    bool_result = _annotate_as_boolean
    binary = ("Left argument", "Right argument")
    n_ary = ("Argument {}".format(n) for n in range(len(args)))
    functions = {
        ir_data.FunctionMapping.ADDITION: (
            int_result,
            int_args,
            binary,
            2,
            2,
            "operator",
        ),
        ir_data.FunctionMapping.SUBTRACTION: (
            int_result,
            int_args,
            binary,
            2,
            2,
            "operator",
        ),
        ir_data.FunctionMapping.MULTIPLICATION: (
            int_result,
            int_args,
            binary,
            2,
            2,
            "operator",
        ),
        ir_data.FunctionMapping.AND: (bool_result, bool_args, binary, 2, 2, "operator"),
        ir_data.FunctionMapping.OR: (bool_result, bool_args, binary, 2, 2, "operator"),
        ir_data.FunctionMapping.MAXIMUM: (
            int_result,
            int_args,
            n_ary,
            1,
            None,
            "function",
        ),
        ir_data.FunctionMapping.PRESENCE: (
            bool_result,
            field_args,
            n_ary,
            1,
            1,
            "function",
        ),
        ir_data.FunctionMapping.UPPER_BOUND: (
            int_result,
            int_args,
            n_ary,
            1,
            1,
            "function",
        ),
        ir_data.FunctionMapping.LOWER_BOUND: (
            int_result,
            int_args,
            n_ary,
            1,
            1,
            "function",
        ),
    }
    function = expression.function.function
    (set_result_type, check_arg, arg_names, min_args, max_args, kind) = functions[
        function
    ]
    for argument, name in zip(args, arg_names):
        assert name is not None, "Too many arguments to function!"
        check_arg(
            argument,
            source_file_name,
            errors,
            "{} of {} '{}'".format(name, kind, expression.function.function_name.text),
        )
    if len(args) < min_args:
        errors.append(
            [
                error.error(
                    source_file_name,
                    expression.source_location,
                    "{} '{}' requires {} {} argument{}.".format(
                        kind.title(),
                        expression.function.function_name.text,
                        "exactly" if min_args == max_args else "at least",
                        min_args,
                        "s" if min_args > 1 else "",
                    ),
                )
            ]
        )
    if max_args is not None and len(args) > max_args:
        errors.append(
            [
                error.error(
                    source_file_name,
                    expression.source_location,
                    "{} '{}' requires {} {} argument{}.".format(
                        kind.title(),
                        expression.function.function_name.text,
                        "exactly" if min_args == max_args else "at most",
                        max_args,
                        "s" if max_args > 1 else "",
                    ),
                )
            ]
        )
    set_result_type(expression)


def _type_check_local_reference(expression, ir, errors):
    """Annotates the type of a local reference."""
    referrent = ir_util.find_object(expression.field_reference.path[-1], ir)
    assert referrent, "Local reference should be non-None after name resolution."
    if isinstance(referrent, ir_data.RuntimeParameter):
        parameter = referrent
        _set_expression_type_from_physical_type_reference(
            expression, parameter.physical_type_alias.atomic_type.reference, ir
        )
        return
    field = referrent
    if ir_util.field_is_virtual(field):
        _type_check_expression(
            field.read_transform, expression.field_reference.path[0], ir, errors
        )
        ir_data_utils.builder(expression).type.CopyFrom(field.read_transform.type)
        return
    if not field.type.HasField("atomic_type"):
        ir_data_utils.builder(expression).type.opaque.CopyFrom(ir_data.OpaqueType())
    else:
        _set_expression_type_from_physical_type_reference(
            expression, field.type.atomic_type.reference, ir
        )


def unbounded_expression_type_for_physical_type(type_definition):
    """Gets the ExpressionType for a field of the given TypeDefinition.

    Arguments:
      type_definition: an ir_data.AddressableUnit.

    Returns:
      An ir_data.ExpressionType with the corresponding expression type filled in:
      for example, [prelude].UInt will result in an ExpressionType with the
      `integer` field filled in.

      The returned ExpressionType will not have any bounds set.
    """
    # TODO(bolms): Add a `[value_type]` attribute for `external`s.
    if ir_util.get_boolean_attribute(type_definition.attribute, attributes.IS_INTEGER):
        return ir_data.ExpressionType(integer=ir_data.IntegerType())
    elif tuple(type_definition.name.canonical_name.object_path) == ("Flag",):
        # This is a hack: the Flag type should say that it is a boolean.
        return ir_data.ExpressionType(boolean=ir_data.BooleanType())
    elif type_definition.HasField("enumeration"):
        return ir_data.ExpressionType(
            enumeration=ir_data.EnumType(
                name=ir_data.Reference(
                    canonical_name=type_definition.name.canonical_name
                )
            )
        )
    else:
        return ir_data.ExpressionType(opaque=ir_data.OpaqueType())


def _set_expression_type_from_physical_type_reference(expression, type_reference, ir):
    """Sets the type of an expression to match a physical type."""
    field_type = ir_util.find_object(type_reference, ir)
    assert field_type, "Field type should be non-None after name resolution."
    ir_data_utils.builder(expression).type.CopyFrom(
        unbounded_expression_type_for_physical_type(field_type)
    )


def _annotate_parameter_type(parameter, ir, source_file_name, errors):
    if parameter.physical_type_alias.WhichOneof("type") != "atomic_type":
        errors.append(
            [
                error.error(
                    source_file_name,
                    parameter.physical_type_alias.source_location,
                    "Parameters cannot be arrays.",
                )
            ]
        )
        return
    _set_expression_type_from_physical_type_reference(
        parameter, parameter.physical_type_alias.atomic_type.reference, ir
    )


def _types_are_compatible(a, b):
    """Returns true if a and b have compatible types."""
    if a.type.WhichOneof("type") != b.type.WhichOneof("type"):
        return False
    elif a.type.WhichOneof("type") == "enumeration":
        return ir_util.hashable_form_of_reference(
            a.type.enumeration.name
        ) == ir_util.hashable_form_of_reference(b.type.enumeration.name)
    elif a.type.WhichOneof("type") in ("integer", "boolean"):
        # All integers are compatible with integers; booleans are compatible with
        # booleans
        return True
    else:
        assert False, "_types_are_compatible works with enums, integers, booleans."


def _type_check_comparison_operator(expression, source_file_name, errors):
    """Checks the type of a comparison operator (==, !=, <, >, >=, <=)."""
    # Applying less than or greater than to a boolean is likely a mistake, so
    # only equality and inequality are allowed for booleans.
    if expression.function.function in (
        ir_data.FunctionMapping.EQUALITY,
        ir_data.FunctionMapping.INEQUALITY,
    ):
        acceptable_types = ("integer", "boolean", "enumeration")
        acceptable_types_for_humans = "an integer, boolean, or enum"
    else:
        acceptable_types = ("integer", "enumeration")
        acceptable_types_for_humans = "an integer or enum"
    left = expression.function.args[0]
    right = expression.function.args[1]
    for argument, name in ((left, "Left"), (right, "Right")):
        if argument.type.WhichOneof("type") not in acceptable_types:
            errors.append(
                [
                    error.error(
                        source_file_name,
                        argument.source_location,
                        "{} argument of operator '{}' must be {}.".format(
                            name,
                            expression.function.function_name.text,
                            acceptable_types_for_humans,
                        ),
                    )
                ]
            )
            return
    if not _types_are_compatible(left, right):
        errors.append(
            [
                error.error(
                    source_file_name,
                    expression.source_location,
                    "Both arguments of operator '{}' must have the same "
                    "type.".format(expression.function.function_name.text),
                )
            ]
        )
    _annotate_as_boolean(expression)


def _type_check_choice_operator(expression, source_file_name, errors):
    """Checks the type of the choice operator cond ? if_true : if_false."""
    condition = expression.function.args[0]
    if condition.type.WhichOneof("type") != "boolean":
        errors.append(
            [
                error.error(
                    source_file_name,
                    condition.source_location,
                    "Condition of operator '?:' must be a boolean.",
                )
            ]
        )
    if_true = expression.function.args[1]
    if if_true.type.WhichOneof("type") not in ("integer", "boolean", "enumeration"):
        errors.append(
            [
                error.error(
                    source_file_name,
                    if_true.source_location,
                    "If-true clause of operator '?:' must be an integer, "
                    "boolean, or enum.",
                )
            ]
        )
        return
    if_false = expression.function.args[2]
    if not _types_are_compatible(if_true, if_false):
        errors.append(
            [
                error.error(
                    source_file_name,
                    expression.source_location,
                    "The if-true and if-false clauses of operator '?:' must "
                    "have the same type.",
                )
            ]
        )
    if if_true.type.WhichOneof("type") == "integer":
        _annotate_as_integer(expression)
    elif if_true.type.WhichOneof("type") == "boolean":
        _annotate_as_boolean(expression)
    elif if_true.type.WhichOneof("type") == "enumeration":
        ir_data_utils.builder(expression).type.enumeration.name.CopyFrom(
            if_true.type.enumeration.name
        )
    else:
        assert False, "Unexpected type for if_true."


def _type_check_boolean_constant(expression):
    _annotate_as_boolean(expression)


def _type_check_builtin_reference(expression):
    name = expression.builtin_reference.canonical_name.object_path[0]
    if name == "$is_statically_sized":
        _annotate_as_boolean(expression)
    elif name == "$static_size_in_bits":
        _annotate_as_integer(expression)
    else:
        assert False, "Unknown builtin '{}'.".format(name)


def _type_check_array_size(expression, source_file_name, errors):
    _type_check_integer(expression, source_file_name, errors, "Array size")


def _type_check_field_location(location, source_file_name, errors):
    _type_check_integer(location.start, source_file_name, errors, "Start of field")
    _type_check_integer(location.size, source_file_name, errors, "Size of field")


def _type_check_field_existence_condition(field, source_file_name, errors):
    _type_check_boolean(
        field.existence_condition, source_file_name, errors, "Existence condition"
    )


def _type_name_for_error_messages(expression_type):
    if expression_type.WhichOneof("type") == "integer":
        return "integer"
    elif expression_type.WhichOneof("type") == "enumeration":
        # TODO(bolms): Should this be the fully-qualified name?
        return expression_type.enumeration.name.canonical_name.object_path[-1]
    assert False, "Shouldn't be here."


def _type_check_passed_parameters(atomic_type, ir, source_file_name, errors):
    """Checks the types of parameters to a parameterized physical type."""
    referenced_type = ir_util.find_object(atomic_type.reference.canonical_name, ir)
    if len(referenced_type.runtime_parameter) != len(atomic_type.runtime_parameter):
        errors.append(
            [
                error.error(
                    source_file_name,
                    atomic_type.source_location,
                    "Type {} requires {} parameter{}; {} parameter{} given.".format(
                        referenced_type.name.name.text,
                        len(referenced_type.runtime_parameter),
                        "" if len(referenced_type.runtime_parameter) == 1 else "s",
                        len(atomic_type.runtime_parameter),
                        "" if len(atomic_type.runtime_parameter) == 1 else "s",
                    ),
                ),
                error.note(
                    atomic_type.reference.canonical_name.module_file,
                    referenced_type.source_location,
                    "Definition of type {}.".format(referenced_type.name.name.text),
                ),
            ]
        )
        return
    for i in range(len(referenced_type.runtime_parameter)):
        if referenced_type.runtime_parameter[i].type.WhichOneof("type") not in (
            "integer",
            "boolean",
            "enumeration",
        ):
            # _type_check_parameter will catch invalid parameter types at the
            # definition site; no need for another, probably-confusing error at any
            # usage sites.
            continue
        if atomic_type.runtime_parameter[i].type.WhichOneof(
            "type"
        ) != referenced_type.runtime_parameter[i].type.WhichOneof("type"):
            errors.append(
                [
                    error.error(
                        source_file_name,
                        atomic_type.runtime_parameter[i].source_location,
                        "Parameter {} of type {} must be {}, not {}.".format(
                            i,
                            referenced_type.name.name.text,
                            _type_name_for_error_messages(
                                referenced_type.runtime_parameter[i].type
                            ),
                            _type_name_for_error_messages(
                                atomic_type.runtime_parameter[i].type
                            ),
                        ),
                    ),
                    error.note(
                        atomic_type.reference.canonical_name.module_file,
                        referenced_type.runtime_parameter[i].source_location,
                        "Parameter {} of {}.".format(i, referenced_type.name.name.text),
                    ),
                ]
            )


def _type_check_parameter(runtime_parameter, source_file_name, errors):
    """Checks the type of a parameter to a physical type."""
    if runtime_parameter.type.WhichOneof("type") not in ("integer", "enumeration"):
        errors.append(
            [
                error.error(
                    source_file_name,
                    runtime_parameter.physical_type_alias.source_location,
                    "Runtime parameters must be integer or enum.",
                )
            ]
        )


def annotate_types(ir):
    """Adds type annotations to all expressions in ir.

    annotate_types adds type information to all expressions (and subexpressions)
    in the IR.  Additionally, it checks expressions for internal type consistency:
    it will generate an error for constructs like "1 + true", where the types of
    the operands are not accepted by the operator.

    Arguments:
        ir: an IR to which to add type annotations

    Returns:
        A (possibly empty) list of errors.
    """
    errors = []
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Expression],
        _type_check_expression,
        skip_descendants_of={ir_data.Expression},
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.RuntimeParameter],
        _annotate_parameter_type,
        parameters={"errors": errors},
    )
    return errors


def check_types(ir):
    """Checks that expressions within the IR have the correct top-level types.

    check_types ensures that expressions at the top level have correct types; in
    particular, it ensures that array sizes are integers ("UInt[true]" is not a
    valid array type) and that the starts and ends of ranges are integers.

    Arguments:
        ir: an IR to type check.

    Returns:
        A (possibly empty) list of errors.
    """
    errors = []
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.FieldLocation],
        _type_check_field_location,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.ArrayType, ir_data.Expression],
        _type_check_array_size,
        skip_descendants_of={ir_data.AtomicType},
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Field],
        _type_check_field_existence_condition,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.RuntimeParameter],
        _type_check_parameter,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.AtomicType],
        _type_check_passed_parameters,
        parameters={"errors": errors},
    )
    return errors
