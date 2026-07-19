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

// Unknowability records *why* a Maybe<T> has no value.  For the vast majority
// of Unknown values -- an absent field, a short backing buffer, a false
// existence condition -- the value is merely `kUnreadable`: reading more bytes
// could still produce a Known() value.  A value is `kUndefined` when it can
// never become Known() no matter how many bytes are supplied, because the
// expression that produced it is mathematically undefined (currently only
// integer division or modulus by zero).
//
// This distinction is what lets a structure whose `$size_in_bytes` divides by
// zero report `IsComplete() == true` (there is nothing more to wait for) while
// still reporting `Ok() == false`.  See emboss_arithmetic.h for how the reason
// is propagated and merged through the expression operators, and
// doc/design_docs/division_and_modulus.md for the rationale.
//
// The reason is kept a single byte and every accessor is constexpr so that it
// does not disturb the heavily-constexpr, size-sensitive Ok() code path.
enum class Unknowability : unsigned char {
  kKnown,       // The Maybe has a value; Known() is true.
  kUnreadable,  // No value yet, but more bytes could supply one.
  kUndefined,   // No value ever; the producing expression is undefined.
};

// Maybe<T> is similar to, but much more restricted than, C++17's std::optional.
// It is intended for use in Emboss's expression system, wherein a non-Known()
// Maybe<T> will usually (but not always) poison the result of an operation.
//
// As such, Maybe<> is intended for use with small, copyable T's: specifically,
// integers, enums, and booleans.  It may not perform well with other types.
template <typename T>
class Maybe final {
 public:
  // A default-constructed Maybe is Unknown for the ordinary `kUnreadable`
  // reason.  This is by far the most common Unknown (an unreadable field), so
  // most Unknown-constructing sites -- field reads, absent parameters -- need
  // no change to get the right reason.
  constexpr Maybe() : value_(), unknowability_(Unknowability::kUnreadable) {}
  constexpr explicit Maybe(T value)
      : value_(::std::move(value)), unknowability_(Unknowability::kKnown) {}
  // Constructs an Unknown Maybe with an explicit reason.  Callers must pass a
  // non-kKnown reason (there is no value to hold); passing kKnown would produce
  // a nominally-Known() Maybe with a default-initialized value.
  constexpr explicit Maybe(Unknowability unknowability)
      : value_(), unknowability_(unknowability) {}
  constexpr Maybe(const Maybe<T> &) = default;
  ~Maybe() = default;
  Maybe &operator=(const Maybe &) = default;
  Maybe &operator=(T value) {
    value_ = ::std::move(value);
    unknowability_ = Unknowability::kKnown;
    return *this;
  }
  Maybe &operator=(const T &value) {
    value_ = value;
    unknowability_ = Unknowability::kKnown;
    return *this;
  }

  constexpr bool Known() const {
    return unknowability_ == Unknowability::kKnown;
  }
  // True iff this Maybe is Unknown specifically because its value is undefined
  // (division/modulus by zero) rather than merely unreadable.
  constexpr bool IsUndefined() const {
    return unknowability_ == Unknowability::kUndefined;
  }
  // The reason this Maybe has (or has not) a value.  Used by the expression
  // operators to merge reasons when combining operands.
  constexpr Unknowability Reason() const { return unknowability_; }
  T Value() const {
    EMBOSS_CHECK(Known());
    return value_;
  }
  constexpr T ValueOr(T default_value) const {
    return Known() ? value_ : default_value;
  }
  // A non-Ok() Maybe value-initializes value_ to a default (by explicitly
  // calling the nullary constructor on value_ in the initializer list), so it
  // is safe to just return value_ here.  For integral types and enums, value_
  // will be 0, for bool it will be false, and for other types it depends on the
  // constructor's behavior.
  constexpr T ValueOrDefault() const { return value_; }

 private:
  T value_;
  Unknowability unknowability_;
};

}  // namespace support
}  // namespace emboss

#endif  // EMBOSS_RUNTIME_CPP_EMBOSS_MAYBE_H_
