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

"""Locator for the clang-format binary used by the C++ back end.

This module is the single seam between Emboss and a concrete clang-format
binary. Downstream consumers that cannot use the upstream `clang-format`
PyPI package can replace this whole file -- and the matching pip dep in
the neighboring BUILD file -- with a shim that returns an alternative
clang-format path, without touching any other Emboss source.
"""


def get_clang_format_path():
    """Returns the path to the clang-format executable."""
    from clang_format import get_executable

    return get_executable("clang-format")
