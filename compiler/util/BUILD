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

# Shared utilities for Emboss back ends.

load("@rules_python//python:py_library.bzl", "py_library")
load("@rules_python//python:py_test.bzl", "py_test")

package(
    default_visibility = ["//compiler:__subpackages__"],
)

py_library(
    name = "ir_data",
    srcs = [
        "ir_data.py",
        "ir_data_fields.py",
        "ir_data_utils.py",
    ],
    deps = [],
)

py_test(
    name = "ir_data_fields_test",
    srcs = ["ir_data_fields_test.py"],
    deps = [":ir_data"],
)

py_test(
    name = "ir_data_utils_test",
    srcs = ["ir_data_utils_test.py"],
    deps = [":expression_parser", ":ir_data"],
)

py_library(
    name = "expression_parser",
    srcs = ["expression_parser.py"],
    deps = [
        "//compiler/front_end:module_ir",
        "//compiler/front_end:parser",
        "//compiler/front_end:tokenizer",
    ],
)

py_library(
    name = "ir_util",
    srcs = ["ir_util.py"],
    deps = [":ir_data"],
)

py_test(
    name = "ir_util_test",
    srcs = ["ir_util_test.py"],
    python_version = "PY3",
    deps = [
        ":expression_parser",
        ":ir_data",
        ":ir_util",
    ],
)

py_library(
    name = "attribute_util",
    srcs = ["attribute_util.py"],
    deps = [
        ":error",
        ":ir_data",
        ":ir_util",
        ":traverse_ir",
    ],
)

py_library(
    name = "simple_memoizer",
    srcs = ["simple_memoizer.py"],
    deps = [],
)

py_test(
    name = "simple_memoizer_test",
    srcs = ["simple_memoizer_test.py"],
    python_version = "PY3",
    deps = [
        ":simple_memoizer",
    ],
)

py_library(
    name = "test_util",
    testonly = 1,
    srcs = ["test_util.py"],
    deps = [],
)

py_test(
    name = "test_util_test",
    srcs = ["test_util_test.py"],
    python_version = "PY3",
    deps = [
        ":test_util",
        "//compiler/util:ir_data",
        "//compiler/util:parser_types",
    ],
)

py_library(
    name = "traverse_ir",
    srcs = ["traverse_ir.py"],
    deps = [
        ":simple_memoizer",
        ":ir_data",
    ],
)

py_test(
    name = "traverse_ir_test",
    srcs = ["traverse_ir_test.py"],
    python_version = "PY3",
    deps = [
        ":traverse_ir",
        ":ir_data",
    ],
)

py_library(
    name = "parser_types",
    srcs = ["parser_types.py"],
    deps = [
        ":ir_data",
    ],
)

py_test(
    name = "parser_types_test",
    srcs = ["parser_types_test.py"],
    python_version = "PY3",
    deps = [
        ":parser_types",
        ":ir_data",
    ],
)

py_library(
    name = "error",
    srcs = [
        "error.py",
    ],
    deps = [
        ":parser_types",
    ],
)

py_test(
    name = "error_test",
    srcs = ["error_test.py"],
    python_version = "PY3",
    deps = [
        ":error",
        ":parser_types",
    ],
)

py_library(
    name = "name_conversion",
    srcs = ["name_conversion.py"],
    deps = [],
)

py_test(
    name = "name_conversion_test",
    srcs = ["name_conversion_test.py"],
    python_version = "PY3",
    deps = [
        ":name_conversion",
    ],
)

py_library(
    name = "resources",
    srcs = ["resources.py"],
    deps = [],
)
