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
load(":build_defs.bzl", "emboss_cc_test")

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
