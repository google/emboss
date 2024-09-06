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

# Generator for emboss_arithmetic_maximum_operation_generated.h.

# Maximum number of explicit arguments in the recursive overloads.  This script
# will generate overloads for 5...OVERLOADS arguments, plus a special overload
# that handles >OVERLOADS arguments using a variadic template.
#
# This should probably be a power of 2.
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
// runtime/cpp/generators/maximum_operation_do.py"""
)

for i in range(5, OVERLOADS + 1):
    print(
        """
  template <typename T>
  static inline constexpr T Do({0}) {{
    return Do(Do({1}), Do({2}));
  }}""".strip().format(
            ", ".join(["T v{}".format(n) for n in range(i)]),
            ", ".join(["v{}".format(n) for n in range(i // 2)]),
            ", ".join(["v{}".format(n) for n in range(i // 2, i)]),
        )
    )

# The "more than OVERLOADS arguments" overload uses a variadic template to
# handle the remaining arguments, even though all arguments should have the
# same type; this is necessary because C++11 variadic functions are either
# variadic templates (one template argument per argument) or C-style variadic
# functions (which operate under very different rules).
#
# This also uses one explicit argument, rest0, to ensure that it does not get
# confused with the last non-variadic overload.
print(
    """
  template <typename T, typename... RestT>
  static inline constexpr T Do({0}, T rest0, RestT... rest) {{
    return Do(Do({1}), Do(rest0, rest...));
  }}""".format(
        ", ".join(["T v{}".format(n) for n in range(OVERLOADS)]),
        ", ".join(["v{}".format(n) for n in range(OVERLOADS)]),
        OVERLOADS,
    )
)
