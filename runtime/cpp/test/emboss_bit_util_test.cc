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
#if EMBOSS_HAS_INT128
  // Create 128-bit value 0x0f0e0d0c0b0a09080706050403020100
  __uint128_t val128 =
      (static_cast<__uint128_t>(0x0807060504030201UL) << 64) |
      static_cast<__uint128_t>(0x100f0e0d0c0b0a09UL);
  // Expected result after swap: 0x090a0b0c0d0e0f10_0102030405060708
  __uint128_t expected128 =
      (static_cast<__uint128_t>(0x090a0b0c0d0e0f10UL) << 64) |
      static_cast<__uint128_t>(0x0102030405060708UL);
  EXPECT_EQ(expected128, ByteSwap(val128));
#endif  // EMBOSS_HAS_INT128
}

TEST(MaskToNBits, MaskToNBits) {
  EXPECT_EQ(0xffU, MaskToNBits(0xffffffffU, 8));
  EXPECT_EQ(0x00U, MaskToNBits(0xffffff00U, 8));
  EXPECT_EQ(0x01U, MaskToNBits(0xffffffffU, 1));
  EXPECT_EQ(0x00U, MaskToNBits(0xfffffffeU, 1));
  EXPECT_EQ(0xffffffffU, MaskToNBits(0xffffffffU, 32));
  EXPECT_EQ(0xffffffffffffffffU, MaskToNBits(0xffffffffffffffffU, 64));
  EXPECT_EQ(0xfU, MaskToNBits(::std::uint8_t{0xff}, 4));
#if EMBOSS_HAS_INT128
  // Create a 128-bit value with all bits set
  __uint128_t all_ones_128 =
      (static_cast<__uint128_t>(0xffffffffffffffffUL) << 64) |
      static_cast<__uint128_t>(0xffffffffffffffffUL);
  // Mask to 72 bits
  __uint128_t expected_72 =
      (static_cast<__uint128_t>(0xffUL) << 64) |
      static_cast<__uint128_t>(0xffffffffffffffffUL);
  EXPECT_EQ(expected_72, MaskToNBits(all_ones_128, 72));
  // Mask to 128 bits should return the original value
  EXPECT_EQ(all_ones_128, MaskToNBits(all_ones_128, 128));
  // Mask to 64 bits should return just the lower 64 bits
  __uint128_t expected_64 = static_cast<__uint128_t>(0xffffffffffffffffUL);
  EXPECT_EQ(expected_64, MaskToNBits(all_ones_128, 64));
#endif  // EMBOSS_HAS_INT128
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
#if EMBOSS_HAS_INT128
  // Test powers of two for 128-bit values
  __uint128_t one_128 = 1;
  EXPECT_TRUE(IsPowerOfTwo(one_128));
  EXPECT_TRUE(IsPowerOfTwo(one_128 << 64));
  EXPECT_TRUE(IsPowerOfTwo(one_128 << 100));
  EXPECT_TRUE(IsPowerOfTwo(one_128 << 127));
  EXPECT_FALSE(IsPowerOfTwo(static_cast<__uint128_t>(0)));
  EXPECT_FALSE(IsPowerOfTwo(static_cast<__uint128_t>(3)));
  EXPECT_FALSE(IsPowerOfTwo((one_128 << 127) - 1));
  EXPECT_FALSE(IsPowerOfTwo((one_128 << 64) + 1));

  // Test signed 128-bit values
  __int128_t signed_one_128 = 1;
  EXPECT_TRUE(IsPowerOfTwo(signed_one_128));
  EXPECT_TRUE(IsPowerOfTwo(signed_one_128 << 64));
  EXPECT_TRUE(IsPowerOfTwo(signed_one_128 << 100));
  EXPECT_TRUE(IsPowerOfTwo(signed_one_128 << 126));  // Max positive power of 2
  EXPECT_FALSE(IsPowerOfTwo(static_cast<__int128_t>(0)));
  EXPECT_FALSE(IsPowerOfTwo(static_cast<__int128_t>(-1)));
  EXPECT_FALSE(IsPowerOfTwo(static_cast<__int128_t>(-2)));
  // Min int128 is negative, so should not be a power of two
  __int128_t min_int128 = static_cast<__int128_t>(1) << 127;
  EXPECT_FALSE(IsPowerOfTwo(min_int128));
#endif  // EMBOSS_HAS_INT128
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

#if EMBOSS_HAS_INT128
TEST(ByteSwap, ByteSwap128Comprehensive) {
  // Test identity: swapping twice should return the original value
  __uint128_t original =
      (static_cast<__uint128_t>(0x0102030405060708UL) << 64) |
      static_cast<__uint128_t>(0x090a0b0c0d0e0f10UL);
  EXPECT_EQ(original, ByteSwap(ByteSwap(original)));

  // Test with value where high and low 64-bit halves are different
  __uint128_t asymmetric =
      (static_cast<__uint128_t>(0xFFFFFFFFFFFFFFFFUL) << 64) |
      static_cast<__uint128_t>(0x0000000000000000UL);
  __uint128_t asymmetric_swapped =
      (static_cast<__uint128_t>(0x0000000000000000UL) << 64) |
      static_cast<__uint128_t>(0xFFFFFFFFFFFFFFFFUL);
  EXPECT_EQ(asymmetric_swapped, ByteSwap(asymmetric));

  // Test with single byte set at position 0
  __uint128_t byte0 = static_cast<__uint128_t>(0x42UL);
  __uint128_t byte0_swapped = static_cast<__uint128_t>(0x42UL) << 120;
  EXPECT_EQ(byte0_swapped, ByteSwap(byte0));

  // Test with single byte set at position 15 (highest byte)
  __uint128_t byte15 = static_cast<__uint128_t>(0x42UL) << 120;
  __uint128_t byte15_swapped = static_cast<__uint128_t>(0x42UL);
  EXPECT_EQ(byte15_swapped, ByteSwap(byte15));

  // Test with value where each byte is unique
  __uint128_t unique_bytes =
      (static_cast<__uint128_t>(0x0102030405060708UL) << 64) |
      static_cast<__uint128_t>(0x090a0b0c0d0e0f10UL);
  __uint128_t unique_bytes_swapped =
      (static_cast<__uint128_t>(0x100f0e0d0c0b0a09UL) << 64) |
      static_cast<__uint128_t>(0x0807060504030201UL);
  EXPECT_EQ(unique_bytes_swapped, ByteSwap(unique_bytes));
}

TEST(MaskToNBits, MaskToNBits128EdgeCases) {
  __uint128_t all_ones_128 =
      (static_cast<__uint128_t>(0xffffffffffffffffUL) << 64) |
      static_cast<__uint128_t>(0xffffffffffffffffUL);

  // Mask to 1 bit
  EXPECT_EQ(static_cast<__uint128_t>(1), MaskToNBits(all_ones_128, 1));

  // Mask to 65 bits (just over 64)
  __uint128_t expected_65 =
      (static_cast<__uint128_t>(0x1UL) << 64) |
      static_cast<__uint128_t>(0xffffffffffffffffUL);
  EXPECT_EQ(expected_65, MaskToNBits(all_ones_128, 65));

  // Mask to 127 bits
  __uint128_t expected_127 =
      (static_cast<__uint128_t>(0x7fffffffffffffffUL) << 64) |
      static_cast<__uint128_t>(0xffffffffffffffffUL);
  EXPECT_EQ(expected_127, MaskToNBits(all_ones_128, 127));

  // Mask value that already fits
  __uint128_t small_value = static_cast<__uint128_t>(0x1234UL);
  EXPECT_EQ(small_value, MaskToNBits(small_value, 128));
  EXPECT_EQ(small_value, MaskToNBits(small_value, 64));
  EXPECT_EQ(static_cast<__uint128_t>(0x234UL), MaskToNBits(small_value, 12));
}
#endif  // EMBOSS_HAS_INT128

}  // namespace test
}  // namespace support
}  // namespace emboss
