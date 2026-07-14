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

# -*- mode: python; -*-
# vim:set ft=blazebuild:
"""Build defs for Emboss.

This file exports emboss_library, which creates an Emboss library, and
cc_emboss_library, which creates a header file and can be used as a dep in a
`cc_library`, `cc_binary`, or `cc_test` rule.

There is also a convenience macro, `emboss_cc_library()`, which creates an
`emboss_library` and a `cc_emboss_library` based on it.
"""

load("@rules_cc//cc:find_cc_toolchain.bzl", "find_cc_toolchain", "use_cc_toolchain")
load("@rules_cc//cc/common:cc_common.bzl", "cc_common")
load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")
load("@rules_rust//rust:defs.bzl", "rust_library")

def emboss_cc_library(name, srcs, deps = [], import_dirs = [], enable_enum_traits = True, **kwargs):
    """Constructs a C++ library from an .emb file.

    Args:
      name: The name of the target.
      srcs: A list containing exactly one .emb source file.
      deps: A list of emboss_library dependencies.
      import_dirs: A list of directories to add to the import path.
      enable_enum_traits: Whether to generate enum traits.
      **kwargs: Additional arguments to pass to underlying rules.
    """
    if len(srcs) != 1:
        fail(
            "Must specify exactly one Emboss source file for emboss_cc_library.",
            "srcs",
        )

    emboss_library(
        name = name + "_ir",
        srcs = srcs,
        deps = [dep + "_ir" for dep in deps],
        import_dirs = import_dirs,
        **kwargs
    )

    cc_emboss_library(
        name = name,
        deps = [":" + name + "_ir"],
        enable_enum_traits = enable_enum_traits,
        **kwargs
    )

# Full Starlark rules for emboss_library and cc_emboss_library.
#
# This implementation is loosely based on the proto_library and
# cc_proto_library rules that are included with Bazel.

EmbossInfo = provider(
    doc = "Encapsulates information provided by a `emboss_library.`",
    fields = {
        "direct_source": "(File) The `.emb` source files from the `srcs`" +
                         " attribute.",
        "transitive_sources": "(depset[File]) The `.emb` files from `srcs` " +
                              "and all `deps`.",
        "transitive_roots": "(list[str]) The root paths for all " +
                            "transitive_sources.",
        "direct_ir": "(list[File]) The `.emb.ir` files generated from the " +
                     "`srcs`.",
        "transitive_ir": "(depset[File]) The `.emb.ir` files generated from " +
                         "transitive_srcs.",
    },
)

def _emboss_library_impl(ctx):
    deps = [dep[EmbossInfo] for dep in ctx.attr.deps]
    outs = []
    if len(ctx.attr.srcs) != 1:
        fail("`srcs` attribute must contain exactly one label.", attr = "srcs")
    src = ctx.files.srcs[0]
    out = ctx.actions.declare_file(src.basename + ".ir", sibling = src)
    outs.append(out)
    inputs = depset(
        direct = [src],
        transitive = [dep.transitive_sources for dep in deps],
    )

    # If the file is in an external repo, we want to use the path to that repo
    # as the root (e.g. ./external/my-repo) so that import paths are resolved
    # relative to the external repo root.
    fixed_src_root = src.root.path
    if src.path.startswith("external/"):
        path_segments = src.path.split("/")[:2]
        fixed_src_root = "/".join(path_segments)

    transitive_roots = depset(
        direct = [fixed_src_root],
        transitive = [dep.transitive_roots for dep in deps],
    )

    imports = ["--import-dir=" + root for root in transitive_roots.to_list()]
    imports_arg = ["--import-dir=" + impt.path for impt in ctx.files.import_dirs]
    ctx.actions.run(
        inputs = inputs.to_list(),
        outputs = [out],
        arguments = [src.path, "--output-file=" + out.path] + imports + imports_arg,
        executable = ctx.executable._emboss_compiler,
        mnemonic = "Emboss",
    )
    transitive_sources = depset(
        direct = [src],
        transitive = [dep.transitive_sources for dep in deps],
    )
    transitive_ir = depset(
        direct = outs,
        transitive = [dep.transitive_ir for dep in deps],
    )
    return [
        EmbossInfo(
            direct_source = src,
            transitive_sources = transitive_sources,
            transitive_roots = transitive_roots,
            direct_ir = outs,
            transitive_ir = transitive_ir,
        ),
        DefaultInfo(
            files = depset(outs),
        ),
    ]

