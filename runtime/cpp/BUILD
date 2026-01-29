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

# Emboss C++ Runtime.

load("@rules_cc//cc:cc_library.bzl", "cc_library")

filegroup(
    name = "raw_headers",
    srcs = [
        "emboss_arithmetic.h",
        "emboss_arithmetic_all_known_generated.h",
        "emboss_arithmetic_maximum_operation_generated.h",
        "emboss_array_view.h",
        "emboss_bit_util.h",
        "emboss_constant_view.h",
        "emboss_cpp_types.h",
        "emboss_cpp_util.h",
        "emboss_defines.h",
        "emboss_enum_view.h",
        "emboss_maybe.h",
        "emboss_memory_util.h",
        "emboss_prelude.h",
        "emboss_text_util.h",
        "emboss_view_parameters.h",
    ],
    visibility = ["//:__subpackages__"],
)

cc_library(
    name = "cpp_utils",
    hdrs = [
        ":raw_headers",
    ],
    visibility = ["//visibility:public"],
    deps = [
        # BEGIN INSERT_MY_SITE_DEFINES_TARGET_HERE
        # "//MY_SITE_DEFINES:TARGET",
        # END INSERT_MY_SITE_DEFINES_TARGET_HERE
    ],
)
