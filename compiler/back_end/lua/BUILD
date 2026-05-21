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

# Emboss Wireshark Lua dissector code generator.

load("@rules_python//python:py_binary.bzl", "py_binary")
load("@rules_python//python:py_library.bzl", "py_library")
load("@rules_python//python:py_test.bzl", "py_test")
load(":build_defs.bzl", "lua_golden_test")

package(
    default_applicable_licenses = ["//:license"],
    default_visibility = [
        "//visibility:private",
    ],
)

py_binary(
    name = "emboss_codegen_lua",
    srcs = ["emboss_codegen_lua.py"],
    visibility = ["//visibility:public"],
    deps = [
        ":dissector_generator",
        "//compiler/util:ir_data",
    ],
)

py_library(
    name = "attributes",
    srcs = ["attributes.py"],
    deps = [
        "//compiler/util:attribute_util",
    ],
)

py_library(
    name = "dissector_generator",
    srcs = ["dissector_generator.py"],
    deps = [
        ":attributes",
        "//compiler/util:attribute_util",
        "//compiler/util:error",
        "//compiler/util:ir_data",
        "//compiler/util:ir_util",
    ],
)

py_test(
    name = "dissector_generator_test",
    srcs = ["dissector_generator_test.py"],
    deps = [
        ":dissector_generator",
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

# NOTE: When adding or removing lua_golden_test(...) rules below, also update
# the GOLDENS list in scripts/regenerate_goldens.py so the two stay in sync.

lua_golden_test(
    name = "enum_golden_test",
    emb_file = "//testdata:enum.emb",
    golden_file = "//testdata/golden_lua:enum.emb.lua",
)

lua_golden_test(
    name = "nested_structure_golden_test",
    emb_file = "//testdata:nested_structure.emb",
    golden_file = "//testdata/golden_lua:nested_structure.emb.lua",
)

lua_golden_test(
    name = "uint_sizes_golden_test",
    emb_file = "//testdata:uint_sizes.emb",
    golden_file = "//testdata/golden_lua:uint_sizes.emb.lua",
)

lua_golden_test(
    name = "int_sizes_golden_test",
    emb_file = "//testdata:int_sizes.emb",
    golden_file = "//testdata/golden_lua:int_sizes.emb.lua",
)

lua_golden_test(
    name = "wireshark_golden_test",
    emb_file = "//testdata:wireshark.emb",
    golden_file = "//testdata/golden_lua:wireshark.emb.lua",
)