emboss_library = rule(
    _emboss_library_impl,
    attrs = {
        "srcs": attr.label_list(
            allow_files = [".emb"],
        ),
        "deps": attr.label_list(
            providers = [EmbossInfo],
        ),
        "import_dirs": attr.label_list(
            allow_files = True,
        ),
        "_emboss_compiler": attr.label(
            executable = True,
            cfg = "exec",
            allow_files = True,
            default = Label(
                "@com_google_emboss//compiler/front_end:emboss_front_end",
            ),
        ),
    },
    provides = [EmbossInfo],
)

EmbossCcHeaderInfo = provider(
    fields = {
        "headers": "(list[File]) The `.emb.h` headers from this rule.",
        "transitive_headers": "(list[File]) The `.emb.h` headers from this " +
                              "rule and all dependencies.",
    },
    doc = "Provide cc emboss headers.",
)

def _cc_emboss_aspect_impl(target, ctx):
    cc_toolchain = find_cc_toolchain(ctx, mandatory = True)
    emboss_cc_compiler = ctx.executable._emboss_cc_compiler
    emboss_info = target[EmbossInfo]
    feature_configuration = cc_common.configure_features(
        ctx = ctx,
        cc_toolchain = cc_toolchain,
        requested_features = list(ctx.features),
        unsupported_features = list(ctx.disabled_features),
    )
    src = target[EmbossInfo].direct_source
    headers = [ctx.actions.declare_file(src.basename + ".h", sibling = src)]
    args = ctx.actions.args()
    args.add("--input-file")
    args.add_all(emboss_info.direct_ir)
    args.add("--output-file")
    args.add_all(headers)
    if not ctx.attr.enable_enum_traits:
        args.add("--no-cc-enum-traits")
    ctx.actions.run(
        executable = emboss_cc_compiler,
        arguments = [args],
        inputs = emboss_info.direct_ir,
        outputs = headers,
        mnemonic = "EmbossCc",
    )
    runtime_cc_info = ctx.attr._emboss_cc_runtime[CcInfo]
    transitive_headers = depset(
        direct = headers,
        transitive = [
            dep[EmbossCcHeaderInfo].transitive_headers
            for dep in ctx.rule.attr.deps
        ],
    )
    (cc_compilation_context, _cc_compilation_outputs) = cc_common.compile(
        name = ctx.label.name,
        actions = ctx.actions,
        feature_configuration = feature_configuration,
        cc_toolchain = cc_toolchain,
        public_hdrs = headers,
        private_hdrs = transitive_headers.to_list(),
        compilation_contexts = [runtime_cc_info.compilation_context] + [
            dep[CcInfo].compilation_context
            for dep in ctx.rule.attr.deps
            if CcInfo in dep
        ],
    )
    return [
        CcInfo(compilation_context = cc_compilation_context),
        EmbossCcHeaderInfo(
            headers = depset(headers),
            transitive_headers = transitive_headers,
        ),
    ]

_cc_emboss_aspect = aspect(
    implementation = _cc_emboss_aspect_impl,
    attr_aspects = ["deps"],
    fragments = ["cpp"],
    required_providers = [EmbossInfo],
    attrs = {
        "_cc_toolchain": attr.label(
            default = "@rules_cc//cc:current_cc_toolchain",
        ),
        "_emboss_cc_compiler": attr.label(
            executable = True,
            cfg = "exec",
            default = "@com_google_emboss//compiler/back_end/cpp:emboss_codegen_cpp",
        ),
        "_emboss_cc_runtime": attr.label(
            default = "@com_google_emboss//runtime/cpp:cpp_utils",
        ),
        "enable_enum_traits": attr.bool(
            default = True,
        ),
    },
    toolchains = use_cc_toolchain(),
)

