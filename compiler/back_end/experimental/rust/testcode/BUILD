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

emboss_rust_library(
    name = "nested_structure_emb_rs",
    deps = ["//testdata:nested_structure_emboss_ir"],
)

rust_test(
    name = "nested_structure_test",
    srcs = ["nested_structure_test.rs"],
    deps = [
        ":nested_structure_emb_rs",
        "//runtime/experimental/rust:emboss_runtime",
    ],
)

emboss_rust_library(
    name = "endian_emb_rs",
    deps = ["//testdata:endian_emboss_ir"],
)

rust_test(
    name = "endian_test",
    srcs = ["endian_test.rs"],
    deps = [
        ":endian_emb_rs",
        "//runtime/experimental/rust:emboss_runtime",
    ],
)

emboss_rust_library(
    name = "int_sizes_emb_rs",
    deps = ["//testdata:int_sizes_emboss_ir"],
)

rust_test(
    name = "int_sizes_test",
    srcs = ["int_sizes_test.rs"],
    deps = [
        ":int_sizes_emb_rs",
    ],
)

emboss_rust_library(
    name = "enum_emb_rs",
    deps = ["//testdata:enum_emboss_ir"],
)

rust_test(
    name = "enum_test",
    srcs = ["enum_test.rs"],
    deps = [
        ":enum_emb_rs",
        "//runtime/experimental/rust:emboss_runtime",
    ],
)
