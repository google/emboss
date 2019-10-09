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

// Tests for the generated View class from bcd.emb.
//
// These tests check that Binary-Coded Decimal (BCD) numbers work.
#include <stdint.h>

#include <array>
#include <string>
#include <vector>

#include "gtest/gtest.h"
#include "testdata/bcd.emb.h"

namespace emboss {
namespace test {
namespace {

alignas(8) static const ::std::uint8_t kBcd[40] = {
    0x02,                    // 0  [+1]  one_byte == 2
    0x04, 0x01,              // 1  [+2]  two_byte == 104
    0x66, 0x55, 0x44,        // 3  [+3]  three_byte == 445566
    0x06, 0x05, 0x04, 0x03,  // 6  [+4]  four_byte == 3040506
    0x21, 0x43, 0x65, 0x87,  // 10 [+5]  five_byte
    0x99,                    // 10 [+5]  five_byte == 9987654321
    0x23, 0x91, 0x78, 0x56,  // 15 [+6]  six_byte
    0x34, 0x12,              // 15 [+6]  six_byte == 123456789123
    0x37, 0x46, 0x55, 0x64,  // 21 [+7]  seven_byte
    0x73, 0x82, 0x91,        // 21 [+7]  seven_byte == 91827364554637
    0x06, 0x05, 0x04, 0x03,  // 28 [+8]  eight_byte
    0x02, 0x01, 0x00, 0x99,  // 28 [+8]  eight_byte == 9900010203040506
    0x34, 0x1d, 0x3c, 0x12,  // 36 [+4]  four_bit = 4,
                             //          six_bit = 13,
                             //          ten_bit = 307,
                             //          twelve_bit = 123,
};

TEST(BcdSizesView, CanReadBcd) {
  auto view =
      MakeAlignedBcdSizesView<const ::std::uint8_t, 8>(kBcd, sizeof kBcd);
  EXPECT_EQ(2, view.one_byte().Read());
  EXPECT_EQ(104, view.two_byte().Read());
  EXPECT_EQ(445566U, view.three_byte().Read());
  EXPECT_EQ(3040506U, view.four_byte().Read());
  EXPECT_EQ(9987654321UL, view.five_byte().Read());
  EXPECT_EQ(123456789123UL, view.six_byte().Read());
  EXPECT_EQ(91827364554637UL, view.seven_byte().Read());
  EXPECT_EQ(9900010203040506UL, view.eight_byte().Read());
  EXPECT_EQ(4, view.four_bit().Read());
  EXPECT_EQ(13, view.six_bit().Read());
  EXPECT_EQ(307, view.ten_bit().Read());
  EXPECT_EQ(123, view.twelve_bit().Read());
  // Test that the views return appropriate integer widths.
  EXPECT_EQ(1U, sizeof(view.one_byte().Read()));
  EXPECT_EQ(2U, sizeof(view.two_byte().Read()));
  EXPECT_EQ(4U, sizeof(view.three_byte().Read()));
  EXPECT_EQ(4U, sizeof(view.four_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.five_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.six_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.seven_byte().Read()));
  EXPECT_EQ(8U, sizeof(view.eight_byte().Read()));
  EXPECT_EQ(1U, sizeof(view.four_bit().Read()));
  EXPECT_EQ(1U, sizeof(view.six_bit().Read()));
  EXPECT_EQ(2U, sizeof(view.ten_bit().Read()));
  EXPECT_EQ(2U, sizeof(view.twelve_bit().Read()));
}

TEST(BcdSizesWriter, CanWriteBcd) {
  ::std::uint8_t buffer[sizeof kBcd] = {0};
  auto writer = BcdSizesWriter(buffer, sizeof buffer);
  writer.one_byte().Write(2);
  writer.two_byte().Write(104);
  writer.three_byte().Write(445566);
  writer.four_byte().Write(3040506);
  writer.five_byte().Write(9987654321UL);
  writer.six_byte().Write(123456789123UL);
  writer.seven_byte().Write(91827364554637UL);
  writer.eight_byte().Write(9900010203040506UL);
  writer.four_bit().Write(4);
  writer.six_bit().Write(13);
  writer.ten_bit().Write(307);
  writer.twelve_bit().Write(123);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kBcd, kBcd + sizeof kBcd),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));

#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(writer.one_byte().Write(100), "");
  EXPECT_DEATH(writer.three_byte().Write(1445566), "");
  EXPECT_DEATH(writer.ten_bit().Write(400), "");
#endif  // EMBOSS_CHECK_ABORTS
}

