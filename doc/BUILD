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

# Documentation for Emboss.
#
# This BUILD file only exists to export grammar.md for use in a test in
# emboss/misc.

filegroup(
    name = "grammar_md",
    srcs = [
        "__init__.py",
        "grammar.md",
    ],
    # This should only be needed by docs_are_up_to_date_test.
    visibility = ["//:__subpackages__"],
)
