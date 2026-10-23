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

"""Module which verifies attributes in an Emboss IR.

The main entry point is check_attributes_in_ir(), which checks attributes in an
IR.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import ir_util
from compiler.util import traverse_ir


# Error messages used by multiple attribute type checkers.
_BAD_TYPE_MESSAGE = "Attribute '{name}' must have {type} value."
_MUST_BE_CONSTANT_MESSAGE = "Attribute '{name}' must have a constant value."

# An attribute validator takes an attribute and the name of the file containing
# it, and returns a list of error groups (empty if the attribute is valid).
AttributeChecker = Callable[[ir_data.Attribute, str], list[list[error.Message]]]

# A set of (attribute_name, is_default) pairs: the attributes allowed in some
# scope.
AttributeSpecs = set[tuple[str, bool]]


def _attribute_name_for_errors(attr: ir_data.Attribute) -> str:
    if ir_data_utils.reader(attr).back_end.text:
        return f"({attr.back_end.text}) {attr.name.text}"
    else:
        return attr.name.text


# Attribute type checkers
def _is_constant_boolean(
    attr: ir_data.Attribute, module_source_file: str
) -> list[list[error.Message]]:
    """Checks if the given attr is a constant boolean."""
    if not attr.value.expression.type.boolean.has_field("value"):
        return [
            [
                error.error(
                    module_source_file,
                    attr.value.source_location,
                    _BAD_TYPE_MESSAGE.format(
                        name=_attribute_name_for_errors(attr), type="a constant boolean"
                    ),
                )
            ]
        ]
    return []


def _is_boolean(
    attr: ir_data.Attribute, module_source_file: str
) -> list[list[error.Message]]:
    """Checks if the given attr is a boolean."""
    if attr.value.expression.type.which_type != "boolean":
        return [
            [
                error.error(
                    module_source_file,
                    attr.value.source_location,
                    _BAD_TYPE_MESSAGE.format(
                        name=_attribute_name_for_errors(attr), type="a boolean"
                    ),
                )
            ]
        ]
    return []


def _is_constant_integer(
    attr: ir_data.Attribute, module_source_file: str
) -> list[list[error.Message]]:
    """Checks if the given attr is an integer constant expression."""
    if (
        not attr.value.has_field("expression")
        or attr.value.expression.type.which_type != "integer"
    ):
        return [
            [
                error.error(
                    module_source_file,
                    attr.value.source_location,
                    _BAD_TYPE_MESSAGE.format(
                        name=_attribute_name_for_errors(attr), type="an integer"
                    ),
                )
            ]
        ]
    if not ir_util.is_constant(attr.value.expression):
        return [
            [
                error.error(
                    module_source_file,
                    attr.value.source_location,
                    _MUST_BE_CONSTANT_MESSAGE.format(
                        name=_attribute_name_for_errors(attr)
                    ),
                )
            ]
        ]
    return []


def _is_string(
    attr: ir_data.Attribute, module_source_file: str
) -> list[list[error.Message]]:
    """Checks if the given attr is a string."""
    if not attr.value.has_field("string_constant"):
        return [
            [
                error.error(
                    module_source_file,
                    attr.value.source_location,
                    _BAD_TYPE_MESSAGE.format(
                        name=_attribute_name_for_errors(attr), type="a string"
                    ),
                )
            ]
        ]
    return []


# Provide more readable names for these functions when used in attribute type
# specifiers.
BOOLEAN_CONSTANT = _is_constant_boolean
BOOLEAN = _is_boolean
INTEGER_CONSTANT = _is_constant_integer
STRING = _is_string


def string_from_list(valid_values: Iterable[str]) -> AttributeChecker:
    """Checks if the given attr has one of the valid_values."""

    def _string_from_list(
        attr: ir_data.Attribute, module_source_file: str
    ) -> list[list[error.Message]]:
        if ir_data_utils.reader(attr).value.string_constant.text not in valid_values:
            return [
                [
                    error.error(
                        module_source_file,
                        attr.value.source_location,
                        "Attribute '{name}' must be '{options}'.".format(
                            name=_attribute_name_for_errors(attr),
                            options="' or '".join(sorted(valid_values)),
                        ),
                    )
                ]
            ]
        return []

    return _string_from_list


def check_attributes_in_ir(
    ir: ir_data.EmbossIr,
    *,
    back_end: str | None = None,
    types: Mapping[str, AttributeChecker] | None = None,
    module_attributes: AttributeSpecs | None = None,
    struct_attributes: AttributeSpecs | None = None,
    bits_attributes: AttributeSpecs | None = None,
    enum_attributes: AttributeSpecs | None = None,
    enum_value_attributes: AttributeSpecs | None = None,
    external_attributes: AttributeSpecs | None = None,
    structure_virtual_field_attributes: AttributeSpecs | None = None,
    structure_physical_field_attributes: AttributeSpecs | None = None,
) -> list[list[error.Message]]:
    """Performs basic checks on all attributes in the given ir.

    This function calls _check_attributes on each attribute list in ir.

    Arguments:
      ir: An ir_data.EmbossIr to check.
      back_end: A string specifying the attribute qualifier to check (such as
          `cpp` for `[(cpp) namespace = "foo"]`), or None to check unqualified
          attributes.

          Attributes with a different qualifier will not be checked.
      types: A map from attribute names to validators, such as:
          {
              "maximum_bits": attribute_util.INTEGER_CONSTANT,
              "requires": attribute_util.BOOLEAN,
          }
      module_attributes: A set of (attribute_name, is_default) tuples specifying
          the attributes that are allowed at module scope.
      struct_attributes: A set of (attribute_name, is_default) tuples specifying
          the attributes that are allowed at `struct` scope.
      bits_attributes: A set of (attribute_name, is_default) tuples specifying
          the attributes that are allowed at `bits` scope.
      enum_attributes: A set of (attribute_name, is_default) tuples specifying
          the attributes that are allowed at `enum` scope.
      enum_value_attributes: A set of (attribute_name, is_default) tuples
          specifying the attributes that are allowed at the scope of enum values.
      external_attributes: A set of (attribute_name, is_default) tuples
          specifying the attributes that are allowed at `external` scope.
      structure_virtual_field_attributes: A set of (attribute_name, is_default)
          tuples specifying the attributes that are allowed at the scope of
          virtual fields (`let` fields) in structures (both `struct` and `bits`).
      structure_physical_field_attributes: A set of (attribute_name, is_default)
          tuples specifying the attributes that are allowed at the scope of
          physical fields in structures (both `struct` and `bits`).

    Returns:
      A list of lists of error.error, or an empty list if there were no errors.
    """

    def check_module(module: ir_data.Module, errors: list[list[error.Message]]) -> None:
        errors.extend(
            _check_attributes(
                module.attribute,
                types,
                back_end,
                module_attributes,
                "module '{}'".format(module.source_file_name),
                module.source_file_name,
            )
        )

    def check_type_definition(
        type_definition: ir_data.TypeDefinition,
        source_file_name: str,
        errors: list[list[error.Message]],
    ) -> None:
        if type_definition.has_field("structure"):
            if type_definition.addressable_unit == ir_data.AddressableUnit.BYTE:
                errors.extend(
                    _check_attributes(
                        type_definition.attribute,
                        types,
                        back_end,
                        struct_attributes,
                        "struct '{}'".format(type_definition.name.name.text),
                        source_file_name,
                    )
                )
            elif type_definition.addressable_unit == ir_data.AddressableUnit.BIT:
                errors.extend(
                    _check_attributes(
                        type_definition.attribute,
                        types,
                        back_end,
                        bits_attributes,
                        "bits '{}'".format(type_definition.name.name.text),
                        source_file_name,
                    )
                )
            else:
                assert False, "Unexpected addressable_unit '{}'".format(
                    type_definition.addressable_unit
                )
        elif type_definition.has_field("enumeration"):
            errors.extend(
                _check_attributes(
                    type_definition.attribute,
                    types,
                    back_end,
                    enum_attributes,
                    "enum '{}'".format(type_definition.name.name.text),
                    source_file_name,
                )
            )
        elif type_definition.has_field("external"):
            errors.extend(
                _check_attributes(
                    type_definition.attribute,
                    types,
                    back_end,
                    external_attributes,
                    "external '{}'".format(type_definition.name.name.text),
                    source_file_name,
                )
            )

    def check_struct_field(
        field: ir_data.Field, source_file_name: str, errors: list[list[error.Message]]
    ) -> None:
        if ir_util.field_is_virtual(field):
            field_attributes = structure_virtual_field_attributes
            field_adjective = "virtual "
        else:
            field_attributes = structure_physical_field_attributes
            field_adjective = ""
        errors.extend(
            _check_attributes(
                field.attribute,
                types,
                back_end,
                field_attributes,
                "{}struct field '{}'".format(field_adjective, field.name.name.text),
                source_file_name,
            )
        )

    def check_enum_value(
        value: ir_data.EnumValue,
        source_file_name: str,
        errors: list[list[error.Message]],
    ) -> None:
        errors.extend(
            _check_attributes(
                value.attribute,
                types,
                back_end,
                enum_value_attributes,
                "enum value '{}'".format(value.name.name.text),
                source_file_name,
            )
        )

    errors: list[list[error.Message]] = []
    # TODO(bolms): Add a check that only known $default'ed attributes are
    # used.
    traverse_ir.fast_traverse_ir_top_down(
        ir, [ir_data.Module], check_module, parameters={"errors": errors}
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.TypeDefinition],
        check_type_definition,
        parameters={"errors": errors},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir, [ir_data.Field], check_struct_field, parameters={"errors": errors}
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir, [ir_data.EnumValue], check_enum_value, parameters={"errors": errors}
    )
    return errors


def _check_attributes(
    attribute_list: Iterable[ir_data.Attribute],
    types: Mapping[str, AttributeChecker] | None,
    back_end: str | None,
    attribute_specs: AttributeSpecs | None,
    context_name: str,
    module_source_file: str,
) -> list[list[error.Message]]:
    """Performs basic checks on the given list of attributes.

    Checks the given attribute_list for duplicates, unknown attributes,
    attributes with incorrect type, and attributes whose values are not
    constant.

    Arguments:
        attribute_list: An iterable of ir_data.Attribute.
        types: A map of attribute types to validators.
        back_end: The qualifier for attributes to check, or None.
        attribute_specs: A dict of attribute names to _Attribute structures
            specifying the allowed attributes.
        context_name: A name for the context of these attributes, such as
            "struct 'Foo'" or "module 'm.emb'".  Used in error messages.
        module_source_file: The value of module.source_file_name from the module
            containing 'attribute_list'.  Used in error messages.

    Returns:
        A list of lists of error.Errors.  An empty list indicates no errors were
        found.
    """
    if attribute_specs is None:
        attribute_specs = set()
    errors: list[list[error.Message]] = []
    already_seen_attributes: dict[tuple[str, bool], ir_data.Attribute] = {}
    for attr in attribute_list:
        field_checker = ir_data_utils.reader(attr)
        if field_checker.back_end.text:
            if attr.back_end.text != back_end:
                continue
        else:
            if back_end is not None:
                continue
        attribute_name = _attribute_name_for_errors(attr)
        attr_key = (field_checker.name.text, field_checker.is_default)
        if attr_key in already_seen_attributes:
            original_attr = already_seen_attributes[attr_key]
            errors.append(
                [
                    error.error(
                        module_source_file,
                        attr.source_location,
                        "Duplicate attribute '{}'.".format(attribute_name),
                    ),
                    error.note(
                        module_source_file,
                        original_attr.source_location,
                        "Original attribute",
                    ),
                ]
            )
            continue
        already_seen_attributes[attr_key] = attr

        if attr_key not in attribute_specs:
            if attr.is_default:
                error_message = "Attribute '{}' may not be defaulted on {}.".format(
                    attribute_name, context_name
                )
            else:
                error_message = "Unknown attribute '{}' on {}.".format(
                    attribute_name, context_name
                )
            errors.append(
                [
                    error.error(
                        module_source_file, attr.name.source_location, error_message
                    )
                ]
            )
        else:
            errors.extend(types[attr.name.text](attr, module_source_file))
    return errors


def gather_default_attributes(
    obj: ir_data.Module | ir_data.TypeDefinition | ir_data.Field,
    defaults: dict[str, ir_data.Attribute],
) -> dict[str, Any]:
    """Gathers default attributes for an IR object.

    This is designed to be able to be used as-is as an incidental action in an
    IR traversal to accumulate defaults for child nodes.

    Arguments:
        defaults: A dict of `{ "defaults": { attr.name.text: attr } }`

    Returns:
        A dict of `{ "defaults": { attr.name.text: attr } }` with any defaults
        provided by `obj` added/overridden.
    """
    defaults = defaults.copy()
    for attr in obj.attribute:
        if attr.is_default:
            defaulted_attr = ir_data_utils.copy(attr)
            defaulted_attr.is_default = False
            defaults[attr.name.text] = defaulted_attr
    return {"defaults": defaults}
