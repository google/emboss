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

"""Emboss Rust code generator."""

import os
import sys
from typing import Literal

from compiler.back_end.util import code_template
from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import ir_util
from compiler.util import resources
import argparse

ColorOutput = Literal["always", "never", "if_tty", "auto"]
Source = str
Diagnostics = list[list[error._Message]]
ErrorList = list[list[error._Message]]

_TEMPLATE_FILE_NAME = "generated_code_templates"
_UNSUPPORTED_PRELUDE_TYPES = {"Bcd", "Flag", "Float"}
_SYNTHETIC_ATTRIBUTES = {"expected_back_ends", "fixed_size_in_bits"}


def _show_errors(
    errors: ErrorList, ir: ir_data.EmbossIr, color_output: ColorOutput
) -> None:
    """Prints errors with source code snippets."""
    source_codes = {}
    if ir:
        for module in ir.module:
            source_codes[module.source_file_name] = module.source_text
    use_color = color_output == "always" or (
        color_output in ("auto", "if_tty") and os.isatty(sys.stderr.fileno())
    )
    print(error.format_errors(errors, source_codes, use_color), file=sys.stderr)


def _load_templates():
    return code_template.parse_templates(
        resources.load("compiler.back_end.experimental.rust", _TEMPLATE_FILE_NAME)
    )


def generate_code(ir: ir_data.EmbossIr) -> tuple[Source, Diagnostics]:
    """Generates Rust source code and definitions for the provided Emboss IR."""
    templates = _load_templates()
    diagnostics = []

    if ir.module:
        main_module = ir.module[0]
        diagnostics.append(
            [
                error.warn(
                    "<rust>",
                    None,
                    "Rust backend support is not yet complete and subject to change at any time.",
                )
            ]
        )

    imports_list = []
    struct_definitions = []
    module = ir.module[0]
    
    real_imports = [
        imp for imp in module.foreign_import if imp.file_name.text != ""
    ]
    for imp in real_imports:
        crate_name = imp.file_name.text.replace("/", "_").replace(".", "_")
        alias = imp.local_name.text
        imports_list.append(f"use {crate_name} as {alias};\n")

    for attr in module.attribute:
        if not attr.is_default:
            if attr.has_field("back_end") and attr.back_end.text != "rust":
                continue
            if attr.name.text in _SYNTHETIC_ATTRIBUTES:
                continue
            diagnostics.append(
                [
                    error.warn(
                        module.source_file_name,
                        attr.source_location,
                        f"Module-level attribute '{attr.name.text}' is not yet supported in this backend. It will be omitted.",
                    )
                ]
            )

    for type_def in module.type:
        struct_definitions.append(
            _generate_type(type_def, ir, module, templates, diagnostics)
        )

    rust_source = code_template.format_template(
        templates.rust_module,
        imports_list="".join(imports_list),
        struct_definitions="".join(struct_definitions),
    )

    return rust_source, diagnostics


def _is_type_omitted(type_ir) -> bool:
    return False

def _resolve_type(reference, ir):
    target_module_file = reference.canonical_name.module_file
    target_object_path = reference.canonical_name.object_path
    
    for mod in ir.module:
        if mod.source_file_name == target_module_file:
            for type_def in mod.type:
                if type_def.name.name.text == target_object_path[0]:
                    current = type_def
                    for path_element in target_object_path[1:]:
                        found = False
                        for nested in current.subtype:
                            if nested.name.name.text == path_element:
                                current = nested
                                found = True
                                break
                        if not found:
                            return None
                    return current
    return None

