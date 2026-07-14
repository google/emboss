load("@rules_rust//rust:defs.bzl", "rust_library")

package(
    default_applicable_licenses = ["//:license"],
    default_visibility = ["//visibility:public"],
)

rust_library(
    name = "emboss_runtime",
    srcs = [
        "src/lib.rs",
        "src/prelude.rs",
    ],
)