TEST(BcdSizesView, OkIsTrueForGoodBcd) {
  auto view = BcdSizesView(kBcd, sizeof kBcd);
  EXPECT_TRUE(view.Ok());
  EXPECT_TRUE(view.one_byte().Ok());
  EXPECT_TRUE(view.one_byte().Ok());
  EXPECT_TRUE(view.two_byte().Ok());
  EXPECT_TRUE(view.three_byte().Ok());
  EXPECT_TRUE(view.four_byte().Ok());
  EXPECT_TRUE(view.five_byte().Ok());
  EXPECT_TRUE(view.six_byte().Ok());
  EXPECT_TRUE(view.seven_byte().Ok());
  EXPECT_TRUE(view.eight_byte().Ok());
}

static const ::std::uint8_t kBadBcd[40] = {
    0x0a,                    // 0  [+1]  one_byte
    0xb4, 0x01,              // 1  [+2]  two_byte
    0xaa, 0x55, 0x44,        // 3  [+3]  three_byte
    0x06, 0x05, 0x04, 0xff,  // 6  [+4]  four_byte
    0xff, 0xff, 0xff, 0xff,  // 10 [+5]  five_byte
    0xff,                    // 10 [+5]  five_byte
    0xff, 0xff, 0xff, 0xff,  // 15 [+6]  six_byte
    0xff, 0xff,              // 15 [+6]  six_byte
    0xff, 0xff, 0xff, 0xff,  // 21 [+7]  seven_byte
    0xff, 0xff, 0xff,        // 21 [+7]  seven_byte
    0xff, 0xff, 0xff, 0xff,  // 28 [+8]  eight_byte
    0xff, 0xff, 0xff, 0xff,  // 28 [+8]  eight_byte
    0xff, 0xff, 0xff, 0xff,  // 36 [+4]  four_, six_, ten_, twelve_bit
};

TEST(BcdSizesView, UncheckedReadingInvalidBcdDoesNotCrash) {
  auto view = BcdSizesView(kBadBcd, sizeof kBadBcd);
  view.one_byte().UncheckedRead();
  view.two_byte().UncheckedRead();
  view.three_byte().UncheckedRead();
  view.four_byte().UncheckedRead();
  view.five_byte().UncheckedRead();
  view.six_byte().UncheckedRead();
  view.seven_byte().UncheckedRead();
  view.eight_byte().UncheckedRead();
  view.four_bit().UncheckedRead();
  view.six_bit().UncheckedRead();
  view.ten_bit().UncheckedRead();
  view.twelve_bit().UncheckedRead();
}

#if EMBOSS_CHECK_ABORTS
TEST(BcdSizesView, ReadingInvalidBcdCrashes) {
  auto view = BcdSizesView(kBadBcd, sizeof kBadBcd);
  EXPECT_DEATH(view.one_byte().Read(), "");
  EXPECT_DEATH(view.two_byte().Read(), "");
  EXPECT_DEATH(view.three_byte().Read(), "");
  EXPECT_DEATH(view.four_byte().Read(), "");
  EXPECT_DEATH(view.five_byte().Read(), "");
  EXPECT_DEATH(view.six_byte().Read(), "");
  EXPECT_DEATH(view.seven_byte().Read(), "");
  EXPECT_DEATH(view.eight_byte().Read(), "");
  EXPECT_DEATH(view.four_bit().Read(), "");
  EXPECT_DEATH(view.six_bit().Read(), "");
  EXPECT_DEATH(view.ten_bit().Read(), "");
  EXPECT_DEATH(view.twelve_bit().Read(), "");
}
#endif  // EMBOSS_CHECK_ABORTS

TEST(BcdSizesView, OkIsFalseForBadBcd) {
  auto view = BcdSizesView(kBadBcd, sizeof kBadBcd);
  EXPECT_FALSE(view.Ok());
  EXPECT_FALSE(view.one_byte().Ok());
  EXPECT_FALSE(view.two_byte().Ok());
  EXPECT_FALSE(view.three_byte().Ok());
  EXPECT_FALSE(view.four_byte().Ok());
  EXPECT_FALSE(view.five_byte().Ok());
  EXPECT_FALSE(view.six_byte().Ok());
  EXPECT_FALSE(view.seven_byte().Ok());
  EXPECT_FALSE(view.eight_byte().Ok());
  EXPECT_FALSE(view.four_bit().Ok());
  EXPECT_FALSE(view.six_bit().Ok());
  EXPECT_FALSE(view.ten_bit().Ok());
  EXPECT_FALSE(view.twelve_bit().Ok());
}

