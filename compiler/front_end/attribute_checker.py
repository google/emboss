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

"""Module which adds and verifies attributes in Emboss IR.

The main entry point is normalize_and_verify(), which adds attributes and/or
verifies attributes which may have been manually entered.
"""

import re

from compiler.front_end import attributes
from compiler.front_end import type_check
from compiler.util import attribute_util
from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import ir_util
from compiler.util import traverse_ir


# Default value for maximum_bits on an `enum`.
_DEFAULT_ENUM_MAXIMUM_BITS = 64

# Default value for expected_back_ends -- mostly for legacy
_DEFAULT_BACK_ENDS = "cpp"

# Attribute type checkers
_VALID_BYTE_ORDER = attribute_util.string_from_list(
    {"BigEndian", "LittleEndian", "Null"}
)
_VALID_TEXT_OUTPUT = attribute_util.string_from_list({"Emit", "Skip"})


def _valid_back_ends(attr, module_source_file):
    """Checks that `attr` holds a valid list of back end specifiers."""
    if not re.fullmatch(
        r"(?:\s*[a-z][a-z0-9_]*\s*(?:,\s*[a-z][a-z0-9_]*\s*)*,?)?\s*",
        attr.value.string_constant.text,
    ):
        return [
            [
                error.error(
                    module_source_file,
                    attr.value.source_location,
                    "Attribute '{name}' must be a comma-delimited list of back end "
                    'specifiers (like "cpp, proto")), not "{value}".'.format(
                        name=attr.name.text, value=attr.value.string_constant.text
                    ),
                )
            ]
        ]
    return []


# Attributes must be the same type no matter where they occur.
_ATTRIBUTE_TYPES = {
    attributes.ADDRESSABLE_UNIT_SIZE: attribute_util.INTEGER_CONSTANT,
    attributes.BYTE_ORDER: _VALID_BYTE_ORDER,
    attributes.ENUM_MAXIMUM_BITS: attribute_util.INTEGER_CONSTANT,
    attributes.FIXED_SIZE: attribute_util.INTEGER_CONSTANT,
    attributes.IS_INTEGER: attribute_util.BOOLEAN_CONSTANT,
    attributes.IS_SIGNED: attribute_util.BOOLEAN_CONSTANT,
    attributes.REQUIRES: attribute_util.BOOLEAN,
    attributes.STATIC_REQUIREMENTS: attribute_util.BOOLEAN,
    attributes.TEXT_OUTPUT: _VALID_TEXT_OUTPUT,
    attributes.BACK_ENDS: _valid_back_ends,
}

_MODULE_ATTRIBUTES = {
    (attributes.BYTE_ORDER, True),
    (attributes.BACK_ENDS, False),
}
_BITS_ATTRIBUTES = {
    (attributes.FIXED_SIZE, False),
    (attributes.REQUIRES, False),
}
_STRUCT_ATTRIBUTES = {
    (attributes.FIXED_SIZE, False),
    (attributes.BYTE_ORDER, True),
    (attributes.REQUIRES, False),
}
_ENUM_ATTRIBUTES = {
    (attributes.ENUM_MAXIMUM_BITS, False),
    (attributes.IS_SIGNED, False),
}
_EXTERNAL_ATTRIBUTES = {
    (attributes.ADDRESSABLE_UNIT_SIZE, False),
    (attributes.FIXED_SIZE, False),
    (attributes.IS_INTEGER, False),
    (attributes.STATIC_REQUIREMENTS, False),
}
_STRUCT_PHYSICAL_FIELD_ATTRIBUTES = {
    (attributes.BYTE_ORDER, False),
    (attributes.REQUIRES, False),
    (attributes.TEXT_OUTPUT, False),
}
_STRUCT_VIRTUAL_FIELD_ATTRIBUTES = {
    (attributes.REQUIRES, False),
    (attributes.TEXT_OUTPUT, False),
}