def _generate_type(type_ir, ir, module, templates, diagnostics) -> str:
    definitions = []

    type_name = "_".join(type_ir.name.canonical_name.object_path)

    if type_ir.has_field("external"):
        return ""

    if type_ir.runtime_parameter:
        diagnostics.append(
            [
                error.warn(
                    module.source_file_name,
                    type_ir.source_location,
                    f"Parameterized types are not yet supported in this backend. Parameters for '{type_name}' will be omitted.",
                )
            ]
        )

    for attr in type_ir.attribute:
        if attr.is_default:
            continue
        if attr.has_field("back_end") and attr.back_end.text != "rust":
            continue
        if attr.name.text in _SYNTHETIC_ATTRIBUTES:
            continue
        diagnostics.append(
            [
                error.warn(
                    module.source_file_name,
                    attr.source_location,
                    f"Type-level attribute '{attr.name.text}' is not yet supported in this backend. It will be omitted.",
                )
            ]
        )

    if type_ir.subtype:
        for st in type_ir.subtype:
            definitions.append(
                _generate_type(st, ir, module, templates, diagnostics)
            )

    if type_ir.has_field("structure"):
        definitions.append(_generate_struct(type_ir, ir, module, templates, diagnostics, type_name))
    elif type_ir.has_field("enumeration"):
        definitions.append(_generate_enum(type_ir, ir, module, templates, diagnostics, type_name))
    else:
        diagnostics.append(
            [
                error.warn(
                    module.source_file_name,
                    type_ir.source_location,
                    f"Non-structure/enum types are not yet supported in this backend. Type '{type_name}' will be omitted.",
                )
            ]
        )

    return "".join(definitions)


def _generate_enum(type_ir, ir, module, templates, diagnostics, enum_name) -> str:
    enum_variants = []
    enum_match_variants = []
    enum_aliases = []

    seen_values = {}
    is_signed = False

    for opt in type_ir.enumeration.value:
        variant_value = ir_util.constant_value(opt.value)
        if variant_value < 0:
            is_signed = True

    underlying_type = "i64" if is_signed else "u64"

    for val in type_ir.enumeration.value:
        variant_name = val.name.name.text
        variant_value = ir_util.constant_value(val.value)

        if variant_value in seen_values:
            enum_aliases.append(
                code_template.format_template(
                    templates.enum_alias,
                    variant_name=variant_name,
                    original_variant_name=seen_values[variant_value],
                )
            )
        else:
            seen_values[variant_value] = variant_name
            enum_variants.append(
                code_template.format_template(
                    templates.enum_variant,
                    variant_name=variant_name,
                    variant_value=str(variant_value),
                )
            )
            enum_match_variants.append(
                code_template.format_template(
                    templates.enum_match_variant,
                    enum_name=enum_name,
                    variant_name=variant_name,
                    variant_value=str(variant_value),
                )
            )

    return code_template.format_template(
        templates.enum_definition,
        enum_name=enum_name,
        underlying_type=underlying_type,
        enum_variants="".join(enum_variants),
        enum_match_variants="".join(enum_match_variants),
        enum_aliases="".join(enum_aliases),
    )


def _rust_type_for_expr_type(expr_type):
    if expr_type.has_field("integer"):
        if int(expr_type.integer.minimum_value) < 0:
            return "i64"
        return "u64"
    if expr_type.has_field("boolean"):
        return "bool"
    if expr_type.has_field("enumeration"):
        return "_".join(expr_type.enumeration.name.canonical_name.object_path)
    return "u64"




def _generate_expression(expr, ir, module, generated_fields, templates, self_ref="self"):
    if ir_util.is_constant(expr):
        return str(ir_util.constant_value(expr))
        
    if expr.has_field("boolean_constant"):
        return "true" if expr.boolean_constant.value else "false"

    if expr.has_field("field_reference"):
        path_names = [part.canonical_name.object_path[-1] for part in expr.field_reference.path]
        if path_names[0] not in generated_fields:
            return None
        
        path_expr = "".join([f".{name}()" for name in path_names])
        return code_template.format_template(templates.expr_field_reference_no_cast, self_ref=self_ref, path_expr=path_expr)

    if expr.has_field("function"):
        func = expr.function.function
        args = []
        for a in expr.function.args:
            arg_str = _generate_expression(a, ir, module, generated_fields, templates, self_ref)
            if arg_str is None:
                return None
            args.append(arg_str)
            
        if func == ir_data.FunctionMapping.ADDITION.value:
            return code_template.format_template(templates.expr_addition, left=args[0], right=args[1])
        if func == ir_data.FunctionMapping.SUBTRACTION.value:
            return code_template.format_template(templates.expr_subtraction, left=args[0], right=args[1])
        if func == ir_data.FunctionMapping.MULTIPLICATION.value:
            return code_template.format_template(templates.expr_multiplication, left=args[0], right=args[1])
        if func == ir_data.FunctionMapping.MAXIMUM.value:
            return code_template.format_template(templates.expr_maximum, left=args[0], right=args[1])
        if func == ir_data.FunctionMapping.CHOICE.value:
            return code_template.format_template(templates.expr_choice, condition=args[0], true_value=args[1], false_value=args[2])
        if func == ir_data.FunctionMapping.EQUALITY.value:
            return code_template.format_template(templates.expr_equality, left=args[0], right=args[1])
        if func == ir_data.FunctionMapping.LESS.value:
            return code_template.format_template(templates.expr_less, left=args[0], right=args[1])
            
        return None
    return None


