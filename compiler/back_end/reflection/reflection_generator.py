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

"""Emboss reflection back end.

Emits a JSON description of a module's types: every field with its bit offset
and bit size, every enum member with its value, every `let` with its value,
plus documentation, `requires` clauses, existence conditions, and byte order.

The point is to let a program consume an `.emb` as *data* rather than as
generated code.  A documentation generator, a register-map catalog, or a host
tool that has to speak several revisions of one interface at once can read this
instead of compiling N sets of C++ views whose type names collide.

Offsets are reported per containing named type: a field's `bit_offset` is
relative to the start of the type it is declared in, not to some outermost
type.  Anonymous `bits` blocks are the exception -- they have no name to be
relative to, so their fields are lifted into the enclosing type at their
absolute bit offsets, which is also where the compiler's own alias fields put
them.

A field whose placement is not a compile-time constant -- anything after a
variable-length field -- reports `null` for `bit_offset`/`bit_size` and the
rendered Emboss expression in `offset_expression`/`size_expression`.
"""

import json

from compiler.front_end import attributes
from compiler.util import expression_printer
from compiler.util import ir_data
from compiler.util import ir_util

# Prelude integer types, and whether they are signed.  The front end hardcodes
# these same three names in `expression_bounds`
# `_set_integer_constraints_from_physical_type`, with a TODO to replace them
# with an attribute on `external`; when that lands, this should read the
# attribute instead.
_PRELUDE_SIGNEDNESS = {
    ("UInt",): False,
    ("Int",): True,
    ("Bcd",): False,
}


def generate_reflection(ir):
    """Generates JSON reflection metadata for the main module of `ir`.

    Arguments:
      ir: an `ir_data.EmbossIr`.

    Returns:
      A tuple of (JSON text, list of errors).
    """
    module = _module_reflection(ir.module[0], ir)
    return json.dumps({"modules": [module]}, indent=2) + "\n", []


# ---- module and type -------------------------------------------------------


def _module_reflection(module, ir):
    return {
        "source_file_name": module.source_file_name,
        "documentation": _documentation(module),
        "types": [
            _type_reflection(type_definition, ir)
            for type_definition in _named_types(module.type)
        ],
    }


def _named_types(type_definitions):
    """Every named type in `type_definitions`, outer first, in source order.

    Anonymous types -- the ones the compiler creates for `bits:` blocks with no
    name -- are skipped, because their fields are reported as part of the type
    that contains them.  A named type nested inside an anonymous one is still
    reported; its `canonical_name` records where it lives.
    """
    result = []
    for type_definition in type_definitions:
        if not type_definition.name.is_anonymous:
            result.append(type_definition)
        result.extend(_named_types(type_definition.subtype))
    return result


def _type_reflection(type_definition, ir):
    """Reflection metadata for one TypeDefinition."""
    result = {
        "name": type_definition.name.name.text,
        "canonical_name": _canonical_name(type_definition.name.canonical_name),
        "kind": _kind_of_type(type_definition),
        "documentation": _documentation(type_definition),
        "requires": _requires(type_definition.attribute),
    }
    if type_definition.has_field("enumeration"):
        result.update(_enum_reflection(type_definition))
    elif type_definition.has_field("structure"):
        result.update(_structure_reflection(type_definition, ir))
    return result


def _kind_of_type(type_definition):
    if type_definition.has_field("enumeration"):
        return "enum"
    if type_definition.has_field("external"):
        return "external"
    assert type_definition.has_field("structure")
    if type_definition.addressable_unit == ir_data.AddressableUnit.BIT:
        return "bits"
    return "struct"


def _enum_reflection(type_definition):
    return {
        "is_signed": ir_util.get_boolean_attribute(
            type_definition.attribute, attributes.IS_SIGNED
        ),
        "maximum_bits": ir_util.get_integer_attribute(
            type_definition.attribute, attributes.ENUM_MAXIMUM_BITS
        ),
        "members": [
            {
                "name": value.name.name.text,
                "value": ir_util.constant_value(value.value),
                "documentation": _documentation(value),
            }
            for value in type_definition.enumeration.value
        ],
    }


def _structure_reflection(type_definition, ir):
    fields = []
    _add_physical_fields(type_definition, 0, None, ir, fields)
    bit_size, min_bit_size, max_bit_size = _sizes_of_structure(type_definition)
    return {
        "bit_size": bit_size,
        "min_bit_size": min_bit_size,
        "max_bit_size": max_bit_size,
        "byte_order": _byte_order_of_structure(type_definition),
        "parameters": [
            _parameter_reflection(parameter)
            for parameter in type_definition.runtime_parameter
        ],
        "fields": fields,
        "virtuals": _virtual_fields(type_definition, ir),
    }


def _parameter_reflection(parameter):
    physical_type = None
    if parameter.has_field("physical_type_alias"):
        physical_type = _base_type_name(parameter.physical_type_alias)
    return {
        "name": parameter.name.name.text,
        "type": parameter.type.which_type,
        "physical_type_name": physical_type,
    }