def _construct_integer_attribute(name, value, source_location):
    """Constructs an integer Attribute with the given name and value."""
    attr_value = ir_data.AttributeValue(
        expression=ir_data.Expression(
            constant=ir_data.NumericConstant(
                value=str(value), source_location=source_location
            ),
            type=ir_data.ExpressionType(
                integer=ir_data.IntegerType(
                    modular_value=str(value),
                    modulus="infinity",
                    minimum_value=str(value),
                    maximum_value=str(value),
                )
            ),
            source_location=source_location,
        ),
        source_location=source_location,
    )
    return ir_data.Attribute(
        name=ir_data.Word(text=name, source_location=source_location),
        value=attr_value,
        source_location=source_location,
    )


def _construct_boolean_attribute(name, value, source_location):
    """Constructs a boolean Attribute with the given name and value."""
    attr_value = ir_data.AttributeValue(
        expression=ir_data.Expression(
            boolean_constant=ir_data.BooleanConstant(
                value=value, source_location=source_location
            ),
            type=ir_data.ExpressionType(boolean=ir_data.BooleanType(value=value)),
            source_location=source_location,
        ),
        source_location=source_location,
    )
    return ir_data.Attribute(
        name=ir_data.Word(text=name, source_location=source_location),
        value=attr_value,
        source_location=source_location,
    )


def _construct_string_attribute(name, value, source_location):
    """Constructs a string Attribute with the given name and value."""
    attr_value = ir_data.AttributeValue(
        string_constant=ir_data.String(text=value, source_location=source_location),
        source_location=source_location,
    )
    return ir_data.Attribute(
        name=ir_data.Word(text=name, source_location=source_location),
        value=attr_value,
        source_location=source_location,
    )


def _fixed_size_of_struct_or_bits(struct, unit_size):
    """Returns size of struct in bits or None, if struct is not fixed size."""
    size = 0
    for field in struct.field:
        if not field.HasField("location"):
            # Virtual fields do not contribute to the physical size of the struct.
            continue
        field_start = ir_util.constant_value(field.location.start)
        field_size = ir_util.constant_value(field.location.size)
        if field_start is None or field_size is None:
            # Technically, start + size could be constant even if start and size are
            # not; e.g. if start == x and size == 10 - x, but we don't handle that
            # here.
            return None
            # TODO(bolms): knows_own_size
            # TODO(bolms): compute min/max sizes for variable-sized arrays.
        field_end = field_start + field_size
        if field_end >= size:
            size = field_end
    return size * unit_size


def _verify_size_attributes_on_structure(
    struct, type_definition, source_file_name, errors
):
    """Verifies size attributes on a struct or bits."""
    fixed_size = _fixed_size_of_struct_or_bits(struct, type_definition.addressable_unit)
    fixed_size_attr = ir_util.get_attribute(
        type_definition.attribute, attributes.FIXED_SIZE
    )
    if not fixed_size_attr:
        return
    if fixed_size is None:
        errors.append(
            [
                error.error(
                    source_file_name,
                    fixed_size_attr.source_location,
                    "Struct is marked as fixed size, but contains variable-location "
                    "fields.",
                )
            ]
        )
    elif ir_util.constant_value(fixed_size_attr.expression) != fixed_size:
        errors.append(
            [
                error.error(
                    source_file_name,
                    fixed_size_attr.source_location,
                    "Struct is {} bits, but is marked as {} bits.".format(
                        fixed_size, ir_util.constant_value(fixed_size_attr.expression)
                    ),
                )
            ]
        )


# TODO(bolms): remove [fixed_size]; it is superseded by $size_in_{bits,bytes}
def _add_missing_size_attributes_on_structure(struct, type_definition):
    """Adds missing size attributes on a struct."""
    fixed_size = _fixed_size_of_struct_or_bits(struct, type_definition.addressable_unit)
    if fixed_size is None:
        return
    fixed_size_attr = ir_util.get_attribute(
        type_definition.attribute, attributes.FIXED_SIZE
    )
    if not fixed_size_attr:
        # TODO(bolms): Use the offset and length of the last field as the
        # source_location of the fixed_size attribute?
        type_definition.attribute.extend(
            [
                _construct_integer_attribute(
                    attributes.FIXED_SIZE, fixed_size, type_definition.source_location
                )
            ]
        )


