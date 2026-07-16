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

load("@rules_python//python:py_binary.bzl", "py_binary")

package(
    default_applicable_licenses = ["//:license"],
    default_visibility = [
        "//visibility:private",
    ],
)

py_binary(
    name = "emboss_codegen_rust",
    srcs = ["emboss_codegen_rust.py"],
    data = ["generated_code_templates"],
    visibility = ["//visibility:public"],
    deps = [
        "//compiler/back_end/util:code_template",
        "//compiler/front_end:module_ir",
        "//compiler/util:error",
        "//compiler/util:ir_data",
        "//compiler/util:ir_util",
        "//compiler/util:resources",
    ],
)
