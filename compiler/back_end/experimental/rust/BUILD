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