def _field_needs_byte_order(field, type_definition, ir):
    """Returns true if the given field needs a byte_order attribute."""
    if ir_util.field_is_virtual(field):
        # Virtual fields have no physical type, and thus do not need a byte order.
        return False
    field_type = ir_util.find_object(
        ir_util.get_base_type(field.type).atomic_type.reference.canonical_name, ir
    )
    assert field_type is not None
    assert field_type.addressable_unit != ir_data.AddressableUnit.NONE
    return field_type.addressable_unit != type_definition.addressable_unit


def _field_may_have_null_byte_order(field, type_definition, ir):
    """Returns true if "Null" is a valid byte order for the given field."""
    # If the field is one unit in length, then byte order does not matter.
    if (
        ir_util.is_constant(field.location.size)
        and ir_util.constant_value(field.location.size) == 1
    ):
        return True
    unit = type_definition.addressable_unit
    # Otherwise, if the field's type is either a one-unit-sized type or an array
    # of a one-unit-sized type, then byte order does not matter.
    if (
        ir_util.fixed_size_of_type_in_bits(ir_util.get_base_type(field.type), ir)
        == unit
    ):
        return True
    # In all other cases, byte order does matter.
    return False


def _add_missing_byte_order_attribute_on_field(field, type_definition, ir, defaults):
    """Adds missing byte_order attributes to fields that need them."""
    if _field_needs_byte_order(field, type_definition, ir):
        byte_order_attr = ir_util.get_attribute(field.attribute, attributes.BYTE_ORDER)
        if byte_order_attr is None:
            if attributes.BYTE_ORDER in defaults:
                field.attribute.extend([defaults[attributes.BYTE_ORDER]])
            elif _field_may_have_null_byte_order(field, type_definition, ir):
                field.attribute.extend(
                    [
                        _construct_string_attribute(
                            attributes.BYTE_ORDER, "Null", field.source_location
                        )
                    ]
                )


def _add_missing_back_ends_to_module(module):
    """Sets the expected_back_ends attribute for a module, if not already set."""
    back_ends_attr = ir_util.get_attribute(module.attribute, attributes.BACK_ENDS)
    if back_ends_attr is None:
        module.attribute.extend(
            [
                _construct_string_attribute(
                    attributes.BACK_ENDS, _DEFAULT_BACK_ENDS, module.source_location
                )
            ]
        )


def _gather_expected_back_ends(module):
    """Captures the expected_back_ends attribute for `module`."""
    back_ends_attr = ir_util.get_attribute(module.attribute, attributes.BACK_ENDS)
    back_ends_str = back_ends_attr.string_constant.text
    return {"expected_back_ends": {x.strip() for x in back_ends_str.split(",")} | {""}}


def _add_addressable_unit_to_external(external, type_definition):
    """Sets the addressable_unit field for an external TypeDefinition."""
    # Strictly speaking, addressable_unit isn't an "attribute," but it's close
    # enough that it makes sense to handle it with attributes.
    del external  # Unused.
    size = ir_util.get_integer_attribute(
        type_definition.attribute, attributes.ADDRESSABLE_UNIT_SIZE
    )
    if size == 1:
        type_definition.addressable_unit = ir_data.AddressableUnit.BIT
    elif size == 8:
        type_definition.addressable_unit = ir_data.AddressableUnit.BYTE
    # If the addressable_unit_size is not in (1, 8), it will be caught by
    # _verify_addressable_unit_attribute_on_external, below.


def _add_missing_width_and_sign_attributes_on_enum(enum, type_definition):
    """Sets the maximum_bits and is_signed attributes for an enum, if needed."""
    max_bits_attr = ir_util.get_integer_attribute(
        type_definition.attribute, attributes.ENUM_MAXIMUM_BITS
    )
    if max_bits_attr is None:
        type_definition.attribute.extend(
            [
                _construct_integer_attribute(
                    attributes.ENUM_MAXIMUM_BITS,
                    _DEFAULT_ENUM_MAXIMUM_BITS,
                    type_definition.source_location,
                )
            ]
        )
    signed_attr = ir_util.get_boolean_attribute(
        type_definition.attribute, attributes.IS_SIGNED
    )
    if signed_attr is None:
        for value in enum.value:
            numeric_value = ir_util.constant_value(value.value)
            if numeric_value < 0:
                is_signed = True
                break
        else:
            is_signed = False
        type_definition.attribute.extend(
            [
                _construct_boolean_attribute(
                    attributes.IS_SIGNED, is_signed, type_definition.source_location
                )
            ]
        )


