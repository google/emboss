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

# Emboss descriptor generator.

load("@rules_python//python:py_binary.bzl", "py_binary")
load("@rules_python//python:py_library.bzl", "py_library")
load("@rules_python//python:py_test.bzl", "py_test")
load(":build_defs.bzl", "descriptor_golden_test")

package(
    default_applicable_licenses = ["//:license"],
    default_visibility = [
        "//visibility:private",
    ],
)

py_binary(
    name = "emboss_codegen_descriptor",
    srcs = ["emboss_codegen_descriptor.py"],
    visibility = ["//visibility:public"],
    deps = [
        ":descriptor_generator",
        "//compiler/util:error",
        "//compiler/util:ir_data",
    ],
)

py_library(
    name = "descriptor_generator",
    srcs = ["descriptor_generator.py"],
    deps = [
        "//compiler/front_end:attributes",
        "//compiler/util:expression_printer",
        "//compiler/util:ir_data",
        "//compiler/util:ir_util",
    ],
)

py_test(
    name = "descriptor_generator_test",
    srcs = ["descriptor_generator_test.py"],
    deps = [
        ":descriptor_generator",
        "//compiler/front_end:glue",
        "//compiler/util:test_util",
    ],
)

py_library(
    name = "one_golden_test_lib",
    srcs = ["one_golden_test.py"],
)

py_binary(
    name = "run_one_golden_test",
    srcs = ["run_one_golden_test.py"],
    deps = [":one_golden_test_lib"],
)

# NOTE: When adding or removing descriptor_golden_test(...) rules below, also
# update the DESCRIPTOR_GOLDENS list in scripts/regenerate_goldens.py so the two
# stay in sync.

descriptor_golden_test(
    name = "anonymous_bits_golden_test",
    emb_file = "//testdata:anonymous_bits.emb",
    golden_file = "//testdata/golden_descriptor:anonymous_bits.emb.json",
)

descriptor_golden_test(
    name = "bits_golden_test",
    emb_file = "//testdata:bits.emb",
    golden_file = "//testdata/golden_descriptor:bits.emb.json",
)

descriptor_golden_test(
    name = "condition_golden_test",
    emb_file = "//testdata:condition.emb",
    golden_file = "//testdata/golden_descriptor:condition.emb.json",
)

descriptor_golden_test(
    name = "dynamic_size_golden_test",
    emb_file = "//testdata:dynamic_size.emb",
    golden_file = "//testdata/golden_descriptor:dynamic_size.emb.json",
)

descriptor_golden_test(
    name = "enum_golden_test",
    emb_file = "//testdata:enum.emb",
    golden_file = "//testdata/golden_descriptor:enum.emb.json",
)

descriptor_golden_test(
    name = "nested_structure_golden_test",
    emb_file = "//testdata:nested_structure.emb",
    golden_file = "//testdata/golden_descriptor:nested_structure.emb.json",
)

descriptor_golden_test(
    name = "parameters_golden_test",
    emb_file = "//testdata:parameters.emb",
    golden_file = "//testdata/golden_descriptor:parameters.emb.json",
)

descriptor_golden_test(
    name = "requires_golden_test",
    emb_file = "//testdata:requires.emb",
    golden_file = "//testdata/golden_descriptor:requires.emb.json",
)

descriptor_golden_test(
    name = "virtual_field_golden_test",
    emb_file = "//testdata:virtual_field.emb",
    golden_file = "//testdata/golden_descriptor:virtual_field.emb.json",
)
