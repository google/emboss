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

"""Routines to check miscellaneous constraints on the IR."""

from compiler.front_end import attributes
from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import ir_util
from compiler.util import resources
from compiler.util import traverse_ir


def _render_type(type_ir, ir):
    """Returns the human-readable notation of the given type."""
    assert type_ir.HasField(
        "atomic_type"
    ), "TODO(bolms): Implement _render_type for array types."
    if type_ir.HasField("size_in_bits"):
        return _render_atomic_type_name(
            type_ir, ir, suffix=":" + str(ir_util.constant_value(type_ir.size_in_bits))
        )
    else:
        return _render_atomic_type_name(type_ir, ir)


def _render_atomic_type_name(type_ir, ir, suffix=None):
    assert type_ir.HasField(
        "atomic_type"
    ), "_render_atomic_type_name() requires an atomic type"
    if not suffix:
        suffix = ""
    type_definition = ir_util.find_object(type_ir.atomic_type.reference, ir)
    if type_definition.name.is_anonymous:
        return "anonymous type"
    else:
        return "type '{}{}'".format(type_definition.name.name.text, suffix)


def _check_that_inner_array_dimensions_are_constant(type_ir, source_file_name, errors):
    """Checks that inner array dimensions are constant."""
    if type_ir.WhichOneof("size") == "automatic":
        errors.append(
            [
                error.error(
                    source_file_name,
                    ir_data_utils.reader(type_ir).element_count.source_location,
                    "Array dimensions can only be omitted for the outermost dimension.",
                )
            ]
        )
    elif type_ir.WhichOneof("size") == "element_count":
        if not ir_util.is_constant(type_ir.element_count):
            errors.append(
                [
                    error.error(
                        source_file_name,
                        type_ir.element_count.source_location,
                        "Inner array dimensions must be constant.",
                    )
                ]
            )
    else:
        assert False, 'Expected "element_count" or "automatic" array size.'


def _check_that_array_base_types_are_fixed_size(type_ir, source_file_name, errors, ir):
    """Checks that the sizes of array elements are known at compile time."""
    if type_ir.base_type.HasField("array_type"):
        # An array is fixed size if its base_type is fixed size and its array
        # dimension is constant.  This function will be called again on the inner
        # array, and we do not want to cascade errors if the inner array's base_type
        # is not fixed size.  The array dimensions are separately checked by
        # _check_that_inner_array_dimensions_are_constant, which will provide an
        # appropriate error message for that case.
        return
    assert type_ir.base_type.HasField("atomic_type")
    if type_ir.base_type.HasField("size_in_bits"):
        # If the base_type has a size_in_bits, then it is fixed size.
        return
    base_type = ir_util.find_object(type_ir.base_type.atomic_type.reference, ir)
    base_type_fixed_size = ir_util.get_integer_attribute(
        base_type.attribute, attributes.FIXED_SIZE
    )
    if base_type_fixed_size is None:
        errors.append(
            [
                error.error(
                    source_file_name,
                    type_ir.base_type.atomic_type.source_location,
                    "Array elements must be fixed size.",
                )
            ]
        )


def _check_that_array_base_types_in_structs_are_multiples_of_bytes(
    type_ir, type_definition, source_file_name, errors, ir
):
    # TODO(bolms): Remove this limitation.
    """Checks that the sizes of array elements are multiples of 8 bits."""
    if type_ir.base_type.HasField("array_type"):
        # Only check the innermost array for multidimensional arrays.
        return
    assert type_ir.base_type.HasField("atomic_type")
    if type_ir.base_type.HasField("size_in_bits"):
        assert ir_util.is_constant(type_ir.base_type.size_in_bits)
        base_type_size = ir_util.constant_value(type_ir.base_type.size_in_bits)
    else:
        fixed_size = ir_util.fixed_size_of_type_in_bits(type_ir.base_type, ir)
        if fixed_size is None:
            # Variable-sized elements are checked elsewhere.
            return
        base_type_size = fixed_size
    if base_type_size % type_definition.addressable_unit != 0:
        assert type_definition.addressable_unit == ir_data.AddressableUnit.BYTE
        errors.append(
            [
                error.error(
                    source_file_name,
                    type_ir.base_type.source_location,
                    "Array elements in structs must have sizes "
                    "which are a multiple of 8 bits.",
                )
            ]
        )


