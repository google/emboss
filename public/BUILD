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

# Emboss public definitions.

load(
    ":build_defs.bzl",
    "emboss_cc_util_test",
)

py_library(
    name = "ir_pb2",
    srcs = ["ir_pb2.py"],
    visibility = ["//visibility:public"],
)

cc_library(
    name = "cpp_utils",
    hdrs = [
        "emboss_arithmetic.h",
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
    deps = [
    ],
    visibility = ["//visibility:public"],
)

emboss_cc_util_test(
    name = "emboss_prelude_test",
    srcs = [
        "emboss_prelude_test.cc",
    ],
    copts = ["-DEMBOSS_FORCE_ALL_CHECKS"],
    deps = [
        ":cpp_utils",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_util_test(
    name = "emboss_arithmetic_test",
    srcs = [
        "emboss_arithmetic_test.cc",
    ],
    copts = ["-DEMBOSS_FORCE_ALL_CHECKS"],
    deps = [
        ":cpp_utils",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_util_test(
    name = "emboss_array_view_test",
    srcs = [
        "emboss_array_view_test.cc",
    ],
    copts = ["-DEMBOSS_FORCE_ALL_CHECKS"],
    deps = [
        ":cpp_utils",
        "@com_google_googletest//:gtest_main",
        "@com_google_absl//absl/strings:str_format",
    ],
)

emboss_cc_util_test(
    name = "emboss_bit_util_test",
    srcs = [
        "emboss_bit_util_test.cc",
    ],
    copts = ["-DEMBOSS_FORCE_ALL_CHECKS"],
    deps = [
        ":cpp_utils",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_util_test(
    name = "emboss_constant_view_test",
    srcs = [
        "emboss_constant_view_test.cc",
    ],
    copts = ["-DEMBOSS_FORCE_ALL_CHECKS"],
    deps = [
        ":cpp_utils",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_util_test(
    name = "emboss_cpp_types_test",
    srcs = [
        "emboss_cpp_types_test.cc",
    ],
    copts = ["-DEMBOSS_FORCE_ALL_CHECKS"],
    deps = [
        ":cpp_utils",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_util_test(
    name = "emboss_defines_test",
    srcs = [
        "emboss_defines_test.cc",
    ],
    copts = ["-DEMBOSS_FORCE_ALL_CHECKS"],
    deps = [
        ":cpp_utils",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_util_test(
    name = "emboss_maybe_test",
    srcs = [
        "emboss_maybe_test.cc",
    ],
    copts = ["-DEMBOSS_FORCE_ALL_CHECKS"],
    deps = [
        ":cpp_utils",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_util_test(
    name = "emboss_memory_util_test",
    srcs = [
        "emboss_memory_util_test.cc",
    ],
    copts = ["-DEMBOSS_FORCE_ALL_CHECKS"],
    deps = [
        ":cpp_utils",
        "@com_google_googletest//:gtest_main",
    ],
)

emboss_cc_util_test(
    name = "emboss_text_util_test",
    srcs = [
        "emboss_text_util_test.cc",
    ],
    copts = [
        "-DEMBOSS_FORCE_ALL_CHECKS",
        "-Wsign-compare",
    ],
    deps = [
        ":cpp_utils",
        "@com_google_googletest//:gtest_main",
    ],
)
