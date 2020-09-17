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

#ifndef EMBOSS_RUNTIME_CPP_EMBOSS_CONSTANT_VIEW_H_
#define EMBOSS_RUNTIME_CPP_EMBOSS_CONSTANT_VIEW_H_

#include "runtime/cpp/emboss_maybe.h"

namespace emboss {
namespace support {

// MaybeConstantView is a "view" type that "reads" a value passed into its
// constructor.
//
// This is used internally by generated structure view classes to provide views
// of parameters; in this way, parameters can be treated like fields in the
// generated code.
template <typename ValueT>
class MaybeConstantView {
 public:
  MaybeConstantView() : value_() {}
  constexpr explicit MaybeConstantView(ValueT value) : value_(value) {}
  MaybeConstantView(const MaybeConstantView &) = default;
  MaybeConstantView(MaybeConstantView &&) = default;
  MaybeConstantView &operator=(const MaybeConstantView &) = default;
  MaybeConstantView &operator=(MaybeConstantView &&) = default;
  ~MaybeConstantView() = default;

  constexpr ValueT Read() const { return value_.Value(); }
  constexpr ValueT UncheckedRead() const { return value_.ValueOrDefault(); }
  constexpr bool Ok() const { return value_.Known(); }

 private:
  ::emboss::support::Maybe<ValueT> value_;
};

}  // namespace support
}  // namespace emboss

#endif  // EMBOSS_RUNTIME_CPP_EMBOSS_CONSTANT_VIEW_H_
