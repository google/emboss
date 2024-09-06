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

"""Utility functions for reading and manipulating Emboss IR."""

import operator

from compiler.util import ir_data
from compiler.util import ir_data_utils


_FIXED_SIZE_ATTRIBUTE = "fixed_size_in_bits"


def get_attribute(attribute_list, name):
    """Finds name in attribute_list and returns a AttributeValue or None."""
    if not attribute_list:
        return None
    attribute_value = None
    for attr in attribute_list:
        if attr.name.text == name and not attr.is_default:
            assert attribute_value is None, 'Duplicate attribute "{}".'.format(name)
            attribute_value = attr.value
    return attribute_value


def get_boolean_attribute(attribute_list, name, default_value=None):
    """Returns the boolean value of an attribute, if any, or default_value.

    Arguments:
        attribute_list: A list of attributes to search.
        name: The name of the desired attribute.
        default_value: A value to return if name is not found in attribute_list,
            or the attribute does not have a boolean value.

    Returns:
        The boolean value of the requested attribute, or default_value if the
        requested attribute is not found or has a non-boolean value.
    """
    attribute_value = get_attribute(attribute_list, name)
    if not attribute_value or not attribute_value.expression.HasField(
        "boolean_constant"
    ):
        return default_value
    return attribute_value.expression.boolean_constant.value


def get_integer_attribute(attribute_list, name, default_value=None):
    """Returns the integer value of an attribute, if any, or default_value.

    Arguments:
        attribute_list: A list of attributes to search.
        name: The name of the desired attribute.
        default_value: A value to return if name is not found in attribute_list,
            or the attribute does not have an integer value.

    Returns:
        The integer value of the requested attribute, or default_value if the
        requested attribute is not found or has a non-integer value.
    """
    attribute_value = get_attribute(attribute_list, name)
    if (
        not attribute_value
        or attribute_value.expression.type.WhichOneof("type") != "integer"
        or not is_constant(attribute_value.expression)
    ):
        return default_value
    return constant_value(attribute_value.expression)


def is_constant(expression, bindings=None):
    return constant_value(expression, bindings) is not None


def is_constant_type(expression_type):
    """Returns True if expression_type is inhabited by a single value."""
    expression_type = ir_data_utils.reader(expression_type)
    return (
        expression_type.integer.modulus == "infinity"
        or expression_type.boolean.HasField("value")
        or expression_type.enumeration.HasField("value")
    )


def constant_value(expression, bindings=None):
    """Evaluates expression with the given bindings."""
    if expression is None:
        return None
    expression = ir_data_utils.reader(expression)
    if expression.WhichOneof("expression") == "constant":
        return int(expression.constant.value or 0)
    elif expression.WhichOneof("expression") == "constant_reference":
        # We can't look up the constant reference without the IR, but by the time
        # constant_value is called, the actual values should have been propagated to
        # the type information.
        if expression.type.WhichOneof("type") == "integer":
            assert expression.type.integer.modulus == "infinity"
            return int(expression.type.integer.modular_value)
        elif expression.type.WhichOneof("type") == "boolean":
            assert expression.type.boolean.HasField("value")
            return expression.type.boolean.value
        elif expression.type.WhichOneof("type") == "enumeration":
            assert expression.type.enumeration.HasField("value")
            return int(expression.type.enumeration.value)
        else:
            assert False, "Unexpected expression type {}".format(
                expression.type.WhichOneof("type")
            )
    elif expression.WhichOneof("expression") == "function":
        return _constant_value_of_function(expression.function, bindings)
    elif expression.WhichOneof("expression") == "field_reference":
        return None
    elif expression.WhichOneof("expression") == "boolean_constant":
        return expression.boolean_constant.value
    elif expression.WhichOneof("expression") == "builtin_reference":
        name = expression.builtin_reference.canonical_name.object_path[0]
        if bindings and name in bindings:
            return bindings[name]
        else:
            return None
    elif expression.WhichOneof("expression") is None:
        return None
    else:
        assert False, "Unexpected expression kind {}".format(
            expression.WhichOneof("expression")
        )


