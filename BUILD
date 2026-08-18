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

load("@pip//:requirements.bzl", "requirement")
load("@rules_license//rules:license.bzl", "license")
load("@rules_python//python:py_binary.bzl", "py_binary")
load("@rules_python//python:py_test.bzl", "py_test")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

package(
    default_applicable_licenses = ["//:license"],
)

license(
    name = "license",
    license_kinds = [
        "@rules_license//licenses/spdx:Apache-2.0",
    ],
    license_text = "LICENSE",
)

exports_files([
    "build_defs.bzl",
    "embossc",
    "LICENSE",
])

# Black formatter binary
py_binary(
    name = "black_runner",
    srcs = ["scripts/black_runner.py"],
    deps = [requirement("black")],
)

# Fix formatting: bazel run //:black_fix -- .
sh_binary(
    name = "black_fix",
    srcs = ["scripts/black_fix.sh"],
    data = [":black_runner"],
)

# Check formatting: bazel run //:black_check
sh_binary(
    name = "black_check",
    srcs = ["scripts/black_check.sh"],
    data = [":black_runner"],
)

# Tests the `embossc` driver itself: which back end `--generate` selects, and
# where each one puts its output.  The two back end binaries are data deps so
# that their runfiles supply the `compiler/` tree `embossc` imports.
py_test(
    name = "embossc_test",
    size = "small",
    srcs = ["scripts/embossc_test.py"],
    data = [
        "embossc",
        "//compiler/back_end/cpp:emboss_codegen_cpp",
        "//compiler/front_end:emboss_front_end",
        "//testdata:test_embs",
    ],
    deps = [requirement("clang-format")],
)
