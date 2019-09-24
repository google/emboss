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

// Tests for the generated View class from subtypes.emb.
//
// These tests check that nested types work.
#include <stdint.h>

#include <vector>

#include "gtest/gtest.h"
#include "testdata/subtypes.emb.h"

namespace emboss {
namespace test {
namespace {

TEST(SubtypesTest, InnerEnumNames) {
  EXPECT_EQ(0, static_cast<int>(Out::In::InIn::InInIn::NO));
  EXPECT_EQ(0, static_cast<int>(Out::In::InInView::InInIn::NO));
}

TEST(SubtypesTest, OuterStructure) {
  ::std::uint8_t buffer[OutWriter::SizeInBytes()] = {0};
  auto view = OutWriter(buffer, sizeof buffer);
  buffer[1] = 0xcc;
  EXPECT_EQ(0xcc, view.in_1().in_in_1().in_2().field_byte().Read());
  view.in_1().in_in_1().in_2().field_byte().Write(0x88);
  EXPECT_EQ(0x88, buffer[1]);
  buffer[static_cast<int>(Out::In::InIn::outer_offset())] = 0xff;
  EXPECT_EQ(0xff, view.nested_constant_check().Read());
  view.nested_constant_check().Write(0x77);
  EXPECT_EQ(0x77, buffer[24]);

  buffer[6] = 0x7;
  buffer[7] = 0x8;
  buffer[14] = 0x6;
  buffer[22] = 0xee;
  EXPECT_EQ(0xee, view.name_collision().Read());
  EXPECT_EQ(0x7, view.in_1().name_collision().Read());
  EXPECT_EQ(0x8, view.in_1().name_collision_check().Read());
  EXPECT_EQ(0x6, view.in_2().name_collision().Read());
  EXPECT_EQ(0x6, view.in_2().name_collision().Read());
}

}  // namespace
}  // namespace test
}  // namespace emboss