def _check_constancy_of_constant_references(expression, source_file_name, errors, ir):
    """Checks that constant_references are constant."""
    if expression.WhichOneof("expression") != "constant_reference":
        return
    # This is a bit of a hack: really, we want to know that the referred-to object
    # has no dependencies on any instance variables of its parent structure; i.e.,
    # that its value does not depend on having a view of the structure.
    if not ir_util.is_constant_type(expression.type):
        referred_name = expression.constant_reference.canonical_name
        referred_object = ir_util.find_object(referred_name, ir)
        errors.append(
            [
                error.error(
                    source_file_name,
                    expression.source_location,
                    "Static references must refer to constants.",
                ),
                error.note(
                    referred_name.module_file,
                    referred_object.source_location,
                    "{} is not constant.".format(referred_name.object_path[-1]),
                ),
            ]
        )


def _check_that_enum_values_are_representable(
    enum_type, type_definition, source_file_name, errors
):
    """Checks that enumeration values can fit in their specified int type."""
    values = []
    max_enum_size = ir_util.get_integer_attribute(
        type_definition.attribute, attributes.ENUM_MAXIMUM_BITS
    )
    is_signed = ir_util.get_boolean_attribute(
        type_definition.attribute, attributes.IS_SIGNED
    )
    if is_signed:
        enum_range = (-(2 ** (max_enum_size - 1)), 2 ** (max_enum_size - 1) - 1)
    else:
        enum_range = (0, 2**max_enum_size - 1)
    for value in enum_type.value:
        values.append((ir_util.constant_value(value.value), value))
    out_of_range = [v for v in values if not enum_range[0] <= v[0] <= enum_range[1]]
    # If all values are in range, this loop will have zero iterations.
    for value in out_of_range:
        errors.append(
            [
                error.error(
                    source_file_name,
                    value[1].value.source_location,
                    "Value {} is out of range for {}-bit {} enumeration.".format(
                        value[0], max_enum_size, "signed" if is_signed else "unsigned"
                    ),
                )
            ]
        )


def _field_size(field, type_definition):
    """Calculates the size of the given field in bits, if it is constant."""
    size = ir_util.constant_value(field.location.size)
    if size is None:
        return None
    return size * type_definition.addressable_unit


