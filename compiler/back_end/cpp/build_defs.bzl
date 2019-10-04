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
"""Rule to generate cc_tests with and without system-specific optimizations."""

def emboss_cc_test(name, copts = None, no_w_sign_compare = False, **kwargs):
    """Generates cc_test rules with and without -DEMBOSS_NO_OPTIMIZATIONS."""
    native.cc_test(
        name = name,
        copts = ["-DEMBOSS_FORCE_ALL_CHECKS"] + (copts or []),
        **kwargs
    )
    native.cc_test(
        name = name + "_no_opts",
        copts = [
            "-DEMBOSS_NO_OPTIMIZATIONS",
            "-DEMBOSS_FORCE_ALL_CHECKS",
        ] + ([] if no_w_sign_compare else ["-Wsign-compare"]) + (copts or []),
        **kwargs
    )