def _generate_array_field(
    field,
    field_name,
    struct_name,
    base_type,
    ir,
    byte_offset,
    byte_length,
    const_byte_length,
    referenced_type,
    source_name,
    byte_order,
    templates,
    field_accessors,
    mut_field_accessors,
    generated_nested_types,
):
    camel_case_field = "".join(word.capitalize() for word in field_name.split("_"))
    view_name = struct_name + "_" + camel_case_field + "_ArrayView"

    element_size_in_bits = ir_util.fixed_size_of_type_in_bits(base_type, ir)
    if element_size_in_bits is None or element_size_in_bits % 8 != 0:
        return
    element_size_bytes = element_size_in_bits // 8

    bits = const_byte_length * 8
    if base_type.has_field("size_in_bits"):
        bits = ir_util.constant_value(base_type.size_in_bits)
        
    storage_type = "S::Sliced<'_>"
    storage_type_mut = "S::SlicedMut<'_>"

    if referenced_type.has_field("external"):
        element_type = code_template.format_template(templates.array_element_type_external, source_name=source_name, bits=str(bits), byte_order=byte_order, storage_type=storage_type)
        element_type_mut = code_template.format_template(templates.array_element_type_external, source_name=source_name, bits=str(bits), byte_order=byte_order, storage_type=storage_type_mut)
        element_constructor = code_template.format_template(templates.array_element_constructor_external, source_name=source_name)
        element_constructor_mut = code_template.format_template(templates.array_element_constructor_external, source_name=source_name)
    elif referenced_type.has_field("structure"):
        element_type = code_template.format_template(templates.array_element_type_structure, struct_clean_name=source_name, storage_type=storage_type)
        element_type_mut = code_template.format_template(templates.array_element_type_structure, struct_clean_name=source_name + "Mut", storage_type=storage_type_mut)
        element_constructor = code_template.format_template(templates.array_element_constructor_structure, struct_clean_name=source_name)
        element_constructor_mut = code_template.format_template(templates.array_element_constructor_structure, struct_clean_name=source_name + "Mut")
    elif referenced_type.has_field("enumeration"):
        element_type = code_template.format_template(templates.array_element_type_enumeration, enum_clean_name=source_name, bits=str(bits), byte_order=byte_order, storage_type=storage_type)
        element_type_mut = code_template.format_template(templates.array_element_type_mut_enumeration, enum_clean_name=source_name, bits=str(bits), byte_order=byte_order, storage_type=storage_type_mut)
        element_constructor = code_template.format_template(templates.array_element_constructor_enumeration)
        element_constructor_mut = code_template.format_template(templates.array_element_constructor_mut_enumeration)
    else:
        return

    field_accessors.append(
        code_template.format_template(
            templates.array_field_accessor,
            field_name=field_name,
            view_name=view_name,
            element_size=str(element_size_bytes),
            byte_offset=str(byte_offset),
            byte_length=str(byte_length),
        )
    )
    mut_field_accessors.append(
        code_template.format_template(
            templates.array_mut_field_accessor,
            field_name=field_name,
            view_name=view_name,
            element_size=str(element_size_bytes),
            byte_offset=str(byte_offset),
            byte_length=str(byte_length),
        )
    )
    generated_nested_types.append(
        code_template.format_template(
            templates.array_view_struct,
            view_name=view_name,
            element_size=str(element_size_bytes),
            element_type=element_type,
            element_constructor=element_constructor,
            element_type_mut=element_type_mut,
            element_constructor_mut=element_constructor_mut,
        )
    )


