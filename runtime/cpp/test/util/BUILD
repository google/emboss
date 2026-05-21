load("@rules_cc//cc:cc_library.bzl", "cc_library")
load("//runtime/cpp/test:build_defs.bzl", "emboss_cc_util_test")

cc_library(
    name = "noncontiguous_container",
    hdrs = ["noncontiguous_container.h"],
    visibility = ["//runtime/cpp/test:__pkg__", "//visibility:public"],
)

emboss_cc_util_test(
    name = "noncontiguous_container_test",
    srcs = ["noncontiguous_container_test.cc"],
    deps = [
        ":noncontiguous_container",
        "//runtime/cpp:cpp_utils",
        "@com_google_googletest//:gtest_main",
    ],
)