def _check_type_requirements_for_field(
    type_ir, type_definition, field, ir, source_file_name, errors
):
    """Checks that the `requires` attribute of each field's type is fulfilled."""
    if not type_ir.HasField("atomic_type"):
        return

    if field.type.HasField("atomic_type"):
        field_min_size = (
            int(field.location.size.type.integer.minimum_value)
            * type_definition.addressable_unit
        )
        field_max_size = (
            int(field.location.size.type.integer.maximum_value)
            * type_definition.addressable_unit
        )
        field_is_atomic = True
    else:
        field_is_atomic = False

    if type_ir.HasField("size_in_bits"):
        element_size = ir_util.constant_value(type_ir.size_in_bits)
    else:
        element_size = None

    referenced_type_definition = ir_util.find_object(type_ir.atomic_type.reference, ir)
    type_is_anonymous = referenced_type_definition.name.is_anonymous
    type_size_attr = ir_util.get_attribute(
        referenced_type_definition.attribute, attributes.FIXED_SIZE
    )
    if type_size_attr:
        type_size = ir_util.constant_value(type_size_attr.expression)
    else:
        type_size = None

    if element_size is not None and type_size is not None and element_size != type_size:
        errors.append(
            [
                error.error(
                    source_file_name,
                    type_ir.size_in_bits.source_location,
                    "Explicit size of {} bits does not match fixed size ({} bits) of "
                    "{}.".format(
                        element_size, type_size, _render_atomic_type_name(type_ir, ir)
                    ),
                ),
                error.note(
                    type_ir.atomic_type.reference.canonical_name.module_file,
                    type_size_attr.source_location,
                    "Size specified here.",
                ),
            ]
        )
        return

    # If the type had no size specifier (the ':32' in 'UInt:32'), but the type is
    # fixed size, then continue as if the type's size were explicitly stated.
    if element_size is None:
        element_size = type_size

    # TODO(bolms): When the full dynamic size expression for types is generated,
    # add a check that dynamically-sized types can, at least potentially, fit in
    # their fields.

    if field_is_atomic and element_size is not None:
        # If the field has a fixed size, and the (atomic) type contained therein is
        # also fixed size, then the sizes should match.
        #
        # TODO(bolms): Maybe change the case where the field is bigger than
        # necessary into a warning?
        if field_max_size == field_min_size and (
            element_size > field_max_size
            or (element_size < field_min_size and not type_is_anonymous)
        ):
            errors.append(
                [
                    error.error(
                        source_file_name,
                        type_ir.source_location,
                        "Fixed-size {} cannot be placed in field of size {} bits; "
                        "requires {} bits.".format(
                            _render_type(type_ir, ir), field_max_size, element_size
                        ),
                    )
                ]
            )
            return
        elif element_size > field_max_size:
            errors.append(
                [
                    error.error(
                        source_file_name,
                        type_ir.source_location,
                        "Field of maximum size {} bits cannot hold fixed-size {}, which "
                        "requires {} bits.".format(
                            field_max_size, _render_type(type_ir, ir), element_size
                        ),
                    )
                ]
            )
            return

    # If we're here, then field/type sizes are consistent.
    if element_size is None and field_is_atomic and field_min_size == field_max_size:
        # From here down, we just use element_size.
        element_size = field_min_size

    errors.extend(
        _check_physical_type_requirements(
            type_ir, field.source_location, element_size, ir, source_file_name
        )
    )


def _check_type_requirements_for_parameter_type(
    runtime_parameter, ir, source_file_name, errors
):
    """Checks that the type of a parameter is valid."""
    physical_type = runtime_parameter.physical_type_alias
    logical_type = runtime_parameter.type
    size = ir_util.constant_value(physical_type.size_in_bits)
    if logical_type.WhichOneof("type") == "integer":
        integer_errors = _integer_bounds_errors(
            logical_type.integer,
            "parameter",
            source_file_name,
            physical_type.source_location,
        )
        if integer_errors:
            errors.extend(integer_errors)
            return
        errors.extend(
            _check_physical_type_requirements(
                physical_type,
                runtime_parameter.source_location,
                size,
                ir,
                source_file_name,
            )
        )
    elif logical_type.WhichOneof("type") == "enumeration":
        if physical_type.HasField("size_in_bits"):
            # This seems a little weird: for `UInt`, `Int`, etc., the explicit size is
            # required, but for enums it is banned.  This is because enums have a
            # "native" 64-bit size in expressions, so the physical size is just
            # ignored.
            errors.extend(
                [
                    [
                        error.error(
                            source_file_name,
                            physical_type.size_in_bits.source_location,
                            "Parameters with enum type may not have explicit size.",
                        )
                    ]
                ]
            )
    else:
        assert False, "Non-integer/enum parameters should have been caught earlier."