def _sizes_of_structure(type_definition):
    """A structure's exact, minimum, and maximum sizes, in bits.

    The compiler already computed all three: it synthesizes a `$size_in_bytes`
    (or `$size_in_bits`, in a `bits`) virtual field, whose value folds to a
    constant exactly when the structure is fixed-size, and whose computed bounds
    hold either way.  A dynamically-sized structure has a null exact size and
    the bounds to offer instead; a bound the compiler could not establish is
    itself null.
    """
    unit = int(type_definition.addressable_unit)
    names = {
        ir_data.AddressableUnit.BIT: "$size_in_bits",
        ir_data.AddressableUnit.BYTE: "$size_in_bytes",
    }
    for field in type_definition.structure.field:
        if field.name.name.text != names[type_definition.addressable_unit]:
            continue
        size = ir_util.constant_value(field.read_transform)
        bounds = field.read_transform.type.integer
        return (
            None if size is None else size * unit,
            _scale_bound(bounds.minimum_value, unit),
            _scale_bound(bounds.maximum_value, unit),
        )
    return None, None, None


def _scale_bound(bound, unit):
    """One end of an integer expression's range, in bits, or None if unbounded."""
    if bound is None or bound.endswith("infinity"):
        return None
    return int(bound) * unit


def _byte_order_of_structure(type_definition):
    """The byte order every physical field of `type_definition` agrees on.

    `[$default byte_order]` has already been pushed down onto the individual
    fields by the time the back end runs, so this asks the fields rather than
    the source text.  A structure whose fields disagree has no single answer and
    reports None; each field reports its own `byte_order` regardless, so nothing
    is lost.  Mixed byte order is legal Emboss, so this is not an error.
    """
    orders = set()
    for field in type_definition.structure.field:
        if ir_util.field_is_virtual(field):
            continue
        order = _byte_order_of_field(field)
        if order is not None:
            orders.add(order)
    if len(orders) == 1:
        return orders.pop()
    return None


def _byte_order_of_field(field):
    attribute = ir_util.get_attribute(field.attribute, attributes.BYTE_ORDER)
    return attribute.string_constant.text if attribute else None


# ---- physical fields -------------------------------------------------------


def _add_physical_fields(type_definition, base_bit_offset, condition, ir, out):
    """Appends reflection metadata for `type_definition`'s physical fields.

    Arguments:
      type_definition: the structure to walk.
      base_bit_offset: the bit offset of `type_definition` within the named type
        being reported, or None if that offset is not a compile-time constant.
      condition: an existence condition inherited from an enclosing anonymous
        field, or None.
      ir: the complete IR, for resolving type references.
      out: the list to append to.
    """
    unit = int(type_definition.addressable_unit)
    for field in type_definition.structure.field:
        if ir_util.field_is_virtual(field):
            continue
        start = ir_util.constant_value(field.location.start)
        bit_offset = None
        if start is not None and base_bit_offset is not None:
            bit_offset = base_bit_offset + start * unit
        existence_condition = _conjoin(condition, field.existence_condition)
        if field.name.is_anonymous:
            # An anonymous `bits:` block: its fields belong to this type, at
            # their absolute offsets.  This is where the compiler's own alias
            # virtuals point, so a consumer sees the same field names it would
            # write in Emboss source.
            _add_physical_fields(
                ir_util.find_object(
                    ir_util.get_base_type(field.type).atomic_type.reference, ir
                ),
                bit_offset,
                existence_condition,
                ir,
                out,
            )
            continue
        out.append(
            _physical_field_reflection(
                field, unit, base_bit_offset, bit_offset, existence_condition, ir
            )
        )


def _physical_field_reflection(
    field, unit, base_bit_offset, bit_offset, existence_condition, ir
):
    """Reflection metadata for one physical field."""
    base_type = ir_util.get_base_type(field.type)
    type_definition = ir_util.find_object(base_type.atomic_type.reference, ir)
    is_enum = type_definition.has_field("enumeration")
    return {
        "name": field.name.name.text,
        "abbreviation": (
            field.abbreviation.text if field.has_field("abbreviation") else None
        ),
        "bit_offset": bit_offset,
        "bit_size": _bit_size_of_field(field, unit),
        "offset_expression": expression_printer.render(field.location.start),
        "size_expression": expression_printer.render(field.location.size),
        "alignment": _alignment_of_field(field, unit, base_bit_offset),
        "type_name": _base_type_name(field.type),
        "type": _canonical_name(base_type.atomic_type.reference.canonical_name),
        "is_signed": _is_signed_physical_type(base_type, type_definition),
        "enum_ref": _base_type_name(field.type) if is_enum else None,
        "is_array": ir_util.is_array(field.type),
        "array_element_count": _array_element_count(field.type),
        "byte_order": _byte_order_of_field(field),
        "existence_condition": expression_printer.render(existence_condition),
        "documentation": _documentation(field),
        "requires": _requires(field.attribute),
    }