def _cc_emboss_library_impl(ctx):
    if len(ctx.attr.deps) != 1:
        fail("`deps` attribute must contain exactly one label.", attr = "deps")
    dep = ctx.attr.deps[0]
    return [
        dep[CcInfo],
        dep[EmbossInfo],
        DefaultInfo(files = dep[EmbossCcHeaderInfo].headers),
    ]

cc_emboss_library = rule(
    implementation = _cc_emboss_library_impl,
    attrs = {
        "deps": attr.label_list(
            aspects = [_cc_emboss_aspect],
            allow_rules = ["emboss_library"],
            allow_files = False,
        ),
        "enable_enum_traits": attr.bool(
            default = True,
        ),
    },
    provides = [CcInfo, EmbossInfo],
)

def _rust_emboss_codegen_impl(ctx):
    if len(ctx.attr.deps) != 1:
        fail("`deps` attribute must contain exactly one label.", attr = "deps")
    dep = ctx.attr.deps[0]
    emboss_info = dep[EmbossInfo]

    src = emboss_info.direct_source
    out_file = ctx.actions.declare_file(src.basename + ".rs")

    args = ctx.actions.args()
    args.add("--input-file")
    args.add_all(emboss_info.direct_ir)
    args.add("--output-file")
    args.add(out_file)

    ctx.actions.run(
        inputs = emboss_info.direct_ir,
        outputs = [out_file],
        executable = ctx.executable._emboss_rust_compiler,
        arguments = [args],
        mnemonic = "EmbossRust",
    )

    return [DefaultInfo(files = depset([out_file]))]

_rust_emboss_codegen = rule(
    implementation = _rust_emboss_codegen_impl,
    attrs = {
        "deps": attr.label_list(
            providers = [EmbossInfo],
            allow_rules = ["emboss_library"],
            allow_files = False,
        ),
        "_emboss_rust_compiler": attr.label(
            executable = True,
            cfg = "exec",
            default = Label("//compiler/back_end/experimental/rust:emboss_codegen_rust"),
        ),
    },
)

def _derive_workspace_path(src, package):
    if src.startswith("//"):
        if ":" in src:
            pkg, name = src[2:].split(":", 1)
        else:
            parts = src[2:].split("/")
            pkg = "/".join(parts[:-1])
            name = parts[-1]
        return pkg + "/" + name if pkg else name
    elif src.startswith("@"):
        return src.replace(":", "/").replace("@", "")
    else:
        return package + "/" + src if package else src

def _derive_crate_name(src, package):
    path = _derive_workspace_path(src, package)
    return path.replace("/", "_").replace(".", "_").replace("-", "_")

def emboss_rust_library(name, srcs, deps = [], rust_deps = [], import_dirs = [], **kwargs):
    """Constructs a Rust library from an .emb file.

    Args:
      name: The name of the resulting rust_library.
      srcs: A list containing exactly one .emb source file.
      deps: A list of emboss_rust_library dependencies.
      rust_deps: Dependencies to forward to the rust_library.
      import_dirs: A list of directories to add to the import path.
      **kwargs: Additional arguments to pass to rust_library.
    """
    if len(srcs) != 1:
        fail(
            "Must specify exactly one Emboss source file for emboss_rust_library.",
            "srcs",
        )

    emboss_library_name = name + "_ir"
    
    emboss_library(
        name = emboss_library_name,
        srcs = srcs,
        deps = [dep + "_ir" for dep in deps],
        import_dirs = import_dirs,
    )

    codegen_name = name + "_srcs"

    _rust_emboss_codegen(
        name = codegen_name,
        deps = [":" + emboss_library_name],
    )

    crate_name = kwargs.pop("crate_name", _derive_crate_name(srcs[0], native.package_name()))

    rust_library(
        name = name,
        srcs = [":" + codegen_name],
        crate_name = crate_name,
        deps = rust_deps + deps + ["//runtime/experimental/rust:emboss_runtime"],
        **kwargs
    )
