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
#include "testdata/int_sizes.emb.h"

namespace emboss {
namespace test {
namespace {

alignas(8) static const ::std::uint8_t kIntSizes[36] = {
    0x02,                    // 0:1    one_byte == 2
    0xfc, 0xfe,              // 1:3    two_byte == -260
    0x66, 0x55, 0x44,        // 3:6    three_byte == 0x445566
    0xfa, 0xfa, 0xfb, 0xfc,  // 6:10   four_byte == -0x03040506
    0x21, 0x43, 0x65, 0x87,  // 10:14  five_byte
    0x29,                    // 14:15  five_byte == 0x2987654321
    0x44, 0x65, 0x87, 0xa9,  // 15:19  six_byte
    0xcb, 0xed,              // 19:21  six_byte == -0x123456789abc
    0x97, 0xa6, 0xb5, 0xc4,  // 21:25  seven_byte
    0xd3, 0xe2, 0x71,        // 25:28  seven_byte == 0x71e2d3c4b5a697
    0xfa, 0xfa, 0xfb, 0xfc,  // 28:32  eight_byte
    0xfd, 0xfe, 0xff, 0x80,  // 32:36  eight_byte == -0x7f00010203040506
};

TEST(SizesView, CanReadSizes) {
  auto view = MakeAlignedSizesView<const ::std::uint8_t, 8>(kIntSizes,
                                                            sizeof kIntSizes);
  EXPECT_EQ(2, view.one_byte().Read());
  EXPECT_EQ(-260, view.two_byte().Read());
  EXPECT_EQ(0x445566, view.three_byte().Read());
  EXPECT_EQ(-0x03040506, view.four_byte().Read());
  EXPECT_EQ(0x2987654321, view.five_byte().Read());
  EXPECT_EQ(-0x123456789abc, view.six_byte().Read());
  EXPECT_EQ(0x71e2d3c4b5a697, view.seven_byte().Read());
  EXPECT_EQ(-0x7f00010203040506, view.eight_byte().Read());
  // Test that the views return appropriate integer widths.
  EXPECT_EQ(1U, sizeof(view.one_byte().Read()));
  EXPECT_EQ(2U, sizeof(view.two_byte().Read()));
  EXPECT_EQ(4U, sizeof(view.three_byte().Read()));
  EXPECT_EQ(4U, sizeof(view.four_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.five_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.six_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.seven_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.eight_byte().Read()));
}

TEST(SizesWriter, CanWriteSizes) {
  ::std::uint8_t buffer[sizeof kIntSizes];
  auto writer = SizesWriter(buffer, sizeof buffer);
  writer.one_byte().Write(2);
  writer.two_byte().Write(-260);
  writer.three_byte().Write(0x445566);
  writer.four_byte().Write(-0x03040506);
  writer.five_byte().Write(0x2987654321);
  writer.six_byte().Write(-0x123456789abc);
  writer.seven_byte().Write(0x71e2d3c4b5a697);
  writer.eight_byte().Write(-0x7f00010203040506);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kIntSizes,
                                               kIntSizes + sizeof kIntSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

alignas(8) static const ::std::uint8_t kIntSizesNegativeOnes[36] = {
    0xff,                    // 0:1    one_byte == -1
    0xff, 0xff,              // 1:3    two_byte == -1
    0xff, 0xff, 0xff,        // 3:6    three_byte == -1
    0xff, 0xff, 0xff, 0xff,  // 6:10   four_byte == -1
    0xff, 0xff, 0xff, 0xff,  // 10:14  five_byte
    0xff,                    // 14:15  five_byte == -1
    0xff, 0xff, 0xff, 0xff,  // 15:19  six_byte
    0xff, 0xff,              // 19:21  six_byte == -1
    0xff, 0xff, 0xff, 0xff,  // 21:25  seven_byte
    0xff, 0xff, 0xff,        // 25:28  seven_byte == -1
    0xff, 0xff, 0xff, 0xff,  // 28:32  eight_byte
    0xff, 0xff, 0xff, 0xff,  // 32:36  eight_byte == -1
};

TEST(SizesView, CanReadNegativeOne) {
  auto view = MakeAlignedSizesView<const ::std::uint8_t, 8>(
      kIntSizesNegativeOnes, sizeof kIntSizesNegativeOnes);
  EXPECT_EQ(-1, view.one_byte().Read());
  EXPECT_EQ(-1, view.two_byte().Read());
  EXPECT_EQ(-1, view.three_byte().Read());
  EXPECT_EQ(-1, view.four_byte().Read());
  EXPECT_EQ(-1, view.five_byte().Read());
  EXPECT_EQ(-1, view.six_byte().Read());
  EXPECT_EQ(-1, view.seven_byte().Read());
  EXPECT_EQ(-1, view.eight_byte().Read());
}

TEST(SizesView, CanWriteNegativeOne) {
  ::std::uint8_t buffer[sizeof kIntSizesNegativeOnes];
  auto writer = SizesWriter(buffer, sizeof buffer);
  writer.one_byte().Write(-1);
  writer.two_byte().Write(-1);
  writer.three_byte().Write(-1);
  writer.four_byte().Write(-1);
  writer.five_byte().Write(-1);
  writer.six_byte().Write(-1);
  writer.seven_byte().Write(-1);
  writer.eight_byte().Write(-1);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(
                kIntSizesNegativeOnes,
                kIntSizesNegativeOnes + sizeof kIntSizesNegativeOnes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(SizesView, CopyFrom) {
  ::std::array</**/ ::std::uint8_t, sizeof kIntSizesNegativeOnes> buf_x = {};
  ::std::array</**/ ::std::uint8_t, sizeof kIntSizesNegativeOnes> buf_y = {};

  auto x = SizesWriter(&buf_x);
  auto y = SizesWriter(&buf_y);

  constexpr int kValue = -1;
  x.one_byte().Write(kValue);
  EXPECT_NE(x.one_byte().Read(), y.one_byte().Read());
  y.one_byte().CopyFrom(x.one_byte());
  EXPECT_EQ(x.one_byte().Read(), y.one_byte().Read());
}

TEST(SizesView, TryToCopyFrom) {
  ::std::array</**/ ::std::uint8_t, sizeof kIntSizesNegativeOnes> buf_x = {};
  ::std::array</**/ ::std::uint8_t, sizeof kIntSizesNegativeOnes> buf_y = {};

  auto x = SizesWriter(&buf_x);
  auto y = SizesWriter(&buf_y);

  constexpr int kValue = -1;
  x.one_byte().Write(kValue);
  EXPECT_NE(x.one_byte().Read(), y.one_byte().Read());
  EXPECT_TRUE(y.one_byte().TryToCopyFrom(x.one_byte()));
  EXPECT_EQ(x.one_byte().Read(), y.one_byte().Read());
}

}  // namespace
}  // namespace test
}  // namespace emboss
