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

// Tests for generated code for "bits" types, using bits.emb.
#include <stdint.h>

#include <vector>

#include "gtest/gtest.h"
#include "runtime/cpp/emboss_cpp_util.h"
#include "testdata/bits.emb.h"

namespace emboss {
namespace test {
namespace {

TEST(Bits, OneByteView) {
  ::std::uint8_t data[] = {0x2b};
  auto one_byte = GenericOneByteView<support::BitBlock<
      support::LittleEndianByteOrderer<support::ReadWriteContiguousBuffer>, 8>>{
      support::BitBlock<
          support::LittleEndianByteOrderer<support::ReadWriteContiguousBuffer>,
          8>{support::ReadWriteContiguousBuffer{data, sizeof data}}};
  EXPECT_EQ(0xa, one_byte.mid_nibble().Read());
  EXPECT_EQ(0, one_byte.high_bit().Read());
  EXPECT_EQ(1, one_byte.low_bit().Read());
  one_byte.less_high_bit().Write(1);
  EXPECT_EQ(0x6b, data[0]);
  one_byte.less_low_bit().Write(0);
  EXPECT_EQ(0x69, data[0]);
  one_byte.mid_nibble().Write(5);
  EXPECT_EQ(0x55, data[0]);
}

TEST(Bits, StructOfBits) {
  alignas(8)::std::uint8_t data[] = {0xe8, 0x7f, 0xfe, 0xf1, 0xff, 0xbf, 0x3d};
  auto struct_of_bits =
      MakeAlignedStructOfBitsView</**/ ::std::uint8_t, 8>(data, sizeof data);
  EXPECT_EQ(0xa, struct_of_bits.one_byte().mid_nibble().Read());
  EXPECT_FALSE(struct_of_bits.Ok());
  EXPECT_FALSE(struct_of_bits.located_byte().Ok());
  struct_of_bits.one_byte().mid_nibble().Write(0x01);
  EXPECT_EQ(0xc4, data[0]);
  EXPECT_TRUE(struct_of_bits.Ok());
  EXPECT_TRUE(struct_of_bits.located_byte().Ok());
  EXPECT_EQ(0x7f, struct_of_bits.located_byte().Read());
  EXPECT_EQ(0x9, struct_of_bits.two_byte().mid_nibble().Read());
  EXPECT_EQ(0x6, struct_of_bits.four_byte().one_byte().mid_nibble().Read());
  EXPECT_EQ(0x3, struct_of_bits.four_byte().high_nibble().Read());
  struct_of_bits.four_byte().one_byte().mid_nibble().Write(0x9);
  EXPECT_EQ(0x7f, data[5]);
  EXPECT_EQ(0x3e, data[6]);
  EXPECT_EQ(101, struct_of_bits.four_byte().low_nibble().Read());
  struct_of_bits.four_byte().low_nibble().Write(115);
  EXPECT_EQ(0xff, data[3]);
  // Out-of-[range] write.
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(struct_of_bits.four_byte().low_nibble().Write(100), "");
#endif  // EMBOSS_CHECK_ABORTS
}

TEST(Bits, StructOfBitsFromText) {
  alignas(8)::std::uint8_t data[] = {0xe8, 0x7f, 0xfe, 0xf1, 0xff, 0xbf, 0x3d};
  auto struct_of_bits =
      MakeAlignedStructOfBitsView</**/ ::std::uint8_t, 8>(data, sizeof data);
  EXPECT_TRUE(::emboss::UpdateFromText(struct_of_bits, R"(
    {
      one_byte: {
        high_bit: false
        mid_nibble: 0x01
      }
      four_byte: {
        one_byte: {
          mid_nibble: 0x9
        }
        low_nibble: 115
      }
    }
  )"));
  EXPECT_EQ(0x44, data[0]);
  EXPECT_EQ(0x7f, data[5]);
  EXPECT_EQ(0x3e, data[6]);
  EXPECT_EQ(0xff, data[3]);
}

TEST(Bits, ArrayOfBits) {
  alignas(8)::std::uint8_t data[] = {0xe8, 0x7f, 0xfe, 0xf1,
                                     0xff, 0xbf, 0x00, 0x3d};
  auto bit_array =
      MakeAlignedBitArrayView</**/ ::std::uint8_t, 8>(data, sizeof data);
  EXPECT_EQ(0xa, bit_array.one_byte()[0].mid_nibble().Read());
  EXPECT_EQ(0xf, bit_array.one_byte()[7].mid_nibble().Read());
  bit_array.one_byte()[7].mid_nibble().Write(0x0);
  EXPECT_EQ(0x01, data[7]);
  EXPECT_TRUE(bit_array.Ok());
  bit_array =
      MakeAlignedBitArrayView</**/ ::std::uint8_t, 8>(data, sizeof data - 1);
  EXPECT_FALSE(bit_array.Ok());
}

TEST(Bits, ArrayInBits) {
  ::std::uint8_t data[] = {0xaa, 0xaa};
  auto array = ArrayInBitsInStructWriter{data, sizeof data};
  EXPECT_EQ(false, array.array_in_bits().flags()[0].Read());
  EXPECT_EQ(true, array.array_in_bits().flags()[1].Read());
  EXPECT_EQ(false, array.array_in_bits().flags()[10].Read());
  EXPECT_EQ(true, array.array_in_bits().flags()[11].Read());
  array.array_in_bits().flags()[8].Write(true);
  EXPECT_EQ(0xab, data[1]);
  EXPECT_EQ(12U, array.array_in_bits().flags().SizeInBits());
  EXPECT_EQ(12U, array.array_in_bits().flags().ElementCount());
  EXPECT_TRUE(array.array_in_bits().flags().Ok());
  EXPECT_TRUE(array.array_in_bits().flags().IsComplete());
}

TEST(Bits, ArrayInBitsFromText) {
  ::std::uint8_t data[] = {0, 0};
  auto array = ArrayInBitsInStructWriter{data, sizeof data};
  EXPECT_TRUE(::emboss::UpdateFromText(array.array_in_bits(), R"(
    {
      lone_flag: true
      flags: { true, false, true, false, true, false,
               true, false, true, false, true, false }
    }
  )"));
  EXPECT_EQ(0x55, data[0]);
  EXPECT_EQ(0x85, data[1]);
}

TEST(Bits, ArrayInBitsToText) {
  ::std::uint8_t data[] = {0x55, 0x85};
  auto array = ArrayInBitsInStructWriter{data, sizeof data};
  EXPECT_EQ(
      "{\n"
      "  lone_flag: true\n"
      "  flags: {\n"
      "    [0]: true\n"
      "    [1]: false\n"
      "    [2]: true\n"
      "    [3]: false\n"
      "    [4]: true\n"
      "    [5]: false\n"
      "    [6]: true\n"
      "    [7]: false\n"
      "    [8]: true\n"
      "    [9]: false\n"
      "    [10]: true\n"
      "    [11]: false\n"
      "  }\n"
      "}",
      ::emboss::WriteToString(array.array_in_bits(),
                              ::emboss::MultilineText()));
}

TEST(Bits, CopyFrom) {
  ::std::array</**/ ::std::uint8_t, 4> buf_x = {0x00, 0x00};
  ::std::array</**/ ::std::uint8_t, 4> buf_y = {0xff, 0xff};

  auto x = ArrayInBitsInStructWriter{&buf_x};
  auto y = ArrayInBitsInStructWriter{&buf_y};

  EXPECT_NE(x.array_in_bits().flags()[0].Read(),
            y.array_in_bits().flags()[0].Read());

  x.array_in_bits().flags()[0].CopyFrom(y.array_in_bits().flags()[0]);
  EXPECT_EQ(x.array_in_bits().flags()[0].Read(),
            y.array_in_bits().flags()[0].Read());

  EXPECT_NE(x.array_in_bits().flags()[1].Read(),
            y.array_in_bits().flags()[1].Read());
  EXPECT_NE(x.array_in_bits().flags()[10].Read(),
            y.array_in_bits().flags()[10].Read());
  EXPECT_NE(x.array_in_bits().flags()[11].Read(),
            y.array_in_bits().flags()[11].Read());
}

TEST(Bits, TryToCopyFrom) {
  ::std::array</**/ ::std::uint8_t, 4> buf_x = {0x00, 0x00};
  ::std::array</**/ ::std::uint8_t, 4> buf_y = {0xff, 0xff};

  auto x = ArrayInBitsInStructWriter{&buf_x};
  auto y = ArrayInBitsInStructWriter{&buf_y};

  EXPECT_NE(x.array_in_bits().flags()[0].Read(),
            y.array_in_bits().flags()[0].Read());

  EXPECT_TRUE(
      x.array_in_bits().flags()[0].TryToCopyFrom(y.array_in_bits().flags()[0]));
  EXPECT_EQ(x.array_in_bits().flags()[0].Read(),
            y.array_in_bits().flags()[0].Read());

  EXPECT_NE(x.array_in_bits().flags()[1].Read(),
            y.array_in_bits().flags()[1].Read());
  EXPECT_NE(x.array_in_bits().flags()[10].Read(),
            y.array_in_bits().flags()[10].Read());
  EXPECT_NE(x.array_in_bits().flags()[11].Read(),
            y.array_in_bits().flags()[11].Read());
}

TEST(Bits, Equals) {
  alignas(8)::std::uint8_t buf_x[] = {0xe8, 0x7f, 0xfe, 0xf1,
                                      0xff, 0xbf, 0x00, 0x3d};
  alignas(8)::std::uint8_t buf_y[] = {0xe8, 0x7f, 0xfe, 0xf1,
                                      0xff, 0xbf, 0x00, 0x3d};

  auto x = MakeAlignedBitArrayView</**/ ::std::uint8_t, 8>(buf_x, sizeof buf_x);
  auto x_const =
      MakeBitArrayView(static_cast</**/ ::std::uint8_t *>(buf_x), sizeof buf_x);
  auto y = MakeAlignedBitArrayView</**/ ::std::uint8_t, 8>(buf_y, sizeof buf_y);

  EXPECT_TRUE(x.Equals(x));
  EXPECT_TRUE(x.UncheckedEquals(x));
  EXPECT_TRUE(y.Equals(y));
  EXPECT_TRUE(y.UncheckedEquals(y));

  EXPECT_TRUE(x.Equals(y));
  EXPECT_TRUE(x.UncheckedEquals(y));
  EXPECT_TRUE(y.Equals(x));
  EXPECT_TRUE(y.UncheckedEquals(x));

  EXPECT_TRUE(x_const.Equals(y));
  EXPECT_TRUE(x_const.UncheckedEquals(y));
  EXPECT_TRUE(y.Equals(x_const));
  EXPECT_TRUE(y.UncheckedEquals(x_const));

  ++buf_y[1];
  EXPECT_FALSE(x.Equals(y));
  EXPECT_FALSE(x.UncheckedEquals(y));
  EXPECT_FALSE(y.Equals(x));
  EXPECT_FALSE(y.UncheckedEquals(x));

  EXPECT_FALSE(x_const.Equals(y));
  EXPECT_FALSE(x_const.UncheckedEquals(y));
  EXPECT_FALSE(y.Equals(x_const));
  EXPECT_FALSE(y.UncheckedEquals(x_const));
}

}  // namespace
}  // namespace test
}  // namespace emboss