def _check_physical_type_requirements(
    type_ir, usage_source_location, size, ir, source_file_name
):
    """Checks that the given atomic `type_ir` is allowed to be `size` bits."""
    referenced_type_definition = ir_util.find_object(type_ir.atomic_type.reference, ir)
    if referenced_type_definition.HasField("enumeration"):
        if size is None:
            return [
                [
                    error.error(
                        source_file_name,
                        type_ir.source_location,
                        "Enumeration {} cannot be placed in a dynamically-sized "
                        "field.".format(_render_type(type_ir, ir)),
                    )
                ]
            ]
        else:
            max_enum_size = ir_util.get_integer_attribute(
                referenced_type_definition.attribute, attributes.ENUM_MAXIMUM_BITS
            )
            if size < 1 or size > max_enum_size:
                return [
                    [
                        error.error(
                            source_file_name,
                            type_ir.source_location,
                            "Enumeration {} cannot be {} bits; {} must be between "
                            "1 and {} bits, inclusive.".format(
                                _render_atomic_type_name(type_ir, ir),
                                size,
                                _render_atomic_type_name(type_ir, ir),
                                max_enum_size,
                            ),
                        )
                    ]
                ]

    if size is None:
        bindings = {"$is_statically_sized": False}
    else:
        bindings = {"$is_statically_sized": True, "$static_size_in_bits": size}
    requires_attr = ir_util.get_attribute(
        referenced_type_definition.attribute, attributes.STATIC_REQUIREMENTS
    )
    if requires_attr and not ir_util.constant_value(requires_attr.expression, bindings):
        # TODO(bolms): Figure out a better way to build this error message.
        # The "Requirements specified here." message should print out the actual
        # source text of the requires attribute, so that should help, but it's still
        # a bit generic and unfriendly.
        return [
            [
                error.error(
                    source_file_name,
                    usage_source_location,
                    "Requirements of {} not met.".format(
                        type_ir.atomic_type.reference.canonical_name.object_path[-1]
                    ),
                ),
                error.note(
                    type_ir.atomic_type.reference.canonical_name.module_file,
                    requires_attr.source_location,
                    "Requirements specified here.",
                ),
            ]
        ]
    return []


def _check_allowed_in_bits(type_ir, type_definition, source_file_name, ir, errors):
    """Verifies that atomic fields have types that are allowed in `bits`."""
    if not type_ir.HasField("atomic_type"):
        return
    referenced_type_definition = ir_util.find_object(type_ir.atomic_type.reference, ir)
    if (
        type_definition.addressable_unit % referenced_type_definition.addressable_unit
        != 0
    ):
        assert type_definition.addressable_unit == ir_data.AddressableUnit.BIT
        assert (
            referenced_type_definition.addressable_unit == ir_data.AddressableUnit.BYTE
        )
        errors.append(
            [
                error.error(
                    source_file_name,
                    type_ir.source_location,
                    "Byte-oriented {} cannot be used in a bits field.".format(
                        _render_type(type_ir, ir)
                    ),
                )
            ]
        )


def _check_size_of_bits(type_ir, type_definition, source_file_name, errors):
    """Checks that `bits` types are fixed size, less than 64 bits."""
    del type_ir  # Unused
    if type_definition.addressable_unit != ir_data.AddressableUnit.BIT:
        return
    fixed_size = ir_util.get_integer_attribute(
        type_definition.attribute, attributes.FIXED_SIZE
    )
    if fixed_size is None:
        errors.append(
            [
                error.error(
                    source_file_name,
                    type_definition.source_location,
                    "`bits` types must be fixed size.",
                )
            ]
        )
        return
    if fixed_size > 64:
        errors.append(
            [
                error.error(
                    source_file_name,
                    type_definition.source_location,
                    "`bits` types must be 64 bits or smaller.",
                )
            ]
        )


_RESERVED_WORDS = None


def get_reserved_word_list():
    if _RESERVED_WORDS is None:
        _initialize_reserved_word_list()
    return _RESERVED_WORDS


