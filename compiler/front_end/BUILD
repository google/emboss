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

# Emboss front end
#
# The code in this directory translates an Emboss definition file (.emb) to an
# intermediate representation (IR).  The IR is passed to back end code
# generators to generate code in various languages.

load("@rules_python//python:py_binary.bzl", "py_binary")
load("@rules_python//python:py_library.bzl", "py_library")
load("@rules_python//python:py_test.bzl", "py_test")

package(
    default_visibility = [
        "//:__subpackages__",
    ],
)

py_library(
    name = "tokenizer",
    srcs = ["tokenizer.py"],
    deps = [
        "//compiler/util:error",
        "//compiler/util:parser_types",
    ],
)

py_test(
    name = "tokenizer_test",
    srcs = ["tokenizer_test.py"],
    python_version = "PY3",
    deps = [
        ":tokenizer",
        "//compiler/util:error",
        "//compiler/util:parser_types",
    ],
)

py_library(
    name = "lr1",
    srcs = ["lr1.py"],
    deps = [
        "//compiler/util:parser_types",
    ],
)

py_test(
    name = "lr1_test",
    srcs = ["lr1_test.py"],
    python_version = "PY3",
    deps = [
        ":lr1",
        "//compiler/util:parser_types",
    ],
)

py_library(
    name = "module_ir",
    srcs = ["module_ir.py"],
    deps = [
        "//compiler/util:ir_data",
        "//compiler/util:name_conversion",
        "//compiler/util:parser_types",
    ],
)

py_test(
    name = "module_ir_test",
    srcs = ["module_ir_test.py"],
    data = [
        "//testdata:golden_files",
    ],
    python_version = "PY3",
    deps = [
        ":module_ir",
        ":parser",
        ":tokenizer",
        "//compiler/util:ir_data",
        "//compiler/util:test_util",
    ],
)

py_library(
    name = "parser",
    srcs = ["parser.py"],
    data = [
        "error_examples",
    ],
    deps = [
        ":cached_parser",
        ":lr1",
        ":make_parser",
        ":module_ir",
        "//compiler/util:parser_types",
        "//compiler/util:simple_memoizer",
    ],
)

py_library(
    name = "cached_parser",
    srcs = ["generated/cached_parser.py"],
    deps = [
        ":lr1",
        "//compiler/util:parser_types",
    ],
)

py_test(
    name = "parser_test",
    srcs = ["parser_test.py"],
    python_version = "PY3",
    deps = [
        ":parser",
        ":tokenizer",
    ],
)

py_library(
    name = "make_parser",
    srcs = ["make_parser.py"],
    data = [
        "error_examples",
    ],
    deps = [
        ":lr1",
        ":module_ir",
        ":tokenizer",
        "//compiler/util:resources",
        "//compiler/util:simple_memoizer",
    ],
)

py_test(
    name = "make_parser_test",
    srcs = ["make_parser_test.py"],
    python_version = "PY3",
    deps = [
        ":lr1",
        ":make_parser",
        ":tokenizer",
        "//compiler/util:parser_types",
    ],
)

py_library(
    name = "glue",
    srcs = ["glue.py"],
    data = [
        "prelude.emb",
    ],
    visibility = ["//:__subpackages__"],
    deps = [
        ":attribute_checker",
        ":constraints",
        ":dependency_checker",
        ":expression_bounds",
        ":lr1",
        ":module_ir",
        ":parser",
        ":symbol_resolver",
        ":synthetics",
        ":tokenizer",
        ":type_check",
        ":write_inference",
        "//compiler/util:error",
        "//compiler/util:ir_data",
        "//compiler/util:parser_types",
        "//compiler/util:resources",
    ],
)

py_test(
    name = "glue_test",
    srcs = ["glue_test.py"],
    data = [
        "//testdata:golden_files",
    ],
    python_version = "PY3",
    deps = [
        ":glue",
        "//compiler/util:error",
        "//compiler/util:ir_data",
        "//compiler/util:parser_types",
        "//compiler/util:test_util",
    ],
)

py_library(
    name = "synthetics",
    srcs = ["synthetics.py"],
    visibility = ["//visibility:private"],
    deps = [
        "//compiler/util:expression_parser",
        "//compiler/util:ir_data",
        "//compiler/util:traverse_ir",
    ],
)

py_test(
    name = "synthetics_test",
    srcs = ["synthetics_test.py"],
    python_version = "PY3",
    deps = [
        ":glue",
        ":synthetics",
        "//compiler/util:test_util",
    ],
)

py_library(
    name = "symbol_resolver",
    srcs = ["symbol_resolver.py"],
    visibility = ["//visibility:private"],
    deps = [
        "//compiler/util:error",
        "//compiler/util:ir_data",
        "//compiler/util:ir_util",
        "//compiler/util:traverse_ir",
    ],
)

py_test(
    name = "symbol_resolver_test",
    srcs = ["symbol_resolver_test.py"],
    python_version = "PY3",
    deps = [
        ":glue",
        ":symbol_resolver",
        "//compiler/util:error",
        "//compiler/util:test_util",
    ],
)

py_library(
    name = "write_inference",
    srcs = ["write_inference.py"],
    visibility = ["//visibility:private"],
    deps = [
        ":attributes",
        ":expression_bounds",
        "//compiler/util:ir_data",
        "//compiler/util:ir_util",
        "//compiler/util:traverse_ir",
    ],
)

