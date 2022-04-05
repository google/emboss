// Copyright 2022 Google LLC
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

// Tests of generated code for structures using the `$next` keyword.
// Note that `$next` is removed from the IR before it reaches the back end, so
// this is really testing that the front end desugared correctly.
#include <stdint.h>

#include <type_traits>
#include <utility>
#include <vector>

#include "gtest/gtest.h"
#include "testdata/next_keyword.emb.h"

namespace emboss {
namespace test {
namespace {

// For reference in the code below, the NextKeyword structure is defined as:
//
// [$default byte_order: "LittleEndian"]
// struct NextKeyword:
//   0       [+4]  UInt  value32
//   $next   [+2]  UInt  value16
//   $next   [+1]  UInt  value8
//   $next+3 [+1]  UInt  value8_offset
TEST(NextKeyword, FieldsAreCorrectlyLocated) {
  ::std::array<char, NextKeyword::IntrinsicSizeInBytes()> values = {
    1, 0, 0, 0,
    2, 0,
    3,
    5, 6, 7, 4,
  };
  const auto view = MakeNextKeywordView(&values);
  ASSERT_TRUE(view.Ok());
  EXPECT_EQ(1, view.value32().Read());
  EXPECT_EQ(2, view.value16().Read());
  EXPECT_EQ(3, view.value8().Read());
  EXPECT_EQ(4, view.value8_offset().Read());
}

}  // namespace
}  // namespace test
}  // namespace emboss
