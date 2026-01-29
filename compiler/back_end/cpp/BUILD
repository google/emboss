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

# Emboss C++ code generator.

load("@rules_python//python:py_binary.bzl", "py_binary")
load("@rules_python//python:py_library.bzl", "py_library")
load("@rules_python//python:py_test.bzl", "py_test")
load(":build_defs.bzl", "cpp_golden_test", "emboss_cc_test")

package(
    default_visibility = [
        "//visibility:private",
    ],
    features = ["-layering_check"],
)

py_binary(
    name = "emboss_codegen_cpp",
    srcs = ["emboss_codegen_cpp.py"],
    python_version = "PY3",
    visibility = ["//visibility:public"],
    deps = [
        ":header_generator",
        "//compiler/util:ir_data",
    ],
)

py_library(
    name = "attributes",
    srcs = ["attributes.py"],
    deps = [],
)

py_library(
    name = "header_generator",
    srcs = ["header_generator.py"],
    data = [
        "generated_code_templates",
    ],
    deps = [
        ":attributes",
        "//compiler/back_end/util:code_template",
        "//compiler/util:attribute_util",
        "//compiler/util:ir_data",
        "//compiler/util:ir_util",
        "//compiler/util:name_conversion",
        "//compiler/util:resources",
    ],
)

py_test(
    name = "header_generator_test",
    srcs = ["header_generator_test.py"],
    deps = [
        ":header_generator",
        "//compiler/front_end:glue",
        "//compiler/util:test_util",
    ],
)

