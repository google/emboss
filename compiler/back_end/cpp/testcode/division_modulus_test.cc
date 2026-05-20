// Copyright 2026 Google LLC
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

// Tests for `//` (flooring integer division) and `%` (flooring modulus)
// operators in generated C++ code.
#include <array>
#include <cstdint>

#include "gtest/gtest.h"
#include "testdata/division_modulus.emb.h"

namespace emboss {
namespace test {
namespace {

// Constant-folded virtual fields match the design doc's sign table.
TEST(Constants, ConstantFoldedQuotients) {
  EXPECT_EQ(20, Constants::exact_quotient());
  EXPECT_EQ(14, Constants::truncating_quotient());
  // (-7) // 2 == -4 (flooring), not -3 (truncating).
  EXPECT_EQ(-4, Constants::negative_quotient());
}

TEST(Constants, ConstantFoldedRemainders) {
  EXPECT_EQ(0, Constants::exact_modulus());
  EXPECT_EQ(2, Constants::truncating_modulus());
  // (-7) % 2 == 1 (flooring: result has sign of divisor).
  EXPECT_EQ(1, Constants::negative_modulus());
}

TEST(Constants, Chained) {
  EXPECT_EQ(10, Constants::chained_div());  // 100 // 5 // 2 == 20 // 2 == 10
  EXPECT_EQ(3, Constants::chained_mod());   // 17 % 7 % 4 == 3 % 4 == 3
  EXPECT_EQ(1, Constants::mixed_divmod());  // 17 % 7 // 2 == 3 // 2 == 1
}

// A field whose size depends on `//`.
TEST(ArrayOfUint16BySizeInBytes, SizeFromBytesDividedByTwo) {
  static constexpr ::std::array</**/ ::std::uint8_t, 7> kBuf = {{
      0x06,                    // size_in_bytes = 6 -> (6 // 2) * 2 = 6 bytes
      0x01, 0x00,              // elements[0] = 1
      0x02, 0x00,              // elements[1] = 2
      0x03, 0x00,              // elements[2] = 3
  }};
  auto view = MakeArrayOfUint16BySizeInBytesView(&kBuf);
  ASSERT_TRUE(view.Ok());
  EXPECT_EQ(7U, view.SizeInBytes());
  EXPECT_EQ(3U, view.elements().ElementCount());
  EXPECT_EQ(1U, view.elements()[0].Read());
  EXPECT_EQ(2U, view.elements()[1].Read());
  EXPECT_EQ(3U, view.elements()[2].Read());
}

// Odd size_in_bytes: the trailing odd byte is excluded because (n // 2) * 2
// rounds down to a multiple of 2.
TEST(ArrayOfUint16BySizeInBytes, OddSizeRoundsDown) {
  static constexpr ::std::array</**/ ::std::uint8_t, 5> kBuf = {{
      0x05,                    // size_in_bytes = 5 -> (5 // 2) * 2 = 4 bytes
      0x01, 0x00,              // elements[0] = 1
      0x02, 0x00,              // elements[1] = 2
  }};
  auto view = MakeArrayOfUint16BySizeInBytesView(&kBuf);
  ASSERT_TRUE(view.Ok());
  EXPECT_EQ(5U, view.SizeInBytes());
  EXPECT_EQ(2U, view.elements().ElementCount());
}

// ChunkedPayload exercises `(n + 3) // 4 * 4` (round up to multiple of 4).
TEST(ChunkedPayload, RoundsUpToMultipleOfFour) {
  static constexpr ::std::array</**/ ::std::uint8_t, 9> kBuf = {{
      0x05,                                // chunk_count = 5
      0x11, 0x22, 0x33, 0x44, 0x55,        // 5 used bytes
      0x00, 0x00, 0x00,                    // 3 padding bytes -> total 8 used
  }};
  auto view = MakeChunkedPayloadView(&kBuf);
  ASSERT_TRUE(view.Ok());
  // ((5 + 3) // 4) * 4 == 8 bytes of payload, plus the 1-byte count = 9 total.
  EXPECT_EQ(9U, view.SizeInBytes());
  EXPECT_EQ(8U, view.padded().ElementCount());
}

}  // namespace
}  // namespace test
}  // namespace emboss