def _initialize_reserved_word_list():
    global _RESERVED_WORDS
    _RESERVED_WORDS = {}
    language = None
    for line in resources.load("compiler.front_end", "reserved_words").splitlines():
        stripped_line = line.partition("#")[0].strip()
        if not stripped_line:
            continue
        if stripped_line.startswith("--"):
            language = stripped_line.partition("--")[2].strip()
        else:
            # For brevity's sake, only use the first language for error messages.
            if stripped_line not in _RESERVED_WORDS:
                _RESERVED_WORDS[stripped_line] = language


def _check_name_for_reserved_words(obj, source_file_name, errors, context_name):
    if obj.name.name.text in get_reserved_word_list():
        errors.append(
            [
                error.error(
                    source_file_name,
                    obj.name.name.source_location,
                    "{} reserved word may not be used as {}.".format(
                        get_reserved_word_list()[obj.name.name.text], context_name
                    ),
                )
            ]
        )


def _check_field_name_for_reserved_words(field, source_file_name, errors):
    return _check_name_for_reserved_words(
        field, source_file_name, errors, "a field name"
    )


def _check_enum_name_for_reserved_words(enum, source_file_name, errors):
    return _check_name_for_reserved_words(
        enum, source_file_name, errors, "an enum name"
    )


def _check_type_name_for_reserved_words(type_definition, source_file_name, errors):
    return _check_name_for_reserved_words(
        type_definition, source_file_name, errors, "a type name"
    )


def _bounds_can_fit_64_bit_unsigned(minimum, maximum):
    return minimum >= 0 and maximum <= 2**64 - 1


def _bounds_can_fit_64_bit_signed(minimum, maximum):
    return minimum >= -(2**63) and maximum <= 2**63 - 1


def _bounds_can_fit_any_64_bit_integer_type(minimum, maximum):
    return _bounds_can_fit_64_bit_unsigned(
        minimum, maximum
    ) or _bounds_can_fit_64_bit_signed(minimum, maximum)


def _integer_bounds_errors_for_expression(expression, source_file_name):
    """Checks that `expression` is in range for int64_t or uint64_t."""
    # Only check non-constant subexpressions.
    if expression.WhichOneof(
        "expression"
    ) == "function" and not ir_util.is_constant_type(expression.type):
        errors = []
        for arg in expression.function.args:
            errors += _integer_bounds_errors_for_expression(arg, source_file_name)
        if errors:
            # Don't cascade bounds errors: report them at the lowest level they
            # appear.
            return errors
    if expression.type.WhichOneof("type") == "integer":
        errors = _integer_bounds_errors(
            expression.type.integer,
            "expression",
            source_file_name,
            expression.source_location,
        )
        if errors:
            return errors
    if expression.WhichOneof(
        "expression"
    ) == "function" and not ir_util.is_constant_type(expression.type):
        int64_only_clauses = []
        uint64_only_clauses = []
        for clause in [expression] + list(expression.function.args):
            if clause.type.WhichOneof("type") == "integer":
                arg_minimum = int(clause.type.integer.minimum_value)
                arg_maximum = int(clause.type.integer.maximum_value)
                if not _bounds_can_fit_64_bit_signed(arg_minimum, arg_maximum):
                    uint64_only_clauses.append(clause)
                elif not _bounds_can_fit_64_bit_unsigned(arg_minimum, arg_maximum):
                    int64_only_clauses.append(clause)
        if int64_only_clauses and uint64_only_clauses:
            error_set = [
                error.error(
                    source_file_name,
                    expression.source_location,
                    "Either all arguments to '{}' and its result must fit in a "
                    "64-bit unsigned integer, or all must fit in a 64-bit signed "
                    "integer.".format(expression.function.function_name.text),
                )
            ]
            for signedness, clause_list in (
                ("unsigned", uint64_only_clauses),
                ("signed", int64_only_clauses),
            ):
                for clause in clause_list:
                    error_set.append(
                        error.note(
                            source_file_name,
                            clause.source_location,
                            "Requires {} 64-bit integer.".format(signedness),
                        )
                    )
            return [error_set]
    return []