def _bit_size_of_field(field, unit):
    """The field's size in bits, or None if it is not a compile-time constant.

    This is the same precedence the C++ back end uses: an explicit `:n` on the
    type wins, and it is already in bits, while `location.size` is in the
    enclosing type's addressable units.
    """
    if field.type.has_field("size_in_bits"):
        return ir_util.constant_value(field.type.size_in_bits)
    size = ir_util.constant_value(field.location.size)
    return None if size is None else size * unit


def _alignment_of_field(field, unit, base_bit_offset):
    """What is known about a non-constant offset: `bit_offset % modulus`.

    None when the offset is exact (`bit_offset` already says everything) or when
    nothing at all is known.
    """
    constraints = field.location.start.type.integer
    if constraints.modulus == "infinity" or base_bit_offset is None:
        return None
    modulus = int(constraints.modulus) * unit
    remainder = (base_bit_offset + int(constraints.modular_value) * unit) % modulus
    return {"modulus": modulus, "remainder": remainder}


def _is_signed_physical_type(base_type, type_definition):
    """Whether a physical field's values can be negative.

    None for types where signedness is not a meaningful question -- `Flag`, and
    structures.
    """
    if type_definition.has_field("enumeration"):
        return ir_util.get_boolean_attribute(
            type_definition.attribute, attributes.IS_SIGNED
        )
    if type_definition.has_field("external"):
        name = tuple(base_type.atomic_type.reference.canonical_name.object_path)
        return _PRELUDE_SIGNEDNESS.get(name)
    return None


def _array_element_count(type_ir):
    """The element count of the outermost array dimension, if it is constant."""
    if not type_ir.has_field("array_type"):
        return None
    if type_ir.array_type.which_size != "element_count":
        return None
    return ir_util.constant_value(type_ir.array_type.element_count)


def _base_type_name(type_ir):
    """The simple name of a type, with any array dimensions stripped."""
    path = ir_util.get_base_type(
        type_ir
    ).atomic_type.reference.canonical_name.object_path
    return path[-1]


# ---- virtual fields --------------------------------------------------------


def _virtual_fields(type_definition, ir):
    """Reflection metadata for the `let` fields the author wrote.

    Skips the compiler's own virtuals: the `$`-prefixed size fields, and the
    alias fields it synthesizes for anonymous `bits` members, whose targets are
    already reported as physical fields of this type.
    """
    result = []
    for field in type_definition.structure.field:
        if not ir_util.field_is_virtual(field):
            continue
        if field.name.name.text.startswith("$"):
            continue
        if field.read_transform.source_location.is_synthetic:
            continue
        result.append(
            {
                "name": field.name.name.text,
                "abbreviation": (
                    field.abbreviation.text if field.has_field("abbreviation") else None
                ),
                "value": ir_util.constant_value(field.read_transform),
                "value_expression": expression_printer.render(field.read_transform),
                "type": field.read_transform.type.which_type,
                "is_signed": _is_signed_expression(field.read_transform, ir),
                "is_read_only": ir_util.field_is_read_only(field),
                "existence_condition": expression_printer.render(
                    field.existence_condition
                ),
                "documentation": _documentation(field),
                "requires": _requires(field.attribute),
            }
        )
    return result


def _is_signed_expression(expression, ir):
    """Whether an expression's values can be negative, or None if not numeric."""
    if expression.type.which_type == "integer":
        minimum = expression.type.integer.minimum_value
        if minimum == "-infinity":
            return True
        if minimum is None:
            return None
        return int(minimum) < 0
    if expression.type.which_type == "enumeration":
        enum_type = ir_util.find_object(expression.type.enumeration.name, ir)
        return ir_util.get_boolean_attribute(enum_type.attribute, attributes.IS_SIGNED)
    return None


# ---- shared ----------------------------------------------------------------


def _canonical_name(canonical_name):
    return {
        "module_file": canonical_name.module_file,
        "object_path": list(canonical_name.object_path),
    }


def _documentation(node):
    return "\n".join(documentation.text for documentation in node.documentation)


def _requires(attribute_list):
    """The `[requires: ...]` clause of a node, rendered, as a list."""
    attribute = ir_util.get_attribute(attribute_list, attributes.REQUIRES)
    if not attribute:
        return []
    return [expression_printer.render(attribute.expression)]


def _conjoin(condition, other):
    """`condition && other`, dropping either half if it is a constant `true`."""
    if condition is None or _is_constant_true(condition):
        return other
    if _is_constant_true(other):
        return condition
    return ir_data.Expression(
        function=ir_data.Function(
            function=ir_data.FunctionMapping.AND, args=[condition, other]
        )
    )


def _is_constant_true(expression):
    return (
        expression.which_expression == "boolean_constant"
        and expression.boolean_constant.value
    )