TEST(BcdBigEndianView, BigEndianReadWrite) {
  ::std::uint8_t big_endian[4] = {0x12, 0x34, 0x56, 0x78};
  auto writer = BcdBigEndianWriter(big_endian, sizeof big_endian);
  EXPECT_EQ(12345678U, writer.four_byte().Read());
  writer.four_byte().Write(87654321);
  EXPECT_EQ(0x87, big_endian[0]);
  EXPECT_EQ(0x65, big_endian[1]);
  EXPECT_EQ(0x43, big_endian[2]);
  EXPECT_EQ(0x21, big_endian[3]);
}

TEST(BcdBigEndianView, CopyFrom) {
  ::std::array</**/ ::std::uint8_t, 4> buf_x = {0x12, 0x34, 0x56, 0x78};
  ::std::array</**/ ::std::uint8_t, 4> buf_y = {0x00, 0x00, 0x00, 0x00};

  auto x = BcdBigEndianWriter(&buf_x);
  auto y = BcdBigEndianWriter(&buf_y);

  EXPECT_NE(x.four_byte().Read(), y.four_byte().Read());
  x.four_byte().CopyFrom(y.four_byte());
  EXPECT_EQ(x.four_byte().Read(), y.four_byte().Read());
}

TEST(BcdBigEndianView, TryToCopyFrom) {
  ::std::array</**/ ::std::uint8_t, 4> buf_x = {0x12, 0x34, 0x56, 0x78};
  ::std::array</**/ ::std::uint8_t, 4> buf_y = {0x00, 0x00, 0x00, 0x00};

  auto x = BcdBigEndianWriter(&buf_x);
  auto y = BcdBigEndianWriter(&buf_y);

  EXPECT_NE(x.four_byte().Read(), y.four_byte().Read());
  EXPECT_TRUE(x.four_byte().TryToCopyFrom(y.four_byte()));
  EXPECT_EQ(x.four_byte().Read(), y.four_byte().Read());
}

TEST(BcdSizesView, Equals) {
  ::std::array</**/ ::std::uint8_t, sizeof kBcd> buf_x;
  ::std::array</**/ ::std::uint8_t, sizeof kBcd> buf_y;

  ::std::copy(kBcd, kBcd + sizeof kBcd, buf_x.begin());
  ::std::copy(kBcd, kBcd + sizeof kBcd, buf_y.begin());

  EXPECT_EQ(buf_x, buf_y);
  auto x = BcdSizesView(&buf_x);
  auto x_const = BcdSizesView(
      static_cast</**/ ::std::array</**/ ::std::uint8_t, sizeof kBcd>*>(
          &buf_x));
  auto y = BcdSizesView(&buf_y);

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

TEST(BcdSizesView, UncheckedEquals) {
  ::std::array</**/ ::std::uint8_t, sizeof kBadBcd> buf_x;
  ::std::array</**/ ::std::uint8_t, sizeof kBadBcd> buf_y;

  ::std::copy(kBadBcd, kBadBcd + sizeof kBadBcd, buf_x.begin());
  ::std::copy(kBadBcd, kBadBcd + sizeof kBadBcd, buf_y.begin());

  EXPECT_EQ(buf_x, buf_y);
  auto x = BcdSizesView(&buf_x);
  auto x_const = BcdSizesView(
      static_cast</**/ ::std::array</**/ ::std::uint8_t, sizeof kBadBcd>*>(
          &buf_x));
  auto y = BcdSizesView(&buf_y);

  EXPECT_TRUE(x.UncheckedEquals(x));
  EXPECT_TRUE(y.UncheckedEquals(y));
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(x.Equals(x), "");
  EXPECT_DEATH(y.Equals(y), "");
#endif  // EMBOSS_CHECK_ABORTS

  EXPECT_TRUE(x.UncheckedEquals(y));
  EXPECT_TRUE(y.UncheckedEquals(x));
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(x.Equals(y), "");
  EXPECT_DEATH(y.Equals(x), "");
#endif  // EMBOSS_CHECK_ABORTS

  EXPECT_TRUE(x_const.UncheckedEquals(y));
  EXPECT_TRUE(y.UncheckedEquals(x_const));
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(x_const.Equals(y), "");
  EXPECT_DEATH(y.Equals(x_const), "");
#endif  // EMBOSS_CHECK_ABORTS

  ++buf_y[1];
  EXPECT_FALSE(x.UncheckedEquals(y));
  EXPECT_FALSE(y.UncheckedEquals(x));
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(x.Equals(y), "");
  EXPECT_DEATH(y.Equals(x), "");
#endif  // EMBOSS_CHECK_ABORTS

  EXPECT_FALSE(x_const.UncheckedEquals(y));
  EXPECT_FALSE(y.UncheckedEquals(x_const));
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(x_const.Equals(y), "");
  EXPECT_DEATH(y.Equals(x_const), "");
#endif  // EMBOSS_CHECK_ABORTS
}

}  // namespace
}  // namespace test
}  // namespace emboss