emboss_cc_test(
    name = "span_se_log_file_status_emb_generated_code_test",
    srcs = [
        "testcode/read_log_file_status_test.cc",
    ],
    deps = [
        "//testdata:span_se_log_file_status_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "nested_structure_test",
    srcs = [
        "testcode/nested_structure_test.cc",
    ],
    deps = [
        "//testdata:nested_structure_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "alignments_test",
    srcs = [
        "testcode/alignments_test.cc",
    ],
    deps = [
        "//testdata:alignments_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "condition_test",
    srcs = [
        "testcode/condition_test.cc",
    ],
    deps = [
        "//testdata:condition_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "enum_test",
    srcs = [
        "testcode/enum_test.cc",
    ],
    deps = [
        "//testdata:enum_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "enum_case_test",
    srcs = [
        "testcode/enum_case_test.cc",
    ],
    deps = [
        "//testdata:enum_case_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "explicit_sizes_test",
    srcs = [
        "testcode/explicit_sizes_test.cc",
    ],
    deps = [
        "//testdata:explicit_sizes_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "importer_test",
    srcs = [
        "testcode/importer_test.cc",
    ],
    deps = [
        "//testdata:importer_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "importer2_test",
    srcs = [
        "testcode/importer2_test.cc",
    ],
    deps = [
        "//testdata:importer2_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "uint_sizes_test",
    srcs = [
        "testcode/uint_sizes_test.cc",
    ],
    deps = [
        "//testdata:uint_sizes_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "int_sizes_test",
    srcs = [
        "testcode/int_sizes_test.cc",
    ],
    deps = [
        "//testdata:int_sizes_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "float_test",
    srcs = [
        "testcode/float_test.cc",
    ],
    deps = [
        "//testdata:float_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "dynamic_size_test",
    srcs = [
        "testcode/dynamic_size_test.cc",
    ],
    deps = [
        "//testdata:dynamic_size_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "auto_array_size_test",
    srcs = [
        "testcode/auto_array_size_test.cc",
    ],
    deps = [
        "//testdata:auto_array_size_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "no_enum_traits_test",
    srcs = [
        "testcode/no_enum_traits_test.cc",
    ],
    deps = [
        "//testdata:no_enum_traits_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "start_size_range_test",
    srcs = [
        "testcode/start_size_range_test.cc",
    ],
    deps = [
        "//testdata:start_size_range_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "bcd_test",
    srcs = [
        "testcode/bcd_test.cc",
    ],
    deps = [
        "//testdata:bcd_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "namespace_test",
    srcs = [
        "testcode/namespace_test.cc",
    ],
    deps = [
        "//testdata:absolute_cpp_namespace_emboss",
        "//testdata:cpp_namespace_emboss",
        "//testdata:no_cpp_namespace_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "requires_test",
    srcs = [
        "testcode/requires_test.cc",
    ],
    deps = [
        "//testdata:requires_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "subtypes_test",
    srcs = [
        "testcode/subtypes_test.cc",
    ],
    deps = [
        "//testdata:subtypes_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "inline_type_test",
    srcs = [
        "testcode/inline_type_test.cc",
    ],
    deps = [
        "//testdata:inline_type_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "bits_test",
    srcs = [
        "testcode/bits_test.cc",
    ],
    deps = [
        "//runtime/cpp:cpp_utils",
        "//testdata:bits_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "anonymous_bits_test",
    srcs = [
        "testcode/anonymous_bits_test.cc",
    ],
    deps = [
        "//runtime/cpp:cpp_utils",
        "//testdata:anonymous_bits_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "next_keyword_test",
    srcs = [
        "testcode/next_keyword_test.cc",
    ],
    deps = [
        "//testdata:next_keyword_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "virtual_field_test",
    srcs = [
        "testcode/virtual_field_test.cc",
    ],
    deps = [
        "//testdata:virtual_field_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "text_format_test",
    srcs = [
        "testcode/text_format_test.cc",
    ],
    deps = [
        "//testdata:text_format_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "parameters_test",
    srcs = [
        "testcode/parameters_test.cc",
    ],
    deps = [
        "//testdata:parameters_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "complex_structure_test",
    srcs = ["testcode/complex_structure_test.cc"],
    deps = [
        "//testdata:complex_structure_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_test(
    name = "complex_offset_test",
    srcs = ["testcode/complex_offset_test.cc"],
    deps = [
        "//testdata:complex_offset_emboss",
        "@com_google_googletest//:gtest_main",
    ],
)

# New golden test infrastructure
py_library(
    name = "one_golden_test_lib",
    srcs = ["one_golden_test.py"],
)

py_binary(
    name = "run_one_golden_test",
    srcs = ["run_one_golden_test.py"],
    deps = [":one_golden_test_lib"],
)

cpp_golden_test(
    name = "anonymous_bits_golden_test",
    emb_file = "//testdata:anonymous_bits.emb",
    golden_file = "//testdata/golden_cpp:anonymous_bits.emb.h",
)

cpp_golden_test(
    name = "bits_golden_test",
    emb_file = "//testdata:bits.emb",
    golden_file = "//testdata/golden_cpp:bits.emb.h",
)

cpp_golden_test(
    name = "absolute_cpp_namespace_golden_test",
    emb_file = "//testdata:absolute_cpp_namespace.emb",
    golden_file = "//testdata/golden_cpp:absolute_cpp_namespace.emb.h",
)

cpp_golden_test(
    name = "alignments_golden_test",
    emb_file = "//testdata:alignments.emb",
    golden_file = "//testdata/golden_cpp:alignments.emb.h",
)

cpp_golden_test(
    name = "auto_array_size_golden_test",
    emb_file = "//testdata:auto_array_size.emb",
    golden_file = "//testdata/golden_cpp:auto_array_size.emb.h",
)

cpp_golden_test(
    name = "bcd_golden_test",
    emb_file = "//testdata:bcd.emb",
    golden_file = "//testdata/golden_cpp:bcd.emb.h",
)

cpp_golden_test(
    name = "complex_offset_golden_test",
    emb_file = "//testdata:complex_offset.emb",
    golden_file = "//testdata/golden_cpp:complex_offset.emb.h",
)

cpp_golden_test(
    name = "complex_structure_golden_test",
    emb_file = "//testdata:complex_structure.emb",
    golden_file = "//testdata/golden_cpp:complex_structure.emb.h",
)

cpp_golden_test(
    name = "condition_golden_test",
    emb_file = "//testdata:condition.emb",
    golden_file = "//testdata/golden_cpp:condition.emb.h",
)

cpp_golden_test(
    name = "cpp_namespace_golden_test",
    emb_file = "//testdata:cpp_namespace.emb",
    golden_file = "//testdata/golden_cpp:cpp_namespace.emb.h",
)

cpp_golden_test(
    name = "dynamic_size_golden_test",
    emb_file = "//testdata:dynamic_size.emb",
    golden_file = "//testdata/golden_cpp:dynamic_size.emb.h",
)

cpp_golden_test(
    name = "enum_case_golden_test",
    emb_file = "//testdata:enum_case.emb",
    golden_file = "//testdata/golden_cpp:enum_case.emb.h",
)

cpp_golden_test(
    name = "enum_golden_test",
    emb_file = "//testdata:enum.emb",
    golden_file = "//testdata/golden_cpp:enum.emb.h",
)

cpp_golden_test(
    name = "explicit_sizes_golden_test",
    emb_file = "//testdata:explicit_sizes.emb",
    golden_file = "//testdata/golden_cpp:explicit_sizes.emb.h",
)

cpp_golden_test(
    name = "float_golden_test",
    emb_file = "//testdata:float.emb",
    golden_file = "//testdata/golden_cpp:float.emb.h",
)

cpp_golden_test(
    name = "imported_golden_test",
    emb_file = "//testdata:imported.emb",
    golden_file = "//testdata/golden_cpp:imported.emb.h",
)

cpp_golden_test(
    name = "inline_type_golden_test",
    emb_file = "//testdata:inline_type.emb",
    golden_file = "//testdata/golden_cpp:inline_type.emb.h",
)

cpp_golden_test(
    name = "int_sizes_golden_test",
    emb_file = "//testdata:int_sizes.emb",
    golden_file = "//testdata/golden_cpp:int_sizes.emb.h",
)

cpp_golden_test(
    name = "large_array_golden_test",
    emb_file = "//testdata:large_array.emb",
    golden_file = "//testdata/golden_cpp:large_array.emb.h",
)

cpp_golden_test(
    name = "nested_structure_golden_test",
    emb_file = "//testdata:nested_structure.emb",
    golden_file = "//testdata/golden_cpp:nested_structure.emb.h",
)

cpp_golden_test(
    name = "next_keyword_golden_test",
    emb_file = "//testdata:next_keyword.emb",
    golden_file = "//testdata/golden_cpp:next_keyword.emb.h",
)

cpp_golden_test(
    name = "no_cpp_namespace_golden_test",
    emb_file = "//testdata:no_cpp_namespace.emb",
    golden_file = "//testdata/golden_cpp:no_cpp_namespace.emb.h",
)

cpp_golden_test(
    name = "no_enum_traits_golden_test",
    emb_file = "//testdata:no_enum_traits.emb",
    golden_file = "//testdata/golden_cpp:no_enum_traits.emb.h",
)

cpp_golden_test(
    name = "parameters_golden_test",
    emb_file = "//testdata:parameters.emb",
    golden_file = "//testdata/golden_cpp:parameters.emb.h",
)

cpp_golden_test(
    name = "requires_golden_test",
    emb_file = "//testdata:requires.emb",
    golden_file = "//testdata/golden_cpp:requires.emb.h",
)

cpp_golden_test(
    name = "start_size_range_golden_test",
    emb_file = "//testdata:start_size_range.emb",
    golden_file = "//testdata/golden_cpp:start_size_range.emb.h",
)

cpp_golden_test(
    name = "subtypes_golden_test",
    emb_file = "//testdata:subtypes.emb",
    golden_file = "//testdata/golden_cpp:subtypes.emb.h",
)

cpp_golden_test(
    name = "text_format_golden_test",
    emb_file = "//testdata:text_format.emb",
    golden_file = "//testdata/golden_cpp:text_format.emb.h",
)

cpp_golden_test(
    name = "uint_sizes_golden_test",
    emb_file = "//testdata:uint_sizes.emb",
    golden_file = "//testdata/golden_cpp:uint_sizes.emb.h",
)

cpp_golden_test(
    name = "virtual_field_golden_test",
    emb_file = "//testdata:virtual_field.emb",
    golden_file = "//testdata/golden_cpp:virtual_field.emb.h",
)

cpp_golden_test(
    name = "importer_golden_test",
    emb_file = "//testdata:importer.emb",
    golden_file = "//testdata/golden_cpp:importer.emb.h",
)

cpp_golden_test(
    name = "importer2_golden_test",
    emb_file = "//testdata:importer2.emb",
    golden_file = "//testdata/golden_cpp:importer2.emb.h",
)

cpp_golden_test(
    name = "imported_genfiles_golden_test",
    emb_file = "//testdata:imported_genfiles.emb",
    golden_file = "//testdata/golden_cpp:imported_genfiles.emb.h",
)