def _verify_byte_order_attribute_on_field(
    field, type_definition, source_file_name, ir, errors
):
    """Verifies the byte_order attribute on the given field."""
    byte_order_attr = ir_util.get_attribute(field.attribute, attributes.BYTE_ORDER)
    field_needs_byte_order = _field_needs_byte_order(field, type_definition, ir)
    if byte_order_attr and not field_needs_byte_order:
        errors.append(
            [
                error.error(
                    source_file_name,
                    byte_order_attr.source_location,
                    "Attribute 'byte_order' not allowed on field which is not byte order "
                    "dependent.",
                )
            ]
        )
    if not byte_order_attr and field_needs_byte_order:
        errors.append(
            [
                error.error(
                    source_file_name,
                    field.source_location,
                    "Attribute 'byte_order' required on field which is byte order "
                    "dependent.",
                )
            ]
        )
    if (
        byte_order_attr
        and byte_order_attr.string_constant.text == "Null"
        and not _field_may_have_null_byte_order(field, type_definition, ir)
    ):
        errors.append(
            [
                error.error(
                    source_file_name,
                    byte_order_attr.source_location,
                    "Attribute 'byte_order' may only be 'Null' for one-byte fields.",
                )
            ]
        )


def _verify_requires_attribute_on_field(field, source_file_name, ir, errors):
    """Verifies that [requires] is valid on the given field."""
    requires_attr = ir_util.get_attribute(field.attribute, attributes.REQUIRES)
    if not requires_attr:
        return
    if ir_util.field_is_virtual(field):
        field_expression_type = field.read_transform.type
    else:
        if not field.type.HasField("atomic_type"):
            errors.append(
                [
                    error.error(
                        source_file_name,
                        requires_attr.source_location,
                        "Attribute 'requires' is only allowed on integer, "
                        "enumeration, or boolean fields, not arrays.",
                    ),
                    error.note(
                        source_file_name, field.type.source_location, "Field type."
                    ),
                ]
            )
            return
        field_type = ir_util.find_object(field.type.atomic_type.reference, ir)
        assert field_type, "Field type should be non-None after name resolution."
        field_expression_type = type_check.unbounded_expression_type_for_physical_type(
            field_type
        )
    if field_expression_type.WhichOneof("type") not in (
        "integer",
        "enumeration",
        "boolean",
    ):
        errors.append(
            [
                error.error(
                    source_file_name,
                    requires_attr.source_location,
                    "Attribute 'requires' is only allowed on integer, enumeration, or "
                    "boolean fields.",
                )
            ]
        )


def _verify_addressable_unit_attribute_on_external(
    external, type_definition, source_file_name, errors
):
    """Verifies the addressable_unit_size attribute on an external."""
    del external  # Unused.
    addressable_unit_size_attr = ir_util.get_integer_attribute(
        type_definition.attribute, attributes.ADDRESSABLE_UNIT_SIZE
    )
    if addressable_unit_size_attr is None:
        errors.append(
            [
                error.error(
                    source_file_name,
                    type_definition.source_location,
                    "Expected '{}' attribute for external type.".format(
                        attributes.ADDRESSABLE_UNIT_SIZE
                    ),
                )
            ]
        )
    elif addressable_unit_size_attr not in (1, 8):
        errors.append(
            [
                error.error(
                    source_file_name,
                    type_definition.source_location,
                    "Only values '1' (bit) and '8' (byte) are allowed for the "
                    "'{}' attribute".format(attributes.ADDRESSABLE_UNIT_SIZE),
                )
            ]
        )


def _verify_width_attribute_on_enum(enum, type_definition, source_file_name, errors):
    """Verifies the maximum_bits attribute for an enum TypeDefinition."""
    del enum  # Unused.
    max_bits_value = ir_util.get_integer_attribute(
        type_definition.attribute, attributes.ENUM_MAXIMUM_BITS
    )
    # The attribute should already have been defaulted, if not originally present.
    assert max_bits_value is not None, "maximum_bits not set"
    if max_bits_value > 64 or max_bits_value < 1:
        max_bits_attr = ir_util.get_attribute(
            type_definition.attribute, attributes.ENUM_MAXIMUM_BITS
        )
        errors.append(
            [
                error.error(
                    source_file_name,
                    max_bits_attr.source_location,
                    "'maximum_bits' on an 'enum' must be between 1 and 64.",
                )
            ]
        )


