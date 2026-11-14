// Copyright 2026 Google LLC
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

#include <array>

#include "gtest/gtest.h"
#include "testdata/parameters.emb.h"

namespace emboss {
namespace test {
namespace {

TEST(BiasedValue, EqualityComparesParameters) {
  ::std::array<char, 1> bytes = {10};
  const auto view = MakeBiasedValueView(20, &bytes);
  const auto same = MakeBiasedValueView(20, &bytes);
  const auto different = MakeBiasedValueView(30, &bytes);
  EXPECT_TRUE(view.Equals(same));
  EXPECT_FALSE(view.Equals(different));
  EXPECT_TRUE(view.UncheckedEquals(same));
  EXPECT_FALSE(view.UncheckedEquals(different));
}

TEST(AxisPair, EqualityComparesEnumParameters) {
  ::std::array<char, 8> bytes = {};
  const auto view =
      MakeAxisPairView(AxisType::X_AXIS, AxisType::Y_AXIS, &bytes);
  const auto same =
      MakeAxisPairView(AxisType::X_AXIS, AxisType::Y_AXIS, &bytes);
  const auto different =
      MakeAxisPairView(AxisType::X_AXIS, AxisType::Z_AXIS, &bytes);
  EXPECT_TRUE(view.Equals(same));
  EXPECT_FALSE(view.Equals(different));
  EXPECT_TRUE(view.UncheckedEquals(same));
  EXPECT_FALSE(view.UncheckedEquals(different));
}

}  // namespace
}  // namespace test
}  // namespace emboss
