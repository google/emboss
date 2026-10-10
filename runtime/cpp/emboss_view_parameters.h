// Copyright 2019 Google LLC
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

// Helper classes for constructing the `Parameters` template argument to view
// classes.

#ifndef EMBOSS_RUNTIME_CPP_EMBOSS_VIEW_PARAMETERS_H_
#define EMBOSS_RUNTIME_CPP_EMBOSS_VIEW_PARAMETERS_H_

#include <type_traits>

#include "runtime/cpp/emboss_defines.h"

namespace emboss {
namespace support {

struct AllValuesAreOk {
  template <typename ValueType>
  static EMBOSS_ALWAYS_INLINE constexpr bool ValueIsOk(ValueType) {
    return true;
  }
};

template <int kBitsParam, typename Verifier>
struct FixedSizeViewParameters {
  static constexpr int kBits = kBitsParam;
  static EMBOSS_ALWAYS_INLINE constexpr bool AllValuesAreOk() {
    return ::std::is_same<Verifier, ::emboss::support::AllValuesAreOk>::value;
  }
  template <typename ValueType>
  static EMBOSS_ALWAYS_INLINE constexpr bool ValueIsOk(ValueType value) {
    return Verifier::ValueIsOk(value);
  }
};

}  // namespace support
}  // namespace emboss

#endif  // EMBOSS_RUNTIME_CPP_EMBOSS_VIEW_PARAMETERS_H_