def _constant_value_of_function(function, bindings):
    """Returns the constant value of evaluating `function`, or None."""
    values = [constant_value(arg, bindings) for arg in function.args]
    # Expressions like `$is_statically_sized && 1 <= $static_size_in_bits <= 64`
    # should return False, not None, if `$is_statically_sized` is false, even
    # though `$static_size_in_bits` is unknown.
    #
    # The easiest way to allow this is to use a three-way logic chart for each;
    # specifically:
    #
    # AND:      True     False    Unknown
    #         +--------------------------
    # True    | True     False    Unknown
    # False   | False    False    False
    # Unknown | Unknown  False    Unknown
    #
    # OR:       True     False    Unknown
    #         +--------------------------
    # True    | True     True     True
    # False   | True     False    Unknown
    # Unknown | True     Unknown  Unknown
    #
    # This raises the question of just how many constant-from-nonconstant
    # expressions Emboss should support.  There are, after all, a vast number of
    # constant expression patterns built from non-constant subexpressions, such as
    # `0 * X` or `X == X` or `3 * X == X + X + X`.  I (bolms@) am not implementing
    # any further special cases because I do not see any practical use for them.
    if function.function == ir_data.FunctionMapping.UNKNOWN:
        return None
    if function.function == ir_data.FunctionMapping.AND:
        if any(value is False for value in values):
            return False
        elif any(value is None for value in values):
            return None
        else:
            return True
    elif function.function == ir_data.FunctionMapping.OR:
        if any(value is True for value in values):
            return True
        elif any(value is None for value in values):
            return None
        else:
            return False
    elif function.function == ir_data.FunctionMapping.CHOICE:
        if values[0] is None:
            return None
        else:
            return values[1] if values[0] else values[2]
    # Other than the logical operators and choice operator, the result of any
    # function on an unknown value is, itself, considered unknown.
    if any(value is None for value in values):
        return None
    functions = {
        ir_data.FunctionMapping.ADDITION: operator.add,
        ir_data.FunctionMapping.SUBTRACTION: operator.sub,
        ir_data.FunctionMapping.MULTIPLICATION: operator.mul,
        ir_data.FunctionMapping.EQUALITY: operator.eq,
        ir_data.FunctionMapping.INEQUALITY: operator.ne,
        ir_data.FunctionMapping.LESS: operator.lt,
        ir_data.FunctionMapping.LESS_OR_EQUAL: operator.le,
        ir_data.FunctionMapping.GREATER: operator.gt,
        ir_data.FunctionMapping.GREATER_OR_EQUAL: operator.ge,
        # Python's max([1, 2]) == 2; max(1, 2) == 2; max([1]) == 1; but max(1)
        # throws a TypeError ("'int' object is not iterable").
        ir_data.FunctionMapping.MAXIMUM: lambda *x: max(x),
    }
    return functions[function.function](*values)


def _hashable_form_of_name(name):
    return (name.module_file,) + tuple(name.object_path)


def hashable_form_of_reference(reference):
    """Returns a representation of reference that can be used as a dict key.

    Arguments:
      reference: An ir_data.Reference or ir_data.NameDefinition.

    Returns:
      A tuple of the module_file and object_path.
    """
    return _hashable_form_of_name(reference.canonical_name)


def hashable_form_of_field_reference(field_reference):
    """Returns a representation of field_reference that can be used as a dict key.

    Arguments:
      field_reference: An ir_data.FieldReference

    Returns:
      A tuple of tuples of the module_files and object_paths.
    """
    return tuple(
        _hashable_form_of_name(reference.canonical_name)
        for reference in field_reference.path
    )


def is_array(type_ir):
    """Returns true if type_ir is an array type."""
    return type_ir.HasField("array_type")


def _find_path_in_structure_field(path, field):
    if not path:
        return field
    return None


def _find_path_in_structure(path, type_definition):
    for field in type_definition.structure.field:
        if field.name.name.text == path[0]:
            return _find_path_in_structure_field(path[1:], field)
    return None


def _find_path_in_enumeration(path, type_definition):
    if len(path) != 1:
        return None
    for value in type_definition.enumeration.value:
        if value.name.name.text == path[0]:
            return value
    return None


def _find_path_in_parameters(path, type_definition):
    if len(path) > 1 or not type_definition.HasField("runtime_parameter"):
        return None
    for parameter in type_definition.runtime_parameter:
        if ir_data_utils.reader(parameter).name.name.text == path[0]:
            return parameter
    return None