def _generate_struct(type_ir, ir, module, templates, diagnostics, struct_name) -> str:
    field_accessors = []
    mut_field_accessors = []
    generated_nested_types = []
    generated_fields = set()

    fields_to_process = []
    if type_ir.structure.fields_in_dependency_order:
        for idx in type_ir.structure.fields_in_dependency_order:
            fields_to_process.append(type_ir.structure.field[idx])
    else:
        fields_to_process = type_ir.structure.field

    for field in fields_to_process:
        field_name = field.name.name.text

        # Skip synthetic fields like $size_in_bytes for now
        if field_name.startswith("$"):
            continue

        if field.has_field("existence_condition") and not field.has_field("read_transform"):
            cond = ir_util.constant_value(field.existence_condition)
            if cond is not True:
                diagnostics.append(
                    [
                        error.warn(
                            module.source_file_name,
                            field.source_location,
                            f"Conditional fields are not yet supported in this backend. Field '{field_name}' will be omitted.",
                        )
                    ]
                )
                continue

        if not field.has_field("location"):
            if not field.has_field("read_transform"):
                diagnostics.append(
                    [
                        error.warn(
                            module.source_file_name,
                            (
                                field.type.source_location
                                if field.has_field("type")
                                else field.source_location
                            ),
                            f"Virtual fields without read_transform are not supported. Field '{field_name}' will be omitted.",
                        )
                    ]
                )
                continue
                
            expr_str = _generate_expression(field.read_transform, ir, module, generated_fields, templates)
            if expr_str is None:
                diagnostics.append(
                    [
                        error.warn(
                            module.source_file_name,
                            field.read_transform.source_location,
                            f"Virtual field '{field_name}' uses unsupported expression. It will be omitted.",
                        )
                    ]
                )
                continue
                
            return_type = _rust_type_for_expr_type(field.read_transform.type)
            
            if field.read_transform.has_field("field_reference") and field.read_transform.type.has_field("opaque"):
                # opaque fields usually mean it's an alias to a struct/array view.
                pass
            else:
                field_accessors.append(code_template.format_template(
                    templates.virtual_field_accessor,
                    field_name=field_name,
                    return_type=return_type,
                    expression=expr_str,
                ))
                mut_field_accessors.append(code_template.format_template(
                    templates.mut_virtual_field_accessor,
                    field_name=field_name,
                    return_type=return_type,
                    expression=expr_str,
                ))
                
            generated_fields.add(field_name)
            continue

        if not field.has_field("type") or not (field.type.has_field("atomic_type") or field.type.has_field("array_type")):
            loc = (
                field.type.source_location
                if field.has_field("type")
                else field.source_location
            )
            diagnostics.append(
                [
                    error.warn(
                        module.source_file_name,
                        loc,
                        f"Non-atomic and non-array types are not yet supported in this backend. Field '{field_name}' will be omitted.",
                    )
                ]
            )
            continue

        is_array = field.type.has_field("array_type")
        if is_array:
            base_type = field.type.array_type.base_type
        else:
            base_type = field.type

        if not base_type.has_field("atomic_type"):
            diagnostics.append(
                [
                    error.warn(
                        module.source_file_name,
                        field.source_location,
                        f"Arrays of non-atomic types (e.g. multi-dimensional arrays) are not yet supported in this backend. Field '{field_name}' will be omitted.",
                    )
                ]
            )
            continue

        orig_source_name = [part.text for part in base_type.atomic_type.reference.source_name]
        obj_path = [part for part in base_type.atomic_type.reference.canonical_name.object_path]

        num_module_parts = len(orig_source_name) - len(obj_path)
        if num_module_parts > 0:
            module_prefix = "::".join(orig_source_name[:num_module_parts]) + "::"
            type_name = "_".join(obj_path)
            source_name = module_prefix + type_name
            source_name_for_prelude = "::".join(orig_source_name) # original style for checking preludes
        else:
            source_name = "_".join(obj_path)
            source_name_for_prelude = "::".join(orig_source_name)

        if source_name_for_prelude in _UNSUPPORTED_PRELUDE_TYPES:
            diagnostics.append(
                [
                    error.warn(
                        module.source_file_name,
                        field.source_location,
                        f"Type '{source_name_for_prelude}' is not yet supported in this backend. Field '{field_name}' will be omitted.",
                    )
                ]
            )
            continue

        target_type = _resolve_type(base_type.atomic_type.reference, ir)

        byte_offset_expr = _generate_expression(field.location.start, ir, module, generated_fields, templates)
        byte_length_expr = _generate_expression(field.location.size, ir, module, generated_fields, templates)

        if byte_offset_expr is None or byte_length_expr is None:
            reason = "offset" if byte_offset_expr is None else "size"
            diagnostics.append(
                [
                    error.warn(
                        module.source_file_name,
                        field.source_location,
                        f"Non-constant {reason} relies on unsupported expression or omitted field. Field '{field_name}' will be omitted.",
                    )
                ]
            )
            continue

        unhandled_attr = None
        for attr in field.attribute:
            if attr.is_default:
                continue
            if attr.has_field("back_end") and attr.back_end.text != "rust":
                continue

            attr_name = attr.name.text
            if attr_name == "requires":
                diagnostics.append(
                    [
                        error.warn(
                            module.source_file_name,
                            attr.source_location,
                            f"Validation '{attr_name}' is not yet supported in this backend. Validation will not be generated for field '{field_name}'.",
                        )
                    ]
                )
            elif attr_name != "byte_order":
                unhandled_attr = attr
                break

        if unhandled_attr:
            diagnostics.append(
                [
                    error.warn(
                        module.source_file_name,
                        unhandled_attr.source_location,
                        f"Attribute '{unhandled_attr.name.text}' is not yet supported in this backend. It will be ignored for field '{field_name}'.",
                    )
                ]
            )

        byte_order_attr = ir_util.get_attribute(field.attribute, "byte_order")
        if byte_order_attr:
            byte_order = byte_order_attr.string_constant.text
        else:
            byte_order = "Null"

        byte_offset = byte_offset_expr
        byte_length = byte_length_expr
        
        if ir_util.is_constant(field.location.size):
            const_byte_length = ir_util.constant_value(field.location.size)
        else:
            const_byte_length = 0

        referenced_type = ir_util.find_object(base_type.atomic_type.reference, ir)

        if is_array:
            # Generate a unique struct for each array field.
            _generate_array_field(
                field,
                field_name,
                struct_name,
                base_type,
                ir,
                byte_offset,
                byte_length,
                const_byte_length,
                referenced_type,
                source_name,
                byte_order,
                templates,
                field_accessors,
                mut_field_accessors,
                generated_nested_types,
            )
        else:
            if referenced_type.has_field("external"):
                bits = const_byte_length * type_ir.addressable_unit
                if field.type.has_field("size_in_bits"):
                    bits = ir_util.constant_value(field.type.size_in_bits)

                accessor_template = templates.external_field_accessor
                mut_accessor_template = templates.external_mut_field_accessor
                
                if type_ir.addressable_unit == 1:
                    bit_offset_int = int(ir_util.constant_value(field.location.start))
                    bits_int = int(bits)
                    byte_len_int = ((bit_offset_int + bits_int - 1) // 8) + 1
                    bit_offset_str = str(bit_offset_int)
                    
                    field_accessors.append(
                        code_template.format_template(
                            templates.bit_external_field_accessor,
                            field_name=field_name,
                            type_name=source_name,
                            bits=str(bits),
                            byte_order=byte_order,
                            bit_offset=bit_offset_str,
                            byte_length=str(byte_len_int),
                        )
                    )
                    mut_field_accessors.append(
                        code_template.format_template(
                            templates.bit_external_mut_field_accessor,
                            field_name=field_name,
                            type_name=source_name,
                            bits=str(bits),
                            byte_order=byte_order,
                            bit_offset=bit_offset_str,
                            byte_length=str(byte_len_int),
                        )
                    )
                else:
                    field_accessors.append(
                        code_template.format_template(
                            templates.external_field_accessor,
                            field_name=field_name,
                            type_name=source_name,
                            bits=str(bits),
                            byte_order=byte_order,
                            byte_offset=str(byte_offset),
                            byte_length=str(byte_length),
                        )
                    )
                    mut_field_accessors.append(
                        code_template.format_template(
                            templates.external_mut_field_accessor,
                            field_name=field_name,
                            type_name=source_name,
                            bits=str(bits),
                            byte_order=byte_order,
                            byte_offset=str(byte_offset),
                            byte_length=str(byte_length),
                        )
                    )
            elif referenced_type.has_field("structure"):
                field_accessors.append(
                    code_template.format_template(
                        templates.struct_field_accessor,
                        field_name=field_name,
                        type_name=source_name,
                        byte_offset=str(byte_offset),
                        byte_length=str(byte_length),
                    )
                )
                mut_field_accessors.append(
                    code_template.format_template(
                        templates.struct_mut_field_accessor,
                        field_name=field_name,
                        type_name=source_name,
                        byte_offset=str(byte_offset),
                        byte_length=str(byte_length),
                    )
                )
            elif referenced_type.has_field("enumeration"):
                bits = const_byte_length * type_ir.addressable_unit
                if field.type.has_field("size_in_bits"):
                    bits = ir_util.constant_value(field.type.size_in_bits)
                if type_ir.addressable_unit == 1:
                    bit_offset_int = int(ir_util.constant_value(field.location.start))
                    bits_int = int(bits)
                    byte_len_int = ((bit_offset_int + bits_int - 1) // 8) + 1
                    field_accessors.append(
                        code_template.format_template(
                            templates.bit_enum_field_accessor,
                            field_name=field_name,
                            enum_name=source_name,
                            bits=str(bits),
                            byte_order=byte_order,
                            bit_offset=str(bit_offset_int),
                            byte_length=str(byte_len_int),
                        )
                    )
                    mut_field_accessors.append(
                        code_template.format_template(
                            templates.bit_enum_mut_field_accessor,
                            field_name=field_name,
                            enum_name=source_name,
                            bits=str(bits),
                            byte_order=byte_order,
                            bit_offset=str(bit_offset_int),
                            byte_length=str(byte_len_int),
                        )
                    )
                else:
                    field_accessors.append(
                        code_template.format_template(
                            templates.enum_field_accessor,
                            field_name=field_name,
                            enum_name=source_name,
                            bits=str(bits),
                            byte_order=byte_order,
                            byte_offset=str(byte_offset),
                            byte_length=str(byte_length),
                        )
                    )
                    mut_field_accessors.append(
                        code_template.format_template(
                            templates.enum_mut_field_accessor,
                            field_name=field_name,
                            enum_name=source_name,
                            bits=str(bits),
                            byte_order=byte_order,
                            byte_offset=str(byte_offset),
                            byte_length=str(byte_length),
                        )
                    )
            else:
                diagnostics.append(
                    [
                        error.warn(
                            module.source_file_name,
                            (
                                field.type.source_location
                                if field.has_field("type")
                                else field.source_location
                            ),
                            f"Target type variety is not yet supported in this backend. Field '{field_name}' will be omitted.",
                        )
                    ]
                )
                continue
            
        generated_fields.add(field_name)

    main_struct_def = code_template.format_template(
        templates.struct_view,
        struct_name=struct_name,
        field_accessors="".join(field_accessors),
        mut_field_accessors="".join(mut_field_accessors),
    )
    return "".join(generated_nested_types) + main_struct_def


def generate_code_and_log_errors(
    ir: ir_data.EmbossIr, color_output: ColorOutput
) -> tuple[Source, ErrorList]:
    """Generates Rust source code and logs any resulting errors or warnings."""
    rust_source, diagnostics = generate_code(ir)

    if diagnostics:
        _show_errors(diagnostics, ir, color_output)

    errors = [
        msg_list
        for msg_list in diagnostics
        if any(msg.severity == error.ERROR for msg in msg_list)
    ]

    return rust_source, errors


def _parse_command_line(argv):
    parser = argparse.ArgumentParser(description="Emboss Rust code generator")
    parser.add_argument(
        "--input-file", type=str, help="Path to input IR", required=True
    )
    parser.add_argument(
        "--output-file", type=str, help="Path to output rust file", required=True
    )
    parser.add_argument("--color-output", type=str, default="auto")
    return parser.parse_args(argv[1:])


def main(flags):
    with open(flags.input_file) as f:
        ir = ir_data_utils.IrDataSerializer.from_json(ir_data.EmbossIr, f.read())

    rust_source, errors = generate_code_and_log_errors(ir, flags.color_output)
    if errors:
        return 1

    with open(flags.output_file, "w") as f:
        f.write(rust_source)
    return 0


if __name__ == "__main__":
    sys.exit(main(_parse_command_line(sys.argv)))