py_test(
    name = "write_inference_test",
    srcs = ["write_inference_test.py"],
    python_version = "PY3",
    deps = [
        ":glue",
        ":write_inference",
        "//compiler/util:ir_data",
        "//compiler/util:test_util",
    ],
)

py_library(
    name = "attribute_checker",
    srcs = ["attribute_checker.py"],
    deps = [
        ":attributes",
        ":type_check",
        "//compiler/util:attribute_util",
        "//compiler/util:error",
        "//compiler/util:ir_data",
        "//compiler/util:ir_util",
        "//compiler/util:traverse_ir",
    ],
)

py_library(
    name = "attributes",
    srcs = ["attributes.py"],
    deps = [],
)

py_test(
    name = "attribute_checker_test",
    timeout = "long",
    srcs = ["attribute_checker_test.py"],
    python_version = "PY3",
    deps = [
        ":attribute_checker",
        ":glue",
        "//compiler/util:error",
        "//compiler/util:ir_data",
        "//compiler/util:ir_util",
        "//compiler/util:test_util",
    ],
)

py_library(
    name = "type_check",
    srcs = ["type_check.py"],
    deps = [
        ":attributes",
        "//compiler/util:error",
        "//compiler/util:ir_data",
        "//compiler/util:ir_util",
        "//compiler/util:traverse_ir",
    ],
)

py_test(
    name = "type_check_test",
    srcs = ["type_check_test.py"],
    python_version = "PY3",
    deps = [
        ":glue",
        ":type_check",
        "//compiler/util:error",
        "//compiler/util:test_util",
    ],
)

py_library(
    name = "expression_bounds",
    srcs = ["expression_bounds.py"],
    data = [
        "reserved_words",
    ],
    deps = [
        ":attributes",
        "//compiler/util:ir_data",
        "//compiler/util:ir_util",
        "//compiler/util:traverse_ir",
    ],
)

py_test(
    name = "expression_bounds_test",
    srcs = ["expression_bounds_test.py"],
    python_version = "PY3",
    deps = [
        ":expression_bounds",
        ":glue",
        "//compiler/util:test_util",
    ],
)

py_library(
    name = "constraints",
    srcs = ["constraints.py"],
    data = [
        "reserved_words",
    ],
    deps = [
        ":attributes",
        "//compiler/util:error",
        "//compiler/util:ir_data",
        "//compiler/util:ir_util",
        "//compiler/util:resources",
        "//compiler/util:traverse_ir",
    ],
)

py_test(
    name = "constraints_test",
    srcs = ["constraints_test.py"],
    python_version = "PY3",
    deps = [
        ":constraints",
        ":glue",
        "//compiler/util:error",
        "//compiler/util:test_util",
    ],
)

py_library(
    name = "dependency_checker",
    srcs = ["dependency_checker.py"],
    deps = [
        "//compiler/util:error",
        "//compiler/util:ir_data",
        "//compiler/util:ir_util",
        "//compiler/util:traverse_ir",
    ],
)

py_test(
    name = "dependency_checker_test",
    srcs = ["dependency_checker_test.py"],
    python_version = "PY3",
    deps = [
        ":dependency_checker",
        ":glue",
        "//compiler/util:error",
        "//compiler/util:test_util",
    ],
)

py_binary(
    name = "emboss_front_end",
    srcs = ["emboss_front_end.py"],
    python_version = "PY3",
    visibility = ["//visibility:public"],
    deps = [
        ":glue",
        ":module_ir",
        "//compiler/util:error",
    ],
)

py_binary(
    name = "format",
    srcs = ["format.py"],
    main = "format.py",
    python_version = "PY3",
    visibility = ["//visibility:public"],
    deps = [
        ":format_emb",
        ":parser",
        ":tokenizer",
        "//compiler/util:error",
    ],
)

py_library(
    name = "format_emb",
    srcs = ["format_emb.py"],
    deps = [
        ":module_ir",
        ":tokenizer",
        "//compiler/util:parser_types",
    ],
)

py_test(
    name = "format_emb_test",
    srcs = ["format_emb_test.py"],
    data = [
        "//testdata:format_embs",
    ],
    python_version = "PY3",
    deps = [
        ":format_emb",
        ":module_ir",
        ":parser",
        ":tokenizer",
    ],
)

py_binary(
    name = "generate_grammar_md",
    srcs = ["generate_grammar_md.py"],
    python_version = "PY3",
    deps = [
        ":constraints",
        ":module_ir",
        ":tokenizer",
    ],
)

py_binary(
    name = "generate_cached_parser",
    srcs = ["generate_cached_parser.py"],
    python_version = "PY3",
    deps = [
        ":lr1",
        ":make_parser",
        "//compiler/util:parser_types",
    ],
)

py_test(
    name = "docs_are_up_to_date_test",
    srcs = ["docs_are_up_to_date_test.py"],
    data = [
        "//doc:grammar_md",
    ],
    python_version = "PY3",
    deps = [
        ":generate_grammar_md",
    ],
)

py_test(
    name = "cached_parser_is_up_to_date_test",
    srcs = ["cached_parser_is_up_to_date_test.py"],
    data = [
        "generated/cached_parser.py",
    ],
    python_version = "PY3",
    deps = [
        ":generate_cached_parser",
    ],
)
