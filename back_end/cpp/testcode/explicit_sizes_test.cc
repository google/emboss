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

// Tests for the generated View class for Container and Box from
// nested_structure.emb.
//
// These tests check that nested structures work.
#include <stdint.h>

#include <vector>

#include "gtest/gtest.h"
#include "testdata/explicit_sizes.emb.h"

namespace emboss {
namespace test {
namespace {

static const ::std::uint8_t kUIntArrays[21] = {
    0x21,                    // one_nibble == { 0x1, 0x2 }
    0x10, 0x20,              // two_nibble == { 0x10, 0x20 }
    0x10, 0x11, 0x20, 0x22,  // four_nibble == { 0x1110, 0x2220 }
};

TEST(SizesView, CanReadSizes) {
  auto outer_view = BitArrayContainerView(kUIntArrays, sizeof kUIntArrays);
  auto view = outer_view.uint_arrays();
  EXPECT_EQ(0x1, view.one_nibble()[0].Read());
  EXPECT_EQ(0x2, view.one_nibble()[1].Read());
  EXPECT_EQ(0x10, view.two_nibble()[0].Read());
  EXPECT_EQ(0x20, view.two_nibble()[1].Read());
  EXPECT_EQ(0x1110, view.four_nibble()[0].Read());
  EXPECT_EQ(0x2220, view.four_nibble()[1].Read());
}

}  // namespace
}  // namespace test
}  // namespace emboss
