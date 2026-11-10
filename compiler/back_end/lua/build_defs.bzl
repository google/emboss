# Copyright 2026 Google LLC
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
"""Bazel test macros for the Emboss Wireshark Lua backend."""

load("@rules_python//python:py_test.bzl", "py_test")

def lua_golden_test(name, emb_file, golden_file, import_dirs = []):
    """Defines a Lua golden file test.

    Args:
        name: The name of the test.
        emb_file: The .emb file to test.
        golden_file: The golden .lua file.
        import_dirs: A list of import directories.
    """
    py_test(
        name = name,
        main = ":run_one_golden_test.py",
        srcs = [":run_one_golden_test.py", ":one_golden_test.py"],
        tags = ["golden"],
        args = [
            "$(location //compiler/front_end:emboss_front_end)",
            "$(location :emboss_codegen_lua)",
            "$(location %s)" % emb_file,
            "$(location %s)" % golden_file,
        ] + ["--import-dir=" + d for d in import_dirs],
        data = [
            "//compiler/front_end:emboss_front_end",
            ":emboss_codegen_lua",
            emb_file,
            golden_file,
            "//testdata:test_embs",
        ] + import_dirs,
        deps = [":one_golden_test_lib"],
    )
