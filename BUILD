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
load("@rules_python//python:py_binary.bzl", "py_binary")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")
load("@rules_shell//shell:sh_test.bzl", "sh_test")

exports_files([
    "build_defs.bzl",
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
