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

#include "runtime/cpp/emboss_bit_util.h"

#include "gtest/gtest.h"

namespace emboss {
namespace support {
namespace test {

TEST(ByteSwap, ByteSwap) {
  EXPECT_EQ(0x01U, ByteSwap(::std::uint8_t{0x01}));
  EXPECT_EQ(0x0102U, ByteSwap(::std::uint16_t{0x0201}));
  EXPECT_EQ(0x01020304U, ByteSwap(::std::uint32_t{0x04030201}));
  EXPECT_EQ(0x0102030405060708UL,
            ByteSwap(::std::uint64_t{0x0807060504030201UL}));
}

TEST(MaskToNBits, MaskToNBits) {
  EXPECT_EQ(0xffU, MaskToNBits(0xffffffffU, 8));
  EXPECT_EQ(0x00U, MaskToNBits(0xffffff00U, 8));
  EXPECT_EQ(0x01U, MaskToNBits(0xffffffffU, 1));
  EXPECT_EQ(0x00U, MaskToNBits(0xfffffffeU, 1));
  EXPECT_EQ(0xffffffffU, MaskToNBits(0xffffffffU, 32));
  EXPECT_EQ(0xffffffffffffffffU, MaskToNBits(0xffffffffffffffffU, 64));
  EXPECT_EQ(0xfU, MaskToNBits(::std::uint8_t{0xff}, 4));
}

TEST(IsPowerOfTwo, IsPowerOfTwo) {
  EXPECT_TRUE(IsPowerOfTwo(1U));
  EXPECT_TRUE(IsPowerOfTwo(2U));
  EXPECT_TRUE(IsPowerOfTwo(1UL << 63));
  EXPECT_TRUE(IsPowerOfTwo(::std::uint8_t{128}));
  EXPECT_TRUE(IsPowerOfTwo(1));
  EXPECT_TRUE(IsPowerOfTwo(2));
  EXPECT_TRUE(IsPowerOfTwo(1L << 62));
  EXPECT_TRUE(IsPowerOfTwo(::std::int8_t{64}));

  EXPECT_FALSE(IsPowerOfTwo(0U));
  EXPECT_FALSE(IsPowerOfTwo(3U));
  EXPECT_FALSE(IsPowerOfTwo((1UL << 63) - 1));
  EXPECT_FALSE(IsPowerOfTwo((1UL << 62) + 1));
  EXPECT_FALSE(IsPowerOfTwo((3UL << 62)));
  EXPECT_FALSE(
      IsPowerOfTwo(::std::numeric_limits</**/ ::std::uint64_t>::max()));
  EXPECT_FALSE(IsPowerOfTwo(::std::uint8_t{129}));
  EXPECT_FALSE(IsPowerOfTwo(::std::uint8_t{255}));
  EXPECT_FALSE(IsPowerOfTwo(-1));
  EXPECT_FALSE(IsPowerOfTwo(-2));
  EXPECT_FALSE(IsPowerOfTwo(-3));
  EXPECT_FALSE(IsPowerOfTwo(::std::numeric_limits</**/ ::std::int64_t>::min()));
  EXPECT_FALSE(IsPowerOfTwo(::std::numeric_limits</**/ ::std::int64_t>::max()));
  EXPECT_FALSE(IsPowerOfTwo(0));
  EXPECT_FALSE(IsPowerOfTwo(3));
  EXPECT_FALSE(IsPowerOfTwo((1L << 62) - 1));
  EXPECT_FALSE(IsPowerOfTwo((1L << 61) + 1));
  EXPECT_FALSE(IsPowerOfTwo((3L << 61)));
  EXPECT_FALSE(IsPowerOfTwo(::std::int8_t{-1}));
  EXPECT_FALSE(IsPowerOfTwo(::std::int8_t{-128}));
  EXPECT_FALSE(IsPowerOfTwo(::std::int8_t{65}));
  EXPECT_FALSE(IsPowerOfTwo(::std::int8_t{127}));
}

#if defined(EMBOSS_LITTLE_ENDIAN_TO_NATIVE)
TEST(EndianConversion, LittleEndianToNative) {
  ::std::uint16_t data16 = 0;
  reinterpret_cast<char *>(&data16)[0] = 0x01;
  reinterpret_cast<char *>(&data16)[1] = 0x02;
  EXPECT_EQ(0x0201, EMBOSS_LITTLE_ENDIAN_TO_NATIVE(data16));

  ::std::uint32_t data32 = 0;
  reinterpret_cast<char *>(&data32)[0] = 0x01;
  reinterpret_cast<char *>(&data32)[1] = 0x02;
  reinterpret_cast<char *>(&data32)[2] = 0x03;
  reinterpret_cast<char *>(&data32)[3] = 0x04;
  EXPECT_EQ(0x04030201U, EMBOSS_LITTLE_ENDIAN_TO_NATIVE(data32));

  ::std::uint64_t data64 = 0;
  reinterpret_cast<char *>(&data64)[0] = 0x01;
  reinterpret_cast<char *>(&data64)[1] = 0x02;
  reinterpret_cast<char *>(&data64)[2] = 0x03;
  reinterpret_cast<char *>(&data64)[3] = 0x04;
  reinterpret_cast<char *>(&data64)[4] = 0x05;
  reinterpret_cast<char *>(&data64)[5] = 0x06;
  reinterpret_cast<char *>(&data64)[6] = 0x07;
  reinterpret_cast<char *>(&data64)[7] = 0x08;
  EXPECT_EQ(0x0807060504030201UL, EMBOSS_LITTLE_ENDIAN_TO_NATIVE(data64));
}
#endif  // defined(EMBOSS_LITTLE_ENDIAN_TO_NATIVE)

#if defined(EMBOSS_BIG_ENDIAN_TO_NATIVE)
TEST(EndianConversion, BigEndianToNative) {
  ::std::uint16_t data16 = 0;
  reinterpret_cast<char *>(&data16)[0] = 0x01;
  reinterpret_cast<char *>(&data16)[1] = 0x02;
  EXPECT_EQ(0x0102, EMBOSS_BIG_ENDIAN_TO_NATIVE(data16));

  ::std::uint32_t data32 = 0;
  reinterpret_cast<char *>(&data32)[0] = 0x01;
  reinterpret_cast<char *>(&data32)[1] = 0x02;
  reinterpret_cast<char *>(&data32)[2] = 0x03;
  reinterpret_cast<char *>(&data32)[3] = 0x04;
  EXPECT_EQ(0x01020304U, EMBOSS_BIG_ENDIAN_TO_NATIVE(data32));

  ::std::uint64_t data64 = 0;
  reinterpret_cast<char *>(&data64)[0] = 0x01;
  reinterpret_cast<char *>(&data64)[1] = 0x02;
  reinterpret_cast<char *>(&data64)[2] = 0x03;
  reinterpret_cast<char *>(&data64)[3] = 0x04;
  reinterpret_cast<char *>(&data64)[4] = 0x05;
  reinterpret_cast<char *>(&data64)[5] = 0x06;
  reinterpret_cast<char *>(&data64)[6] = 0x07;
  reinterpret_cast<char *>(&data64)[7] = 0x08;
  EXPECT_EQ(0x0102030405060708UL, EMBOSS_BIG_ENDIAN_TO_NATIVE(data64));
}
#endif  // defined(EMBOSS_BIG_ENDIAN_TO_NATIVE)

#if defined(EMBOSS_NATIVE_TO_LITTLE_ENDIAN)
TEST(EndianConversion, NativeToLittleEndian) {
  ::std::uint16_t data16 =
      EMBOSS_NATIVE_TO_LITTLE_ENDIAN(static_cast</**/ ::std::uint16_t>(0x0201));
  EXPECT_EQ(0x01, reinterpret_cast<char *>(&data16)[0]);
  EXPECT_EQ(0x02, reinterpret_cast<char *>(&data16)[1]);

  ::std::uint32_t data32 = EMBOSS_NATIVE_TO_LITTLE_ENDIAN(
      static_cast</**/ ::std::uint32_t>(0x04030201));
  EXPECT_EQ(0x01, reinterpret_cast<char *>(&data32)[0]);
  EXPECT_EQ(0x02, reinterpret_cast<char *>(&data32)[1]);
  EXPECT_EQ(0x03, reinterpret_cast<char *>(&data32)[2]);
  EXPECT_EQ(0x04, reinterpret_cast<char *>(&data32)[3]);

  ::std::uint64_t data64 = EMBOSS_NATIVE_TO_LITTLE_ENDIAN(
      static_cast</**/ ::std::uint64_t>(0x0807060504030201));
  EXPECT_EQ(0x01, reinterpret_cast<char *>(&data64)[0]);
  EXPECT_EQ(0x02, reinterpret_cast<char *>(&data64)[1]);
  EXPECT_EQ(0x03, reinterpret_cast<char *>(&data64)[2]);
  EXPECT_EQ(0x04, reinterpret_cast<char *>(&data64)[3]);
  EXPECT_EQ(0x05, reinterpret_cast<char *>(&data64)[4]);
  EXPECT_EQ(0x06, reinterpret_cast<char *>(&data64)[5]);
  EXPECT_EQ(0x07, reinterpret_cast<char *>(&data64)[6]);
  EXPECT_EQ(0x08, reinterpret_cast<char *>(&data64)[7]);
}
#endif  // defined(EMBOSS_NATIVE_TO_LITTLE_ENDIAN)

#if defined(EMBOSS_NATIVE_TO_BIG_ENDIAN)
TEST(EndianConversion, NativeToBigEndian) {
  ::std::uint16_t data16 =
      EMBOSS_NATIVE_TO_BIG_ENDIAN(static_cast</**/ ::std::uint16_t>(0x0102));
  EXPECT_EQ(0x01, reinterpret_cast<char *>(&data16)[0]);
  EXPECT_EQ(0x02, reinterpret_cast<char *>(&data16)[1]);

  ::std::uint32_t data32 = EMBOSS_NATIVE_TO_BIG_ENDIAN(
      static_cast</**/ ::std::uint32_t>(0x01020304));
  EXPECT_EQ(0x01, reinterpret_cast<char *>(&data32)[0]);
  EXPECT_EQ(0x02, reinterpret_cast<char *>(&data32)[1]);
  EXPECT_EQ(0x03, reinterpret_cast<char *>(&data32)[2]);
  EXPECT_EQ(0x04, reinterpret_cast<char *>(&data32)[3]);

  ::std::uint64_t data64 = EMBOSS_NATIVE_TO_BIG_ENDIAN(
      static_cast</**/ ::std::uint64_t>(0x0102030405060708));
  EXPECT_EQ(0x01, reinterpret_cast<char *>(&data64)[0]);
  EXPECT_EQ(0x02, reinterpret_cast<char *>(&data64)[1]);
  EXPECT_EQ(0x03, reinterpret_cast<char *>(&data64)[2]);
  EXPECT_EQ(0x04, reinterpret_cast<char *>(&data64)[3]);
  EXPECT_EQ(0x05, reinterpret_cast<char *>(&data64)[4]);
  EXPECT_EQ(0x06, reinterpret_cast<char *>(&data64)[5]);
  EXPECT_EQ(0x07, reinterpret_cast<char *>(&data64)[6]);
  EXPECT_EQ(0x08, reinterpret_cast<char *>(&data64)[7]);
}
#endif  // defined(EMBOSS_NATIVE_TO_BIG_ENDIAN)

}  // namespace test
}  // namespace support
}  // namespace emboss
