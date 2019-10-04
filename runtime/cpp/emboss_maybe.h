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

// Definition of the Maybe<T> template class.
#ifndef EMBOSS_RUNTIME_CPP_EMBOSS_MAYBE_H_
#define EMBOSS_RUNTIME_CPP_EMBOSS_MAYBE_H_

#include <utility>

#include "runtime/cpp/emboss_defines.h"

namespace emboss {
// TODO(bolms): Should Maybe be a public type (i.e., live in ::emboss)?
namespace support {

// Maybe<T> is similar to, but much more restricted than, C++17's std::optional.
// It is intended for use in Emboss's expression system, wherein a non-Known()
// Maybe<T> will usually (but not always) poison the result of an operation.
//
// As such, Maybe<> is intended for use with small, copyable T's: specifically,
// integers, enums, and booleans.  It may not perform well with other types.
template <typename T>
class Maybe final {
 public:
  constexpr Maybe() : value_(), known_(false) {}
  constexpr explicit Maybe(T value)
      : value_(::std::move(value)), known_(true) {}
  constexpr Maybe(const Maybe<T> &) = default;
  ~Maybe() = default;
  Maybe &operator=(const Maybe &) = default;
  Maybe &operator=(T value) {
    value_ = ::std::move(value);
    known_ = true;
    return *this;
  }
  Maybe &operator=(const T &value) {
    value_ = value;
    known_ = true;
    return *this;
  }

  constexpr bool Known() const { return known_; }
  T Value() const {
    EMBOSS_CHECK(Known());
    return value_;
  }
  constexpr T ValueOr(T default_value) const {
    return known_ ? value_ : default_value;
  }
  // A non-Ok() Maybe value-initializes value_ to a default (by explicitly
  // calling the nullary constructor on value_ in the initializer list), so it
  // is safe to just return value_ here.  For integral types and enums, value_
  // will be 0, for bool it will be false, and for other types it depends on the
  // constructor's behavior.
  constexpr T ValueOrDefault() const { return value_; }

 private:
  T value_;
  bool known_;
};

}  // namespace support
}  // namespace emboss

#endif  // EMBOSS_RUNTIME_CPP_EMBOSS_MAYBE_H_
