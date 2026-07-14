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

    struct_definitions = []
    for module in ir.module:

        real_imports = [
            imp for imp in module.foreign_import if imp.file_name.text != ""
        ]
        if real_imports:
            diagnostics.append(
                [
                    error.warn(
                        module.source_file_name,
                        real_imports[0].source_location,
                        f"Imports are not yet supported in this backend. Foreign imports will be omitted.",
                    )
                ]
            )

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
        struct_definitions="".join(struct_definitions),
    )

    return rust_source, diagnostics


def _generate_type(type_ir, ir, module, templates, diagnostics) -> str:
    definitions = []

    if type_ir.has_field("external"):
        return ""

    if type_ir.has_field("enumeration"):
        return _generate_enum(type_ir, ir, module, templates, diagnostics)

    if type_ir.runtime_parameter:
        diagnostics.append(
            [
                error.warn(
                    module.source_file_name,
                    type_ir.source_location,
                    f"Parameterized types are not yet supported in this backend. Parameters for '{type_ir.name.name.text}' will be omitted.",
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
        diagnostics.append(
            [
                error.warn(
                    module.source_file_name,
                    type_ir.subtype[0].source_location,
                    f"Subtypes are not yet supported in this backend. All subtypes in '{type_ir.name.name.text}' will be omitted.",
                )
            ]
        )

    if type_ir.addressable_unit != 8:
        diagnostics.append(
            [
                error.warn(
                    module.source_file_name,
                    type_ir.source_location,
                    f"Bit-level structs are not yet supported in this backend. Type '{type_ir.name.name.text}' will be omitted.",
                )
            ]
        )
        return ""

    if not type_ir.has_field("structure"):
        diagnostics.append(
            [
                error.warn(
                    module.source_file_name,
                    type_ir.source_location,
                    f"Non-structure types are not yet supported in this backend. Type '{type_ir.name.name.text}' will be omitted.",
                )
            ]
        )
        return "".join(definitions)

    definitions.append(_generate_struct(type_ir, ir, module, templates, diagnostics))
    return "".join(definitions)


def _generate_enum(type_ir, ir, module, templates, diagnostics) -> str:
    enum_name = type_ir.name.name.text
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


def _generate_struct(type_ir, ir, module, templates, diagnostics) -> str:
    struct_name = type_ir.name.name.text
    field_accessors = []
    mut_field_accessors = []

    for field in type_ir.structure.field:
        field_name = field.name.name.text

        # Skip synthetic fields like $size_in_bytes for now
        if field_name.startswith("$"):
            continue

        if field.has_field("existence_condition"):
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

        if not field.has_field("type") or not field.type.has_field("atomic_type"):
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
                        f"Non-atomic types are not yet supported in this backend. Field '{field_name}' will be omitted.",
                    )
                ]
            )
            continue

        source_name = field.type.atomic_type.reference.source_name[0].text

        if source_name in _UNSUPPORTED_PRELUDE_TYPES:
            diagnostics.append(
                [
                    error.warn(
                        module.source_file_name,
                        field.source_location,
                        f"Type '{source_name}' is not yet supported in this backend. Field '{field_name}' will be omitted.",
                    )
                ]
            )
            continue

        if not field.has_field("location"):
            diagnostics.append(
                [
                    error.warn(
                        module.source_file_name,
                        field.source_location,
                        f"Virtual fields are not yet supported in this backend. Field '{field_name}' will be omitted.",
                    )
                ]
            )
            continue

        if not ir_util.is_constant(field.location.start) or not ir_util.is_constant(
            field.location.size
        ):
            diagnostics.append(
                [
                    error.warn(
                        module.source_file_name,
                        field.source_location,
                        f"Non-constant size or offset is not yet supported in this backend. Field '{field_name}' will be omitted.",
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
                        f"Attribute '{unhandled_attr.name.text}' is not yet supported in this backend. Field '{field_name}' will be omitted.",
                    )
                ]
            )
            continue

        byte_order_attr = ir_util.get_attribute(field.attribute, "byte_order")
        if byte_order_attr:
            byte_order = byte_order_attr.string_constant.text
        else:
            byte_order = "Null"

        byte_offset = ir_util.constant_value(field.location.start)
        byte_length = ir_util.constant_value(field.location.size)

        referenced_type = ir_util.find_object(field.type.atomic_type.reference, ir)

        if referenced_type not in module.type and not referenced_type.has_field(
            "external"
        ):
            diagnostics.append(
                [
                    error.warn(
                        module.source_file_name,
                        field.source_location,
                        f"Cross-module dependencies are not yet supported in this backend. Field '{field_name}' will be omitted.",
                    )
                ]
            )
            continue

        if referenced_type.has_field("external"):
            bits = byte_length * 8
            if field.type.has_field("size_in_bits"):
                bits = ir_util.constant_value(field.type.size_in_bits)

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
                    type_name=source_name.replace(".", "::"),
                    byte_offset=str(byte_offset),
                    byte_length=str(byte_length),
                )
            )
            mut_field_accessors.append(
                code_template.format_template(
                    templates.struct_mut_field_accessor,
                    field_name=field_name,
                    type_name=source_name.replace(".", "::"),
                    byte_offset=str(byte_offset),
                    byte_length=str(byte_length),
                )
            )
        elif referenced_type.has_field("enumeration"):
            bits = byte_length * 8
            if field.type.has_field("size_in_bits"):
                bits = ir_util.constant_value(field.type.size_in_bits)
            field_accessors.append(
                code_template.format_template(
                    templates.enum_field_accessor,
                    field_name=field_name,
                    enum_name=source_name.replace(".", "::"),
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
                    enum_name=source_name.replace(".", "::"),
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

    return code_template.format_template(
        templates.struct_view,
        struct_name=struct_name,
        field_accessors="".join(field_accessors),
        mut_field_accessors="".join(mut_field_accessors),
    )


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
