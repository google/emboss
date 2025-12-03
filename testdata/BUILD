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

# Shared test data for Emboss.

load(
    "//:build_defs.bzl",
    "cc_emboss_library",
    "emboss_cc_library",
    "emboss_library",
)

package(
    default_visibility = ["//:__subpackages__"],
)

filegroup(
    name = "golden_files",
    srcs = [
        "golden/__init__.py",
        "golden/span_se_log_file_status.emb",
        "golden/span_se_log_file_status.ir.txt",
        "golden/span_se_log_file_status.parse_tree.txt",
        "golden/span_se_log_file_status.tokens.txt",
    ],
)



exports_files(glob(["**/*.emb"]))


filegroup(
    name = "test_embs",
    srcs = [
        "__init__.py",
        "absolute_cpp_namespace.emb",
        "anonymous_bits.emb",
        "bcd.emb",
        "bits.emb",
        "complex_structure.emb",
        "condition.emb",
        "cpp_namespace.emb",
        "dynamic_size.emb",
        "enum.emb",
        "enum_case.emb",
        "explicit_sizes.emb",
        "float.emb",
        "import_dir/project/imported.emb",
        "import_dir/project/importer.emb",
        "imported.emb",
        "imported_genfiles.emb",
        "importer.emb",
        "importer2.emb",
        "int_sizes.emb",
        "int128_sizes.emb",
        "nested_structure.emb",
        "next_keyword.emb",
        "no_cpp_namespace.emb",
        "parameters.emb",
        "requires.emb",
        "subtypes.emb",
        "text_format.emb",
        "uint_sizes.emb",
        "virtual_field.emb",
    ],
)

filegroup(
    name = "format_embs",
    srcs = glob(["format/**"]),
)

emboss_library(
    name = "span_se_log_file_status_emb_ir",
    srcs = [
        "golden/span_se_log_file_status.emb",
    ],
)

cc_emboss_library(
    name = "span_se_log_file_status_emboss",
    deps = [
        ":span_se_log_file_status_emb_ir",
    ],
)

emboss_cc_library(
    name = "nested_structure_emboss",
    srcs = [
        "nested_structure.emb",
    ],
)

emboss_cc_library(
    name = "condition_emboss",
    srcs = [
        "condition.emb",
    ],
)

emboss_cc_library(
    name = "enum_emboss",
    srcs = [
        "enum.emb",
    ],
    # This tag is arbitrary, and exists to ensure you can pass attributes common
    # to all build rules to the underlying rules.
    tags = ["an_arbitrary_tag"],
)

emboss_cc_library(
    name = "enum_case_emboss",
    srcs = [
        "enum_case.emb",
    ],
)

emboss_cc_library(
    name = "explicit_sizes_emboss",
    srcs = [
        "explicit_sizes.emb",
    ],
)

emboss_cc_library(
    name = "imported_emboss",
    srcs = [
        "imported.emb",
    ],
)

emboss_cc_library(
    name = "import_dir_imported_emboss",
    srcs = [
        "import_dir/project/imported.emb",
    ],
)

# This rule is here to test that the Emboss Skylark macro sets eveything up
# correctly for the Emboss front end to read generated .embs.
#
# TODO(bolms): Should genrules with output_to_bindir = 1 be supported as inputs
# to emboss_cc_library?
genrule(
    name = "imported_genfiles",
    srcs = ["imported.emb"],
    outs = ["imported_genfiles.emb"],
    cmd = "sed -e 's/emboss::test/emboss::test::generated/g' $(SRCS) > $(@)",
)

emboss_cc_library(
    name = "imported_genfiles_emboss",
    srcs = [
        "imported_genfiles.emb",
    ],
)

emboss_cc_library(
    name = "alignments_emboss",
    srcs = [
        "alignments.emb",
    ],
)

emboss_cc_library(
    name = "importer_emboss",
    srcs = [
        "importer.emb",
    ],
    deps = [
        ":imported_emboss",
        ":imported_genfiles_emboss",
    ],
)

# Tests that the `import_dirs` attribute works.
emboss_cc_library(
    name = "import_dir_importer_emboss",
    srcs = [
        "import_dir/project/importer.emb",
    ],
    import_dirs = [
        "import_dir",
    ],
    deps = [
        ":import_dir_imported_emboss",
    ],
)

emboss_cc_library(
    name = "importer2_emboss",
    srcs = [
        "importer2.emb",
    ],
    deps = [
        ":importer_emboss",
    ],
)

emboss_cc_library(
    name = "float_emboss",
    srcs = [
        "float.emb",
    ],
)

emboss_cc_library(
    name = "large_array_emboss",
    srcs = [
        "large_array.emb",
    ],
)

emboss_cc_library(
    name = "uint_sizes_emboss",
    srcs = [
        "uint_sizes.emb",
    ],
)

emboss_cc_library(
    name = "int_sizes_emboss",
    srcs = [
        "int_sizes.emb",
    ],
)

emboss_cc_library(
    name = "int128_sizes_emboss",
    srcs = [
        "int128_sizes.emb",
    ],
)

emboss_cc_library(
    name = "dynamic_size_emboss",
    srcs = [
        "dynamic_size.emb",
    ],
)

emboss_cc_library(
    name = "auto_array_size_emboss",
    srcs = [
        "auto_array_size.emb",
    ],
)

emboss_cc_library(
    name = "no_enum_traits_emboss",
    srcs = [
        "no_enum_traits.emb",
    ],
    enable_enum_traits = False,
)

emboss_cc_library(
    name = "start_size_range_emboss",
    srcs = [
        "start_size_range.emb",
    ],
)

emboss_cc_library(
    name = "bcd_emboss",
    srcs = [
        "bcd.emb",
    ],
)

emboss_cc_library(
    name = "no_cpp_namespace_emboss",
    srcs = [
        "no_cpp_namespace.emb",
    ],
)

emboss_cc_library(
    name = "cpp_namespace_emboss",
    srcs = [
        "cpp_namespace.emb",
    ],
)

emboss_cc_library(
    name = "absolute_cpp_namespace_emboss",
    srcs = [
        "absolute_cpp_namespace.emb",
    ],
)

emboss_cc_library(
    name = "requires_emboss",
    srcs = [
        "requires.emb",
    ],
)

emboss_cc_library(
    name = "subtypes_emboss",
    srcs = [
        "subtypes.emb",
    ],
)

emboss_cc_library(
    name = "inline_type_emboss",
    srcs = [
        "inline_type.emb",
    ],
)

emboss_cc_library(
    name = "bits_emboss",
    srcs = [
        "bits.emb",
    ],
)

emboss_cc_library(
    name = "complex_structure_emboss",
    srcs = [
        "complex_structure.emb",
    ],
)

emboss_cc_library(
    name = "anonymous_bits_emboss",
    srcs = [
        "anonymous_bits.emb",
    ],
)

emboss_cc_library(
    name = "text_format_emboss",
    srcs = [
        "text_format.emb",
    ],
)

emboss_cc_library(
    name = "parameters_emboss",
    srcs = [
        "parameters.emb",
    ],
)

emboss_cc_library(
    name = "virtual_field_emboss",
    srcs = [
        "virtual_field.emb",
    ],
)

emboss_cc_library(
    name = "next_keyword_emboss",
    srcs = [
        "next_keyword.emb",
    ],
)

emboss_cc_library(
    name = "complex_offset_emboss",
    srcs = [
        "complex_offset.emb",
    ],
)
