#!/usr/bin/python3

# Copyright 2020 Google LLC
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

# Generator for emboss_arithmetic_all_known_generated.h.

# Maximum number of explicit arguments in the recursive overloads.  This script
# will generate overloads for 1...OVERLOADS-1 arguments, plus a special overload
# that handles >=OVERLOADS arguments using a variadic template.
OVERLOADS = 64

# Copyright header in the generated code complies with Google policies.
print(
    """// Copyright 2020 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// GENERATED CODE.  DO NOT EDIT.  REGENERATE WITH
// runtime/cpp/generators/all_known.py"""
)

for i in range(1, OVERLOADS + 1):
    print(
        """
template <{}>
inline constexpr bool AllKnown({}) {{
  return {};
}}""".format(
            ", ".join(
                ["typename T{}".format(n) for n in range(i)]
                + (["typename... RestT"] if i == OVERLOADS else [])
            ),
            ", ".join(
                ["T{} v{}".format(n, n) for n in range(i)]
                + (["RestT... rest"] if i == OVERLOADS else [])
            ),
            " && ".join(
                ["v{}.Known()".format(n) for n in range(i)]
                + (["AllKnown(rest...)"] if i == OVERLOADS else [])
            ),
        )
    )
