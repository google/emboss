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

"""Macro to run tests both with and without optimizations."""

load("@rules_cc//cc:cc_test.bzl", "cc_test")

def emboss_cc_util_test(name, copts = [], **kwargs):
    """Constructs two cc_test targets, with and without optimizations."""
    cc_test(
        name = name,
        copts = copts + ["-Wsign-compare"],
        **kwargs
    )
    cc_test(
        name = name + "_no_opts",
        copts = copts + [
            # This is generally a dangerous flag for an individual target, but
            # these tests do not depend on any other .cc files that might
            # #include any Emboss headers.
            "-DEMBOSS_NO_OPTIMIZATIONS",
        ],
        **kwargs
    )
