load("@rules_rust//rust:defs.bzl", "rust_test")
load("//:build_defs.bzl", "emboss_rust_library")
rust_test(
    name = "imported_test",
    srcs = ["imported_test.rs"],
    deps = [
        "//runtime/experimental/rust:emboss_runtime",
        "//testdata:imported_emb_rs",
    ],
)

rust_test(
    name = "importer_test",
    srcs = ["importer_test.rs"],
    deps = [
        "//runtime/experimental/rust:emboss_runtime",
        "//testdata:imported_emb_rs",
        "//testdata:importer_emb_rs",
    ],
)

rust_test(
    name = "next_keyword_test",
    srcs = ["next_keyword_test.rs"],
    deps = [
        "//runtime/experimental/rust:emboss_runtime",
        "//testdata:next_keyword_emb_rs",
    ],
)

rust_test(
    name = "nested_structure_test",
    srcs = ["nested_structure_test.rs"],
    deps = [
        "//testdata:nested_structure_emb_rs",
        "//runtime/experimental/rust:emboss_runtime",
    ],
)
rust_test(
    name = "endian_test",
    srcs = ["endian_test.rs"],
    deps = [
        "//testdata:endian_emb_rs",
        "//runtime/experimental/rust:emboss_runtime",
    ],
)
rust_test(
    name = "int_sizes_test",
    srcs = ["int_sizes_test.rs"],
    deps = [
        "//testdata:int_sizes_emb_rs",
    ],
)
rust_test(
    name = "enum_test",
    srcs = ["enum_test.rs"],
    deps = [
        "//runtime/experimental/rust:emboss_runtime",
        "//testdata:enum_emb_rs",
    ],
)
rust_test(
    name = "dynamic_size_test",
    srcs = ["dynamic_size_test.rs"],
    deps = [
        "//runtime/experimental/rust:emboss_runtime",
        "//testdata:dynamic_size_emb_rs",
    ],
)
rust_test(
    name = "auto_array_size_test",
    srcs = ["auto_array_size_test.rs"],
    deps = [
        "//runtime/experimental/rust:emboss_runtime",
        "//testdata:auto_array_size_emb_rs",
    ],
)