def _add_missing_attributes_on_ir(ir):
    """Adds missing attributes in a complete IR."""
    traverse_ir.fast_traverse_ir_top_down(
        ir, [ir_data.Module], _add_missing_back_ends_to_module
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir, [ir_data.External], _add_addressable_unit_to_external
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir, [ir_data.Enum], _add_missing_width_and_sign_attributes_on_enum
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Structure],
        _add_missing_size_attributes_on_structure,
        incidental_actions={
            ir_data.Module: attribute_util.gather_default_attributes,
            ir_data.TypeDefinition: attribute_util.gather_default_attributes,
            ir_data.Field: attribute_util.gather_default_attributes,
        },
        parameters={"defaults": {}},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Field],
        _add_missing_byte_order_attribute_on_field,
        incidental_actions={
            ir_data.Module: attribute_util.gather_default_attributes,
            ir_data.TypeDefinition: attribute_util.gather_default_attributes,
            ir_data.Field: attribute_util.gather_default_attributes,
        },
        parameters={"defaults": {}},
    )
    return []


def _verify_field_attributes(field, type_definition, source_file_name, ir, errors):
    _verify_byte_order_attribute_on_field(
        field, type_definition, source_file_name, ir, errors
    )
    _verify_requires_attribute_on_field(field, source_file_name, ir, errors)


def _verify_back_end_attributes(
    attribute, expected_back_ends, source_file_name, errors
):
    back_end_text = ir_data_utils.reader(attribute).back_end.text
    if back_end_text not in expected_back_ends:
        expected_back_ends_for_error = expected_back_ends - {""}
        errors.append(
            [
                error.error(
                    source_file_name,
                    attribute.back_end.source_location,
                    "Back end specifier '{back_end}' does not match any expected back end "
                    "specifier for this file: '{expected_back_ends}'.  Add or update the "
                    "'[expected_back_ends: \"{new_expected_back_ends}\"]' attribute at the "
                    "file level if this back end specifier is intentional.".format(
                        back_end=attribute.back_end.text,
                        expected_back_ends="', '".join(
                            sorted(expected_back_ends_for_error)
                        ),
                        new_expected_back_ends=", ".join(
                            sorted(expected_back_ends_for_error | {back_end_text})
                        ),
                    ),
                )
            ]
        )


def _verify_attributes_on_ir(ir):
    """Verifies attributes in a complete IR."""
    errors = []
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Attribute],
        _verify_back_end_attributes,
        incidental_actions={
            ir_data.Module: _gather_expected_back_ends,
        },
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Structure],
        _verify_size_attributes_on_structure,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Enum],
        _verify_width_attribute_on_enum,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.External],
        _verify_addressable_unit_attribute_on_external,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir, [ir_data.Field], _verify_field_attributes, parameters={"errors": errors}
    )
    return errors


def normalize_and_verify(ir):
    """Performs various normalizations and verifications on ir.

    Checks for duplicate attributes.

    Adds fixed_size_in_bits and addressable_unit_size attributes to types when
    they are missing, and checks their correctness when they are not missing.

    Arguments:
      ir: The IR object to normalize.

    Returns:
      A list of validation errors, or an empty list if no errors were encountered.
    """
    errors = attribute_util.check_attributes_in_ir(
        ir,
        types=_ATTRIBUTE_TYPES,
        module_attributes=_MODULE_ATTRIBUTES,
        struct_attributes=_STRUCT_ATTRIBUTES,
        bits_attributes=_BITS_ATTRIBUTES,
        enum_attributes=_ENUM_ATTRIBUTES,
        external_attributes=_EXTERNAL_ATTRIBUTES,
        structure_virtual_field_attributes=_STRUCT_VIRTUAL_FIELD_ATTRIBUTES,
        structure_physical_field_attributes=_STRUCT_PHYSICAL_FIELD_ATTRIBUTES,
    )
    if errors:
        return errors
    _add_missing_attributes_on_ir(ir)
    return _verify_attributes_on_ir(ir)
