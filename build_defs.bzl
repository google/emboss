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

This file exports the emboss_cc_library rule, which accepts an .emb file and
produces a corresponding C++ library.
"""

def emboss_cc_library(name, srcs, deps = [], visibility = None):
    """Constructs a C++ library from an .emb file."""
    if len(srcs) != 1:
        fail(
            "Must specify exactly one Emboss source file for emboss_cc_library.",
            "srcs",
        )

    native.filegroup(
        # The original .emb file must be visible to any other emboss_cc_library
        # that specifies this emboss_cc_library in its deps.  This rule makes the
        # original .emb available to dependent rules.
        # TODO(bolms): As an optimization, use the precompiled IR instead of
        # reparsing the raw .embs.
        name = name + "__emb",
        srcs = srcs,
        visibility = visibility,
    )

    native.genrule(
        # The generated header may be used in non-cc_library rules.
        name = name + "_header",
        tools = [
            # TODO(bolms): Make "emboss" driver program.
            "@com_google_emboss//compiler/front_end:emboss_front_end",
            "@com_google_emboss//compiler/back_end/cpp:emboss_codegen_cpp",
        ],
        srcs = srcs + [dep + "__emb" for dep in deps],
        cmd = ("$(location @com_google_emboss//compiler/front_end:emboss_front_end) " +
               "--output-ir-to-stdout " +
               "--import-dir=. " +
               "--import-dir='$(GENDIR)' " +
               "$(location {}) > $(@D)/$$(basename $(OUTS) .h).ir; " +
               "$(location @com_google_emboss//compiler/back_end/cpp:emboss_codegen_cpp) " +
               "< $(@D)/$$(basename $(OUTS) .h).ir > " +
               "$(OUTS); " +
               "rm $(@D)/$$(basename $(OUTS) .h).ir").format(") $location( ".join(srcs)),
        outs = [src + ".h" for src in srcs],
        # This rule should only be visible to the following rule.
        visibility = ["//visibility:private"],
    )

    native.cc_library(
        name = name,
        hdrs = [
            ":" + name + "_header",
        ],
        deps = deps + [
            "@com_google_emboss//runtime/cpp:cpp_utils",
        ],
        visibility = visibility,
    )
