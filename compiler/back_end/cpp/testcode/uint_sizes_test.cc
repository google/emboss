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
#include "testdata/uint_sizes.emb.h"

namespace emboss {
namespace test {
namespace {

alignas(8) static const ::std::uint8_t kUIntSizes[36] = {
    0x02,                    // 0:1    one_byte == 2
    0x04, 0x01,              // 1:3    two_byte == 260
    0x66, 0x55, 0x44,        // 3:6    three_byte == 0x445566
    0x06, 0x05, 0x04, 0x03,  // 6:10   four_byte == 0x03040506
    0x21, 0x43, 0x65, 0x87,  // 10:14  five_byte
    0xa9,                    // 14:15  five_byte == 0xa987654321
    0xbc, 0x9a, 0x78, 0x56,  // 15:19  six_byte
    0x34, 0x12,              // 19:21  six_byte == 0x123456789abc
    0x97, 0xa6, 0xb5, 0xc4,  // 21:25  seven_byte
    0xd3, 0xe2, 0xf1,        // 25:28  seven_byte == 0xf1e2d3c4b5a697
    0x06, 0x05, 0x04, 0x03,  // 28:32  eight_byte
    0x02, 0x01, 0x00, 0xff,  // 32:36  eight_byte == 0xff00010203040506
};

TEST(SizesView, CanReadSizes) {
  auto view = MakeAlignedSizesView<const ::std::uint8_t, 8>(kUIntSizes,
                                                            sizeof kUIntSizes);
  EXPECT_EQ(2, view.one_byte().Read());
  EXPECT_EQ(260, view.two_byte().Read());
  EXPECT_EQ(0x445566U, view.three_byte().Read());
  EXPECT_EQ(0x03040506U, view.four_byte().Read());
  EXPECT_EQ(0xa987654321UL, view.five_byte().Read());
  EXPECT_EQ(0x123456789abcUL, view.six_byte().Read());
  EXPECT_EQ(0xf1e2d3c4b5a697UL, view.seven_byte().Read());
  EXPECT_EQ(0xff00010203040506UL, view.eight_byte().Read());
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
  ::std::uint8_t buffer[sizeof kUIntSizes];
  auto writer = SizesWriter(buffer, sizeof buffer);
  writer.one_byte().Write(2);
  writer.two_byte().Write(260);
  writer.three_byte().Write(0x445566U);
  writer.four_byte().Write(0x03040506U);
  writer.five_byte().Write(0xa987654321);
  writer.six_byte().Write(0x123456789abc);
  writer.seven_byte().Write(0xf1e2d3c4b5a697);
  writer.eight_byte().Write(0xff00010203040506UL);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kUIntSizes,
                                               kUIntSizes + sizeof kUIntSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(SizesView, CanReadSizesBigEndian) {
  auto view = BigEndianSizesView(kUIntSizes, sizeof kUIntSizes);
  EXPECT_EQ(2, view.one_byte().Read());
  EXPECT_EQ(0x0401, view.two_byte().Read());
  EXPECT_EQ(0x665544U, view.three_byte().Read());
  EXPECT_EQ(0x06050403U, view.four_byte().Read());
  EXPECT_EQ(0x21436587a9UL, view.five_byte().Read());
  EXPECT_EQ(0xbc9a78563412UL, view.six_byte().Read());
  EXPECT_EQ(0x97a6b5c4d3e2f1UL, view.seven_byte().Read());
  EXPECT_EQ(0x06050403020100ffUL, view.eight_byte().Read());
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

TEST(SizesWriter, CanWriteSizesBigEndian) {
  ::std::uint8_t buffer[sizeof kUIntSizes];
  auto writer = BigEndianSizesWriter(buffer, sizeof buffer);
  writer.one_byte().Write(2);
  writer.two_byte().Write(0x0401);
  writer.three_byte().Write(0x665544U);
  writer.four_byte().Write(0x06050403U);
  writer.five_byte().Write(0x21436587a9);
  writer.six_byte().Write(0xbc9a78563412);
  writer.seven_byte().Write(0x97a6b5c4d3e2f1);
  writer.eight_byte().Write(0x06050403020100ffUL);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kUIntSizes,
                                               kUIntSizes + sizeof kUIntSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(SizesView, CanReadSizesAlternatingEndian) {
  auto view = AlternatingEndianSizesView(kUIntSizes, sizeof kUIntSizes);
  EXPECT_EQ(2, view.one_byte().Read());
  EXPECT_EQ(0x0104, view.two_byte().Read());
  EXPECT_EQ(0x665544U, view.three_byte().Read());
  EXPECT_EQ(0x03040506U, view.four_byte().Read());
  EXPECT_EQ(0x21436587a9UL, view.five_byte().Read());
  EXPECT_EQ(0x123456789abcUL, view.six_byte().Read());
  EXPECT_EQ(0x97a6b5c4d3e2f1UL, view.seven_byte().Read());
  EXPECT_EQ(0xff00010203040506UL, view.eight_byte().Read());
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

TEST(SizesWriter, CanWriteSizesAlternatingEndian) {
  ::std::uint8_t buffer[sizeof kUIntSizes];
  auto writer = AlternatingEndianSizesWriter(buffer, sizeof buffer);
  writer.one_byte().Write(2);
  writer.two_byte().Write(0x0104);
  writer.three_byte().Write(0x665544U);
  writer.four_byte().Write(0x03040506);
  writer.five_byte().Write(0x21436587a9);
  writer.six_byte().Write(0x123456789abc);
  writer.seven_byte().Write(0x97a6b5c4d3e2f1);
  writer.eight_byte().Write(0xff00010203040506UL);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kUIntSizes,
                                               kUIntSizes + sizeof kUIntSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(SizesView, DecodeUIntsFromText) {
  ::std::uint8_t buffer[sizeof kUIntSizes] = {0};
  auto writer = SizesWriter(buffer, sizeof buffer);
  EXPECT_TRUE(::emboss::UpdateFromText(writer, R"(
    {
      one_byte: 2
      two_byte: 260
      three_byte: 0x445566
      four_byte: 0x03040506
      five_byte: 0xa987654321
      six_byte: 0x123456789abc
      seven_byte: 0xf1e2d3c4b5a697
      eight_byte: 0xff00010203040506
    }
  )"));
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kUIntSizes,
                                               kUIntSizes + sizeof kUIntSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
  EXPECT_EQ(2, writer.one_byte().Read());
  EXPECT_TRUE(::emboss::UpdateFromText(writer, "{one_byte:5}"));
  EXPECT_EQ(5, buffer[0]);
  EXPECT_EQ(5, writer.one_byte().Read());
  EXPECT_FALSE(::emboss::UpdateFromText(writer, "{one_byte:256}"));
  EXPECT_EQ(5, buffer[0]);
  EXPECT_EQ(5, writer.one_byte().Read());
  EXPECT_FALSE(::emboss::UpdateFromText(writer, "{three_byte:0x1000000}"));
  EXPECT_FALSE(::emboss::UpdateFromText(writer, "{no_byte:0}"));
}

TEST(SizesView, DecodeUIntsFromTextWithCommas) {
  ::std::uint8_t buffer[sizeof kUIntSizes] = {0};
  auto writer = SizesWriter(buffer, sizeof buffer);
  EXPECT_TRUE(::emboss::UpdateFromText(writer, R"(
    {
      one_byte: 2,
      two_byte: 260,
      three_byte: 0x445566,
      four_byte: 0x03040506,
      five_byte: 0xa987654321,
      six_byte: 0x123456789abc,
      seven_byte: 0xf1e2d3c4b5a697,
      eight_byte: 0xff00010203040506,
    }
  )"));
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kUIntSizes,
                                               kUIntSizes + sizeof kUIntSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(SizesView, DecodeBigEndianUIntsFromText) {
  ::std::uint8_t buffer[sizeof kUIntSizes] = {0};
  auto writer = BigEndianSizesWriter(buffer, sizeof buffer);
  EXPECT_TRUE(::emboss::UpdateFromText(writer, R"(
    {
      one_byte: 2
      two_byte: 0x0401
      three_byte: 0x665544
      four_byte: 0x06050403
      five_byte: 0x21436587a9
      six_byte: 0xbc9a78563412
      seven_byte: 0x97a6b5c4d3e2f1
      eight_byte: 0x06050403020100ff
    }
  )"));
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kUIntSizes,
                                               kUIntSizes + sizeof kUIntSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(SizesView, EncodeUIntsToText) {
  auto view = MakeAlignedSizesView<const ::std::uint8_t, 8>(kUIntSizes,
                                                            sizeof kUIntSizes);
  EXPECT_EQ(
      "{\n"
      "  one_byte: 2  # 0x2\n"
      "  two_byte: 260  # 0x104\n"
      "  three_byte: 4_478_310  # 0x44_5566\n"
      "  four_byte: 50_595_078  # 0x304_0506\n"
      "  five_byte: 728_121_033_505  # 0xa9_8765_4321\n"
      "  six_byte: 20_015_998_343_868  # 0x1234_5678_9abc\n"
      "  seven_byte: 68_084_868_553_483_927  # 0xf1_e2d3_c4b5_a697\n"
      "  eight_byte: 18_374_687_587_823_781_126  # 0xff00_0102_0304_0506\n"
      "}",
      ::emboss::WriteToString(view, ::emboss::MultilineText()));
  EXPECT_EQ(
      "{ one_byte: 2, two_byte: 260, three_byte: 4478310, four_byte: 50595078, "
      "five_byte: 728121033505, six_byte: 20015998343868, seven_byte: "
      "68084868553483927, eight_byte: 18374687587823781126 }",
      ::emboss::WriteToString(view));
}

static const ::std::uint8_t kEnumSizes[36] = {
    0x01,                    // 0:1    one_byte == VALUE1
    0x0a, 0x00,              // 1:3    two_byte == VALUE10
    0x10, 0x27, 0x00,        // 3:6    three_byte == VALUE10000
    0x64, 0x00, 0x00, 0x00,  // 6:10   four_byte == VALUE100
    0xa0, 0x86, 0x01, 0x00,  // 10:14  five_byte
    0x00,                    // 14:15  five_byte == VALUE100000
    0x40, 0x42, 0x0f, 0x00,  // 15:19  six_byte
    0x00, 0x00,              // 19:21  six_byte == VALUE1000000
    0x80, 0x96, 0x98, 0x00,  // 21:25  seven_byte
    0x00, 0x00, 0x00,        // 25:28  seven_byte == VALUE10000000
    0xe8, 0x03, 0x00, 0x00,  // 28:32  eight_byte
    0x00, 0x00, 0x00, 0x00,  // 32:36  eight_byte == VALUE1000
};

TEST(SizesView, CanReadEnumSizes) {
  auto view = EnumSizesView(kEnumSizes, sizeof kEnumSizes);
  EXPECT_EQ(Enum::VALUE1, view.one_byte().Read());
  EXPECT_EQ(Enum::VALUE10, view.two_byte().Read());
  EXPECT_EQ(Enum::VALUE10000, view.three_byte().Read());
  EXPECT_EQ(Enum::VALUE100, view.four_byte().Read());
  EXPECT_EQ(Enum::VALUE100000, view.five_byte().Read());
  EXPECT_EQ(Enum::VALUE1000000, view.six_byte().Read());
  EXPECT_EQ(Enum::VALUE10000000, view.seven_byte().Read());
  EXPECT_EQ(Enum::VALUE1000, view.eight_byte().Read());
  // Emboss enums are always derived from uint64_t.
  EXPECT_EQ(8U, sizeof(view.one_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.two_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.three_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.four_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.five_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.six_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.seven_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.eight_byte().Read()));
}

TEST(SizesWriter, CanWriteEnumSizes) {
  ::std::uint8_t buffer[sizeof kEnumSizes];
  auto writer = EnumSizesWriter(buffer, sizeof buffer);
  writer.one_byte().Write(Enum::VALUE1);
  writer.two_byte().Write(Enum::VALUE10);
  writer.three_byte().Write(Enum::VALUE10000);
  writer.four_byte().Write(Enum::VALUE100);
  writer.five_byte().Write(Enum::VALUE100000);
  writer.six_byte().Write(Enum::VALUE1000000);
  writer.seven_byte().Write(Enum::VALUE10000000);
  writer.eight_byte().Write(Enum::VALUE1000);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kEnumSizes,
                                               kEnumSizes + sizeof kEnumSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(SizesView, DecodeEnumsFromText) {
  ::std::uint8_t buffer[sizeof kEnumSizes] = {0};
  auto writer = EnumSizesWriter(buffer, sizeof buffer);
  EXPECT_TRUE(::emboss::UpdateFromText(writer, R"(
    {
      one_byte: VALUE1
      two_byte: VALUE10
      three_byte: VALUE10000
      four_byte: VALUE100
      five_byte: VALUE100000
      six_byte: VALUE1000000
      seven_byte: VALUE10000000
      eight_byte: VALUE1000
    }
  )"));
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kEnumSizes,
                                               kEnumSizes + sizeof kEnumSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(SizesView, DecodeEnumsFromIntegerText) {
  ::std::uint8_t buffer[sizeof kEnumSizes] = {0};
  auto writer = EnumSizesWriter(buffer, sizeof buffer);
  EXPECT_TRUE(::emboss::UpdateFromText(writer, R"(
    {
      one_byte: 1
      two_byte: 10
      three_byte: 10000
      four_byte: 100
      five_byte: 100000
      six_byte: 1000000
      seven_byte: 10000000
      eight_byte: 1000
    }
  )"));
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kEnumSizes,
                                               kEnumSizes + sizeof kEnumSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

static const ::std::uint8_t kExplicitlySizedEnumSizes
    [ExplicitlySizedEnumSizes::IntrinsicSizeInBytes()] = {
        0x01,                    // 0:1    one_byte == VALUE1
        0x0a, 0x00,              // 1:3    two_byte == VALUE10
        0x10, 0x27, 0x00,        // 3:6    three_byte == VALUE10000
        0x64, 0x00, 0x00, 0x00,  // 6:10   three_and_a_half_byte == VALUE100
};

TEST(SizesView, CanReadExplicitlySizedEnumSizes) {
  auto view = ExplicitlySizedEnumSizesView(kExplicitlySizedEnumSizes,
                                           sizeof kExplicitlySizedEnumSizes);
  EXPECT_EQ(ExplicitlySizedEnum::VALUE1, view.one_byte().Read());
  EXPECT_EQ(ExplicitlySizedEnum::VALUE10, view.two_byte().Read());
  EXPECT_EQ(ExplicitlySizedEnum::VALUE10000, view.three_byte().Read());
  EXPECT_EQ(ExplicitlySizedEnum::VALUE100, view.three_and_a_half_byte().Read());
  // 28-bit explicitly-sized enum should be uint32_t.
  EXPECT_EQ(4U, sizeof(view.one_byte().Read()));
  EXPECT_EQ(4U, sizeof(view.two_byte().Read()));
  EXPECT_EQ(4U, sizeof(view.three_byte().Read()));
  EXPECT_EQ(4U, sizeof(view.three_and_a_half_byte().Read()));
}

TEST(SizesWriter, CanWriteExplicitlySizedEnumSizes) {
  ::std::uint8_t buffer[sizeof kExplicitlySizedEnumSizes] = {0};
  auto writer = ExplicitlySizedEnumSizesWriter(buffer, sizeof buffer);
  writer.one_byte().Write(ExplicitlySizedEnum::VALUE1);
  writer.two_byte().Write(ExplicitlySizedEnum::VALUE10);
  writer.three_byte().Write(ExplicitlySizedEnum::VALUE10000);
  writer.three_and_a_half_byte().Write(ExplicitlySizedEnum::VALUE100);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(
                kExplicitlySizedEnumSizes,
                kExplicitlySizedEnumSizes + sizeof kExplicitlySizedEnumSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(SizesView, DecodeExplicitlySizedEnumsFromText) {
  ::std::uint8_t buffer[sizeof kExplicitlySizedEnumSizes] = {0};
  auto writer = ExplicitlySizedEnumSizesWriter(buffer, sizeof buffer);
  EXPECT_TRUE(::emboss::UpdateFromText(writer, R"(
    {
      one_byte: VALUE1
      two_byte: VALUE10
      three_byte: VALUE10000
      three_and_a_half_byte: VALUE100
    }
  )"));
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(
                kExplicitlySizedEnumSizes,
                kExplicitlySizedEnumSizes + sizeof kExplicitlySizedEnumSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(SizesView, DecodeExplicitlySizedEnumsFromIntegerText) {
  ::std::uint8_t buffer[sizeof kExplicitlySizedEnumSizes] = {0};
  auto writer = ExplicitlySizedEnumSizesWriter(buffer, sizeof buffer);
  EXPECT_TRUE(::emboss::UpdateFromText(writer, R"(
    {
      one_byte: 1
      two_byte: 10
      three_byte: 10000
      three_and_a_half_byte: 100
    }
  )"));
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(
                kExplicitlySizedEnumSizes,
                kExplicitlySizedEnumSizes + sizeof kExplicitlySizedEnumSizes),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

static const ::std::uint8_t kUIntArraySizes[72] = {
    0x02,                    // 0:2    one_byte[0] == 2
    0x03,                    // 0:2    one_byte[1] == 3
    0x04, 0x01,              // 2:6    two_byte[0] == 260
    0x05, 0x01,              // 2:6    two_byte[1] == 261
    0x66, 0x55, 0x44,        // 6:12   three_byte[0] == 0x445566
    0x67, 0x55, 0x44,        // 6:12   three_byte[1] == 0x445567
    0x06, 0x05, 0x04, 0x03,  // 12:20  four_byte[0] == 0x03040506
    0x07, 0x05, 0x04, 0x03,  // 12:20  four_byte[1] == 0x03040507
    0x21, 0x43, 0x65, 0x87,  // 20:30  five_byte[0]
    0xa9,                    // 20:30  five_byte[0] == 0xa987654321
    0x22, 0x43, 0x65, 0x87,  // 20:30  five_byte[1]
    0xa9,                    // 20:30  five_byte[1] == 0xa987654322
    0xbc, 0x9a, 0x78, 0x56,  // 30:42  six_byte[0]
    0x34, 0x12,              // 30:42  six_byte[0] == 0x123456789abc
    0xbd, 0x9a, 0x78, 0x56,  // 30:42  six_byte[1]
    0x34, 0x12,              // 30:42  six_byte[1] == 0x123456789abd
    0x97, 0xa6, 0xb5, 0xc4,  // 42:56  seven_byte[0]
    0xd3, 0xe2, 0xf1,        // 42:56  seven_byte[0] == 0xf1e2d3c4b5a697
    0x98, 0xa6, 0xb5, 0xc4,  // 42:56  seven_byte[1]
    0xd3, 0xe2, 0xf1,        // 42:56  seven_byte[1] == 0xf1e2d3c4b5a698
    0x06, 0x05, 0x04, 0x03,  // 56:72  eight_byte[0]
    0x02, 0x01, 0x00, 0xff,  // 56:72  eight_byte[0] == 0xff00010203040506
    0x07, 0x05, 0x04, 0x03,  // 56:72  eight_byte[1]
    0x02, 0x01, 0x00, 0xff,  // 56:72  eight_byte[1] == 0xff00010203040507
};

TEST(SizesView, CanReadArraySizes) {
  auto view = ArraySizesView(kUIntArraySizes, sizeof kUIntArraySizes);
  EXPECT_EQ(2, view.one_byte()[0].Read());
  EXPECT_EQ(3, view.one_byte()[1].Read());
  EXPECT_EQ(260, view.two_byte()[0].Read());
  EXPECT_EQ(261, view.two_byte()[1].Read());
  EXPECT_EQ(0x445566U, view.three_byte()[0].Read());
  EXPECT_EQ(0x445567U, view.three_byte()[1].Read());
  EXPECT_EQ(0x03040506U, view.four_byte()[0].Read());
  EXPECT_EQ(0x03040507U, view.four_byte()[1].Read());
  EXPECT_EQ(0xa987654321UL, view.five_byte()[0].Read());
  EXPECT_EQ(0xa987654322UL, view.five_byte()[1].Read());
  EXPECT_EQ(0x123456789abcUL, view.six_byte()[0].Read());
  EXPECT_EQ(0x123456789abdUL, view.six_byte()[1].Read());
  EXPECT_EQ(0xf1e2d3c4b5a697UL, view.seven_byte()[0].Read());
  EXPECT_EQ(0xf1e2d3c4b5a698UL, view.seven_byte()[1].Read());
  EXPECT_EQ(0xff00010203040506UL, view.eight_byte()[0].Read());
  EXPECT_EQ(0xff00010203040507UL, view.eight_byte()[1].Read());
  // Test that the views return appropriate integer widths.
  EXPECT_EQ(1U, sizeof(view.one_byte()[0].Read()));
  EXPECT_EQ(2U, sizeof(view.two_byte()[0].Read()));
  EXPECT_EQ(4U, sizeof(view.three_byte()[0].Read()));
  EXPECT_EQ(4U, sizeof(view.four_byte()[0].Read()));
  EXPECT_EQ(8U, sizeof(view.five_byte()[0].Read()));
  EXPECT_EQ(8U, sizeof(view.six_byte()[0].Read()));
  EXPECT_EQ(8U, sizeof(view.seven_byte()[0].Read()));
  EXPECT_EQ(8U, sizeof(view.eight_byte()[0].Read()));
}

TEST(SizesView, ToString) {
  ::std::array</**/ ::std::uint8_t, sizeof kUIntArraySizes> buf = {'a', 'b'};
  auto view = MakeArraySizesView(&buf);

  EXPECT_EQ(view.one_byte().ToString</**/ ::std::string>(), "ab");
}

TEST(SizesView, CopyFrom) {
  ::std::array</**/ ::std::uint8_t, sizeof kUIntArraySizes> buf_x = {};
  ::std::array</**/ ::std::uint8_t, sizeof kUIntArraySizes> buf_y = {};

  const auto x = SizesWriter(&buf_x);
  const auto y = SizesWriter(&buf_y);

  constexpr int kValue = 42;
  x.one_byte().Write(kValue);
  EXPECT_NE(x.one_byte().Read(), y.one_byte().Read());
  y.one_byte().CopyFrom(x.one_byte());
  EXPECT_EQ(x.one_byte().Read(), y.one_byte().Read());
}

TEST(SizesView, TryToCopyFrom) {
  ::std::array</**/ ::std::uint8_t, sizeof kUIntArraySizes> buf_x = {};
  ::std::array</**/ ::std::uint8_t, sizeof kUIntArraySizes> buf_y = {};

  const auto x = SizesWriter(&buf_x);
  const auto y = SizesWriter(&buf_y);

  constexpr int kValue = 42;
  x.one_byte().Write(kValue);
  EXPECT_NE(x.one_byte().Read(), y.one_byte().Read());
  EXPECT_TRUE(y.one_byte().TryToCopyFrom(x.one_byte()));
  EXPECT_EQ(x.one_byte().Read(), y.one_byte().Read());
}

}  // namespace
}  // namespace test
}  // namespace emboss