def _find_path_in_type_definition(path, type_definition):
    """Finds the object with the given path in the given type_definition."""
    if not path:
        return type_definition
    obj = _find_path_in_parameters(path, type_definition)
    if obj:
        return obj
    if type_definition.HasField("structure"):
        obj = _find_path_in_structure(path, type_definition)
    elif type_definition.HasField("enumeration"):
        obj = _find_path_in_enumeration(path, type_definition)
    if obj:
        return obj
    else:
        return _find_path_in_type_list(path, type_definition.subtype or [])


def _find_path_in_type_list(path, type_list):
    for type_definition in type_list:
        if type_definition.name.name.text == path[0]:
            return _find_path_in_type_definition(path[1:], type_definition)
    return None


def _find_path_in_module(path, module_ir):
    if not path:
        return module_ir
    return _find_path_in_type_list(path, module_ir.type)


def find_object_or_none(name, ir):
    """Finds the object with the given canonical name, if it exists.."""
    if isinstance(name, ir_data.Reference) or isinstance(name, ir_data.NameDefinition):
        path = _hashable_form_of_name(name.canonical_name)
    elif isinstance(name, ir_data.CanonicalName):
        path = _hashable_form_of_name(name)
    else:
        path = name

    for module in ir.module:
        if module.source_file_name == path[0]:
            return _find_path_in_module(path[1:], module)

    return None


def find_object(name, ir):
    """Finds the IR of the type, field, or value with the given canonical name."""
    result = find_object_or_none(name, ir)
    assert result is not None, "Bad reference {}".format(name)
    return result


def find_parent_object(name, ir):
    """Finds the parent object of the object with the given canonical name."""
    if isinstance(name, ir_data.Reference) or isinstance(name, ir_data.NameDefinition):
        path = _hashable_form_of_name(name.canonical_name)
    elif isinstance(name, ir_data.CanonicalName):
        path = _hashable_form_of_name(name)
    else:
        path = name
    return find_object(path[:-1], ir)


def get_base_type(type_ir):
    """Returns the base type of the given type.

    Arguments:
      type_ir: IR of a type reference.

    Returns:
      If type_ir corresponds to an atomic type (like "UInt"), returns type_ir.  If
      type_ir corresponds to an array type (like "UInt:8[12]" or "Square[8][8]"),
      returns the type after stripping off the array types ("UInt" or "Square").
    """
    while type_ir.HasField("array_type"):
        type_ir = type_ir.array_type.base_type
    assert type_ir.HasField("atomic_type"), "Unknown kind of type {}".format(type_ir)
    return type_ir


def fixed_size_of_type_in_bits(type_ir, ir):
    """Returns the fixed, known size for the given type, in bits, or None.

    Arguments:
      type_ir: The IR of a type.
      ir: A complete IR, used to resolve references to types.

    Returns:
      size if the size of the type can be determined, otherwise None.
    """
    array_multiplier = 1
    while type_ir.HasField("array_type"):
        if type_ir.array_type.WhichOneof("size") == "automatic":
            return None
        else:
            assert (
                type_ir.array_type.WhichOneof("size") == "element_count"
            ), 'Expected array size to be "automatic" or "element_count".'
        element_count = type_ir.array_type.element_count
        if not is_constant(element_count):
            return None
        else:
            array_multiplier *= constant_value(element_count)
        assert not type_ir.HasField(
            "size_in_bits"
        ), "TODO(bolms): implement explicitly-sized arrays"
        type_ir = type_ir.array_type.base_type
    assert type_ir.HasField("atomic_type"), "Unexpected type!"
    if type_ir.HasField("size_in_bits"):
        size = constant_value(type_ir.size_in_bits)
    else:
        type_definition = find_object(type_ir.atomic_type.reference, ir)
        size_attr = get_attribute(type_definition.attribute, _FIXED_SIZE_ATTRIBUTE)
        if not size_attr:
            return None
        size = constant_value(size_attr.expression)
    return size * array_multiplier


def field_is_virtual(field_ir):
    """Returns true if the field is virtual."""
    # TODO(bolms): Should there be a more explicit indicator that a field is
    # virtual?
    return not field_ir.HasField("location")


def field_is_read_only(field_ir):
    """Returns true if the field is read-only."""
    # For now, all virtual fields are read-only, and no non-virtual fields are
    # read-only.
    return ir_data_utils.reader(field_ir).write_method.read_only