def _integer_bounds_errors(bounds, name, source_file_name, error_source_location):
    """Returns appropriate errors, if any, for the given integer bounds."""
    assert bounds.minimum_value, "{}".format(bounds)
    assert bounds.maximum_value, "{}".format(bounds)
    if bounds.minimum_value == "-infinity" or bounds.maximum_value == "infinity":
        return [
            [
                error.error(
                    source_file_name,
                    error_source_location,
                    "Integer range of {} must not be unbounded; it must fit "
                    "in a 64-bit signed or unsigned integer.".format(name),
                )
            ]
        ]
    if not _bounds_can_fit_any_64_bit_integer_type(
        int(bounds.minimum_value), int(bounds.maximum_value)
    ):
        if int(bounds.minimum_value) == int(bounds.maximum_value):
            return [
                [
                    error.error(
                        source_file_name,
                        error_source_location,
                        "Constant value {} of {} cannot fit in a 64-bit signed or "
                        "unsigned integer.".format(bounds.minimum_value, name),
                    )
                ]
            ]
        else:
            return [
                [
                    error.error(
                        source_file_name,
                        error_source_location,
                        "Potential range of {} is {} to {}, which cannot fit "
                        "in a 64-bit signed or unsigned integer.".format(
                            name, bounds.minimum_value, bounds.maximum_value
                        ),
                    )
                ]
            ]
    return []


def _check_bounds_on_runtime_integer_expressions(
    expression, source_file_name, in_attribute, errors
):
    if in_attribute and in_attribute.name.text == attributes.STATIC_REQUIREMENTS:
        # [static_requirements] is never evaluated at runtime, and $size_in_bits is
        # unbounded, so it should not be checked.
        return
    # The logic for gathering errors and suppressing cascades is simpler if
    # errors are just returned, rather than appended to a shared list.
    errors += _integer_bounds_errors_for_expression(expression, source_file_name)


def _attribute_in_attribute_action(a):
    return {"in_attribute": a}


def check_constraints(ir):
    """Checks miscellaneous validity constraints in ir.

    Checks that auto array sizes are only used for the outermost size of
    multidimensional arrays.  That is, Type[3][] is OK, but Type[][3] is not.

    Checks that fixed-size fields are a correct size to hold statically-sized
    types.

    Checks that inner array dimensions are constant.

    Checks that only constant-size types are used in arrays.

    Arguments:
      ir: An ir_data.EmbossIr object to check.

    Returns:
      A list of ConstraintViolations, or an empty list if there are none.
    """
    errors = []
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Structure, ir_data.Type],
        _check_allowed_in_bits,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        # TODO(bolms): look for [ir_data.ArrayType], [ir_data.AtomicType], and
        # simplify _check_that_array_base_types_are_fixed_size.
        ir,
        [ir_data.ArrayType],
        _check_that_array_base_types_are_fixed_size,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Structure, ir_data.ArrayType],
        _check_that_array_base_types_in_structs_are_multiples_of_bytes,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.ArrayType, ir_data.ArrayType],
        _check_that_inner_array_dimensions_are_constant,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir, [ir_data.Structure], _check_size_of_bits, parameters={"errors": errors}
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Structure, ir_data.Type],
        _check_type_requirements_for_field,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Field],
        _check_field_name_for_reserved_words,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.EnumValue],
        _check_enum_name_for_reserved_words,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.TypeDefinition],
        _check_type_name_for_reserved_words,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Expression],
        _check_constancy_of_constant_references,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Enum],
        _check_that_enum_values_are_representable,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Expression],
        _check_bounds_on_runtime_integer_expressions,
        incidental_actions={ir_data.Attribute: _attribute_in_attribute_action},
        skip_descendants_of={ir_data.EnumValue, ir_data.Expression},
        parameters={"errors": errors, "in_attribute": None},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.RuntimeParameter],
        _check_type_requirements_for_parameter_type,
        parameters={"errors": errors},
    )
    return errors
