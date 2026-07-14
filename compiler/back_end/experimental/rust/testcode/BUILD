load("@rules_rust//rust:defs.bzl", "rust_test")
load("//:build_defs.bzl", "emboss_rust_library")

emboss_rust_library(
    name = "imported_emb_rs",
    deps = ["//testdata:imported_emboss_ir"],
)

emboss_rust_library(
    name = "next_keyword_emb_rs",
    deps = ["//testdata:next_keyword_emboss_ir"],
)

rust_test(
    name = "imported_test",
    srcs = ["imported_test.rs"],
    deps = [
        ":imported_emb_rs",
        "//runtime/experimental/rust:emboss_runtime",
    ],
)

rust_test(
    name = "next_keyword_test",
    srcs = ["next_keyword_test.rs"],
    deps = [
        ":next_keyword_emb_rs",
        "//runtime/experimental/rust:emboss_runtime",
    ],
)
