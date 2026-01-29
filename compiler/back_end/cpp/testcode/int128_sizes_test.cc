// Copyright 2024 Google LLC
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

// Tests for 128-bit integer support in generated Emboss code.
// This file tests structures defined in int128_sizes.emb with UInt and Int
// fields larger than 64 bits.

#include <stdint.h>

#include <cstring>
#include <vector>

#include "gtest/gtest.h"
#include "runtime/cpp/emboss_defines.h"

#if EMBOSS_HAS_INT128
#include "testdata/int128_sizes.emb.h"

namespace emboss {
namespace test {
namespace {

// Test data for UInt128Sizes (100 bytes total)
alignas(16) static const ::std::uint8_t kUInt128Sizes[100] = {
    // 0:9    nine_byte (72 bits) = 0x090807060504030201
    0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
    // 9:19   ten_byte (80 bits)
    0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x13,
    // 19:30  eleven_byte (88 bits)
    0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e,
    // 30:42  twelve_byte (96 bits)
    0x1f, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2a,
    // 42:55  thirteen_byte (104 bits)
    0x2b, 0x2c, 0x2d, 0x2e, 0x2f, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36,
    0x37,
    // 55:69  fourteen_byte (112 bits)
    0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f, 0x40, 0x41, 0x42, 0x43,
    0x44, 0x45,
    // 69:84  fifteen_byte (120 bits)
    0x46, 0x47, 0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x50, 0x51,
    0x52, 0x53, 0x54,
    // 84:100 sixteen_byte (128 bits)
    0x55, 0x56, 0x57, 0x58, 0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f, 0x60,
    0x61, 0x62, 0x63, 0x64,
};

TEST(UInt128SizesView, CanReadSizes) {
  auto view = MakeUInt128SizesView(kUInt128Sizes, sizeof kUInt128Sizes);
  EXPECT_TRUE(view.Ok());

  // Nine byte (72 bits) - little endian
  __uint128_t expected_nine =
      (static_cast<__uint128_t>(0x09UL) << 64) |
      static_cast<__uint128_t>(0x0807060504030201UL);
  EXPECT_EQ(expected_nine, view.nine_byte().Read());
  EXPECT_EQ(16U, sizeof(view.nine_byte().Read()));

  // Ten byte (80 bits)
  __uint128_t expected_ten =
      (static_cast<__uint128_t>(0x1312UL) << 64) |
      static_cast<__uint128_t>(0x11100f0e0d0c0b0aUL);
  EXPECT_EQ(expected_ten, view.ten_byte().Read());

  // Sixteen byte (128 bits)
  __uint128_t expected_sixteen =
      (static_cast<__uint128_t>(0x6463626160'5f5e5dUL) << 64) |
      static_cast<__uint128_t>(0x5c5b5a5958'575655UL);
  EXPECT_EQ(expected_sixteen, view.sixteen_byte().Read());
}

TEST(UInt128SizesWriter, CanWriteSizes) {
  ::std::uint8_t buffer[sizeof kUInt128Sizes] = {};
  auto writer = UInt128SizesWriter(buffer, sizeof buffer);

  // Write nine byte value
  __uint128_t nine_value =
      (static_cast<__uint128_t>(0xffUL) << 64) |
      static_cast<__uint128_t>(0xfedcba9876543210UL);
  writer.nine_byte().Write(nine_value);

  // Verify written bytes (little-endian)
  EXPECT_EQ(0x10, buffer[0]);
  EXPECT_EQ(0x32, buffer[1]);
  EXPECT_EQ(0x54, buffer[2]);
  EXPECT_EQ(0x76, buffer[3]);
  EXPECT_EQ(0x98, buffer[4]);
  EXPECT_EQ(0xba, buffer[5]);
  EXPECT_EQ(0xdc, buffer[6]);
  EXPECT_EQ(0xfe, buffer[7]);
  EXPECT_EQ(0xff, buffer[8]);

  // Read back and verify
  auto view = MakeUInt128SizesView(buffer, sizeof buffer);
  EXPECT_EQ(nine_value, view.nine_byte().Read());
}

TEST(UInt128SizesView, CanReadMaxValues) {
  ::std::uint8_t buffer[100];
  auto writer = UInt128SizesWriter(buffer, sizeof buffer);

  // Max 72-bit value
  __uint128_t max_72 = (static_cast<__uint128_t>(1) << 72) - 1;
  writer.nine_byte().Write(max_72);
  EXPECT_EQ(max_72,
            MakeUInt128SizesView(buffer, sizeof buffer).nine_byte().Read());

  // Max 128-bit value
  __uint128_t max_128 =
      (static_cast<__uint128_t>(0xffffffffffffffffUL) << 64) |
      static_cast<__uint128_t>(0xffffffffffffffffUL);
  writer.sixteen_byte().Write(max_128);
  EXPECT_EQ(max_128,
            MakeUInt128SizesView(buffer, sizeof buffer).sixteen_byte().Read());
}

// Int128 tests with negative values
alignas(16) static const ::std::uint8_t kInt128SizesNegativeOne[100] = {
    // All bytes are 0xff, representing -1 in two's complement for all sizes
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,  // nine_byte
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,  // ten_byte
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    0xff,  // eleven_byte
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    0xff,  // twelve_byte
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    0xff,  // thirteen_byte
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    0xff, 0xff,  // fourteen_byte
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    0xff, 0xff, 0xff,  // fifteen_byte
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    0xff, 0xff, 0xff, 0xff,  // sixteen_byte
};

TEST(Int128SizesView, CanReadNegativeOne) {
  auto view = MakeInt128SizesView(kInt128SizesNegativeOne,
                                  sizeof kInt128SizesNegativeOne);
  EXPECT_TRUE(view.Ok());

  EXPECT_EQ(static_cast<__int128_t>(-1), view.nine_byte().Read());
  EXPECT_EQ(static_cast<__int128_t>(-1), view.ten_byte().Read());
  EXPECT_EQ(static_cast<__int128_t>(-1), view.eleven_byte().Read());
  EXPECT_EQ(static_cast<__int128_t>(-1), view.twelve_byte().Read());
  EXPECT_EQ(static_cast<__int128_t>(-1), view.thirteen_byte().Read());
  EXPECT_EQ(static_cast<__int128_t>(-1), view.fourteen_byte().Read());
  EXPECT_EQ(static_cast<__int128_t>(-1), view.fifteen_byte().Read());
  EXPECT_EQ(static_cast<__int128_t>(-1), view.sixteen_byte().Read());
}

TEST(Int128SizesWriter, CanWriteNegativeOne) {
  ::std::uint8_t buffer[sizeof kInt128SizesNegativeOne];
  auto writer = Int128SizesWriter(buffer, sizeof buffer);

  writer.nine_byte().Write(static_cast<__int128_t>(-1));
  writer.ten_byte().Write(static_cast<__int128_t>(-1));
  writer.eleven_byte().Write(static_cast<__int128_t>(-1));
  writer.twelve_byte().Write(static_cast<__int128_t>(-1));
  writer.thirteen_byte().Write(static_cast<__int128_t>(-1));
  writer.fourteen_byte().Write(static_cast<__int128_t>(-1));
  writer.fifteen_byte().Write(static_cast<__int128_t>(-1));
  writer.sixteen_byte().Write(static_cast<__int128_t>(-1));

  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(
                kInt128SizesNegativeOne,
                kInt128SizesNegativeOne + sizeof kInt128SizesNegativeOne),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(Int128SizesView, CanReadMinMaxValues) {
  ::std::uint8_t buffer[100];
  auto writer = Int128SizesWriter(buffer, sizeof buffer);

  // Test 72-bit signed min/max
  __int128_t max_72 = (static_cast<__int128_t>(1) << 71) - 1;
  __int128_t min_72 = -(static_cast<__int128_t>(1) << 71);
  writer.nine_byte().Write(max_72);
  EXPECT_EQ(max_72,
            MakeInt128SizesView(buffer, sizeof buffer).nine_byte().Read());
  writer.nine_byte().Write(min_72);
  EXPECT_EQ(min_72,
            MakeInt128SizesView(buffer, sizeof buffer).nine_byte().Read());

  // Test 128-bit signed min/max
  __int128_t max_128 = static_cast<__int128_t>(
      (static_cast<__uint128_t>(0x7fffffffffffffffUL) << 64) |
      static_cast<__uint128_t>(0xffffffffffffffffUL));
  __int128_t min_128 = static_cast<__int128_t>(1) << 127;

  writer.sixteen_byte().Write(max_128);
  EXPECT_EQ(
      max_128,
      MakeInt128SizesView(buffer, sizeof buffer).sixteen_byte().Read());
  writer.sixteen_byte().Write(min_128);
  EXPECT_EQ(
      min_128,
      MakeInt128SizesView(buffer, sizeof buffer).sixteen_byte().Read());
}

// Test big-endian 128-bit structures
TEST(BigEndianUInt128SizesView, CanReadAndWrite) {
  ::std::uint8_t buffer[100] = {};
  auto writer = BigEndianUInt128SizesWriter(buffer, sizeof buffer);

  // Write a recognizable value to nine_byte (72 bits)
  __uint128_t nine_value =
      (static_cast<__uint128_t>(0x01UL) << 64) |
      static_cast<__uint128_t>(0x0203040506070809UL);
  writer.nine_byte().Write(nine_value);

  // The bytes should be in big-endian order
  EXPECT_EQ(0x01, buffer[0]);
  EXPECT_EQ(0x02, buffer[1]);
  EXPECT_EQ(0x09, buffer[8]);

  // Read back and verify
  auto view = MakeBigEndianUInt128SizesView(buffer, sizeof buffer);
  EXPECT_EQ(nine_value, view.nine_byte().Read());
}

TEST(BigEndianInt128SizesView, CanReadNegativeOne) {
  ::std::uint8_t buffer[100];
  ::std::memset(buffer, 0xff, sizeof buffer);

  auto view = MakeBigEndianInt128SizesView(buffer, sizeof buffer);
  EXPECT_EQ(static_cast<__int128_t>(-1), view.nine_byte().Read());
  EXPECT_EQ(static_cast<__int128_t>(-1), view.sixteen_byte().Read());
}

// Test arrays of 128-bit values
TEST(UInt128ArraySizesView, CanReadAndWriteArrays) {
  ::std::uint8_t buffer[200] = {};
  auto writer = UInt128ArraySizesWriter(buffer, sizeof buffer);

  // Write to first element of nine_byte array (72-bit elements)
  __uint128_t value_0 =
      (static_cast<__uint128_t>(0xffUL) << 64) |
      static_cast<__uint128_t>(0x0102030405060708UL);
  writer.nine_byte()[0].Write(value_0);

  __uint128_t value_1 =
      (static_cast<__uint128_t>(0xeeUL) << 64) |
      static_cast<__uint128_t>(0x1112131415161718UL);
  writer.nine_byte()[1].Write(value_1);

  auto view = MakeUInt128ArraySizesView(buffer, sizeof buffer);
  EXPECT_EQ(value_0, view.nine_byte()[0].Read());
  EXPECT_EQ(value_1, view.nine_byte()[1].Read());

  // Test sixteen_byte array (128-bit elements)
  __uint128_t sixteen_0 =
      (static_cast<__uint128_t>(0xfedcba9876543210UL) << 64) |
      static_cast<__uint128_t>(0x0123456789abcdefUL);
  __uint128_t sixteen_1 =
      (static_cast<__uint128_t>(0x0123456789abcdefUL) << 64) |
      static_cast<__uint128_t>(0xfedcba9876543210UL);
  writer.sixteen_byte()[0].Write(sixteen_0);
  writer.sixteen_byte()[1].Write(sixteen_1);

  EXPECT_EQ(sixteen_0, view.sixteen_byte()[0].Read());
  EXPECT_EQ(sixteen_1, view.sixteen_byte()[1].Read());
}

TEST(UInt128SizesView, CopyFrom) {
  ::std::uint8_t buf_x[sizeof kUInt128Sizes] = {};
  ::std::uint8_t buf_y[sizeof kUInt128Sizes] = {};

  auto x = UInt128SizesWriter(buf_x, sizeof buf_x);
  auto y = UInt128SizesWriter(buf_y, sizeof buf_y);

  __uint128_t value =
      (static_cast<__uint128_t>(0xfedcba9876543210UL) << 64) |
      static_cast<__uint128_t>(0x0123456789abcdefUL);
  x.sixteen_byte().Write(value);
  EXPECT_NE(x.sixteen_byte().Read(), y.sixteen_byte().Read());
  y.sixteen_byte().CopyFrom(x.sixteen_byte());
  EXPECT_EQ(x.sixteen_byte().Read(), y.sixteen_byte().Read());
}

TEST(Int128SizesView, CopyFrom) {
  ::std::uint8_t buf_x[sizeof kInt128SizesNegativeOne] = {};
  ::std::uint8_t buf_y[sizeof kInt128SizesNegativeOne] = {};

  auto x = Int128SizesWriter(buf_x, sizeof buf_x);
  auto y = Int128SizesWriter(buf_y, sizeof buf_y);

  // Use a value that fits in int64_t to avoid literal issues
  __int128_t large_negative = static_cast<__int128_t>(-1234567890123456789LL);
  x.sixteen_byte().Write(large_negative);
  EXPECT_NE(x.sixteen_byte().Read(), y.sixteen_byte().Read());
  y.sixteen_byte().CopyFrom(x.sixteen_byte());
  EXPECT_EQ(x.sixteen_byte().Read(), y.sixteen_byte().Read());
}

TEST(UInt128SizesView, TryToCopyFrom) {
  ::std::uint8_t buf_x[sizeof kUInt128Sizes] = {};
  ::std::uint8_t buf_y[sizeof kUInt128Sizes] = {};

  auto x = UInt128SizesWriter(buf_x, sizeof buf_x);
  auto y = UInt128SizesWriter(buf_y, sizeof buf_y);

  __uint128_t value =
      (static_cast<__uint128_t>(0xabcdef0123456789UL) << 64) |
      static_cast<__uint128_t>(0x9876543210fedcbaUL);
  x.sixteen_byte().Write(value);
  EXPECT_NE(x.sixteen_byte().Read(), y.sixteen_byte().Read());
  EXPECT_TRUE(y.sixteen_byte().TryToCopyFrom(x.sixteen_byte()));
  EXPECT_EQ(x.sixteen_byte().Read(), y.sixteen_byte().Read());
}

}  // namespace
}  // namespace test
}  // namespace emboss

#else  // !EMBOSS_HAS_INT128

// Provide a placeholder test when 128-bit integers are not available
namespace emboss {
namespace test {
namespace {

TEST(Int128Support, NotAvailable) {
  // This test exists just to indicate that 128-bit tests were skipped
  // because the platform doesn't support __int128_t/__uint128_t.
  GTEST_SKIP() << "128-bit integer support is not available on this platform";
}

}  // namespace
}  // namespace test
}  // namespace emboss

#endif  // EMBOSS_HAS_INT128
