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

// Tests of packed field support.
#include <stdint.h>

#include <type_traits>
#include <utility>
#include <vector>

#include "gtest/gtest.h"
#include "testdata/complex_offset.emb.h"

namespace emboss {
namespace test {
namespace {

TEST(PackedFields, PerformanceOfOk) {
  ::std::array<char, 64> values = {0};
  const auto view = MakePackedFieldsView(&values);
  EXPECT_TRUE(view.Ok());
  EXPECT_TRUE(view.length6().Ok());
  EXPECT_TRUE(view.data6().Ok());
}

}  // namespace
}  // namespace test
}  // namespace emboss
