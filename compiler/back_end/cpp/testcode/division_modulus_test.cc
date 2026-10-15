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

// Tests for the `//` (flooring integer division) and `%` (flooring modulus)
// operators in generated C++ code.
#include <array>
#include <cstdint>
#include <limits>

#include "gtest/gtest.h"
#include "testdata/division_modulus.emb.h"

namespace emboss {
namespace test {
namespace {

// Constant-folded virtual fields match the design doc's sign table.
TEST(Constants, ConstantFoldedQuotients) {
  EXPECT_EQ(20, Constants::exact_quotient());
  EXPECT_EQ(14, Constants::truncating_quotient());  // 100 // 7
  // (-7) // 2 == -4 (flooring), not -3 (truncating).
  EXPECT_EQ(-4, Constants::negative_quotient());
}

TEST(Constants, ConstantFoldedRemainders) {
  EXPECT_EQ(0, Constants::exact_modulus());
  EXPECT_EQ(2, Constants::truncating_modulus());  // 100 % 7
  // (-7) % 2 == 1 (flooring: result takes the sign of the divisor).
  EXPECT_EQ(1, Constants::negative_modulus());
}

TEST(Constants, Chained) {
  EXPECT_EQ(10, Constants::chained_div());  // 100 // 5 // 2 == 20 // 2
  EXPECT_EQ(3, Constants::chained_mod());   // 17 % 7 % 4 == 3 % 4
  EXPECT_EQ(1, Constants::mixed_divmod());  // 17 % 7 // 2 == 3 // 2
}

// A field whose size depends on `//`.
TEST(ArrayOfUint16BySizeInBytes, EvenSizeUsesAllBytes) {
  static constexpr ::std::array</**/ ::std::uint8_t, 7> kBuf = {{
      0x06,        // size_in_bytes = 6 -> (6 // 2) * 2 = 6 bytes
      0x01, 0x00,  // elements[0] = 1
      0x02, 0x00,  // elements[1] = 2
      0x03, 0x00,  // elements[2] = 3
  }};
  auto view = MakeArrayOfUint16BySizeInBytesView(&kBuf);
  ASSERT_TRUE(view.Ok());
  EXPECT_EQ(7U, view.SizeInBytes());
  EXPECT_EQ(3U, view.elements().ElementCount());
  EXPECT_EQ(1U, view.elements()[0].Read());
  EXPECT_EQ(3U, view.elements()[2].Read());
}

// Odd size_in_bytes: the trailing odd byte is excluded because (n // 2) * 2
// rounds down to a multiple of 2.
TEST(ArrayOfUint16BySizeInBytes, OddSizeRoundsDown) {
  static constexpr ::std::array</**/ ::std::uint8_t, 5> kBuf = {{
      0x05,        // size_in_bytes = 5 -> (5 // 2) * 2 = 4 bytes
      0x01, 0x00,  // elements[0] = 1
      0x02, 0x00,  // elements[1] = 2
  }};
  auto view = MakeArrayOfUint16BySizeInBytesView(&kBuf);
  ASSERT_TRUE(view.Ok());
  EXPECT_EQ(5U, view.SizeInBytes());
  EXPECT_EQ(2U, view.elements().ElementCount());
}

// ChunkedPayload exercises `((n + 3) // 4) * 4` (round up to a multiple of 4).
TEST(ChunkedPayload, RoundsUpToMultipleOfFour) {
  static constexpr ::std::array</**/ ::std::uint8_t, 9> kBuf = {{
      0x05,                                // chunk_count = 5
      0x11, 0x22, 0x33, 0x44, 0x55,        // 5 used bytes
      0x00, 0x00, 0x00,                    // 3 padding bytes -> 8 total
  }};
  auto view = MakeChunkedPayloadView(&kBuf);
  ASSERT_TRUE(view.Ok());
  // ((5 + 3) // 4) * 4 == 8 bytes of payload, plus the 1-byte count = 9 total.
  EXPECT_EQ(9U, view.SizeInBytes());
  EXPECT_EQ(8U, view.padded().ElementCount());
}

TEST(SignedRuntimeDivision, NegativeDividends) {
  ::std::array</**/ ::std::uint8_t, 13> buf = {};
  auto view = MakeSignedRuntimeDivisionView(&buf);
  view.wide_dividend().Write(-7);
  view.narrow_dividend().Write(-7);
  view.divisor_magnitude().Write(2);
  ASSERT_TRUE(view.Ok());
  EXPECT_EQ(-2, view.wide_quotient_by_constant().Read());   // -7 // 4
  EXPECT_EQ(1, view.wide_remainder_by_constant().Read());   // -7 % 4
  EXPECT_EQ(-4, view.wide_quotient_by_divisor().Read());    // -7 // 2
  EXPECT_EQ(-1, view.wide_remainder_by_negative_divisor().Read());   // -7 % -2
  EXPECT_EQ(3, view.narrow_quotient_by_negative_divisor().Read());   // -7 // -2
  EXPECT_EQ(-1, view.narrow_remainder_by_negative_divisor().Read());  // -7 % -2
}

TEST(SignedRuntimeDivision, MostNegativeDividends) {
  ::std::array</**/ ::std::uint8_t, 13> buf = {};
  auto view = MakeSignedRuntimeDivisionView(&buf);
  constexpr ::std::int64_t kMin64 = ::std::numeric_limits<::std::int64_t>::min();
  constexpr ::std::int32_t kMin32 = ::std::numeric_limits<::std::int32_t>::min();
  view.wide_dividend().Write(kMin64);
  view.narrow_dividend().Write(kMin32);
  // divisor_magnitude == 0 still yields a divisor of magnitude 1.
  view.divisor_magnitude().Write(0);
  ASSERT_TRUE(view.Ok());
  EXPECT_EQ(kMin64 / 4, view.wide_quotient_by_constant().Read());
  EXPECT_EQ(0, view.wide_remainder_by_constant().Read());
  EXPECT_EQ(kMin64, view.wide_quotient_by_divisor().Read());
  // INT64_MIN % -1: mathematically 0; must not trap.
  EXPECT_EQ(0, view.wide_remainder_by_negative_divisor().Read());
  // INT32_MIN // -1 == 2**31, which does not fit in 32 bits but does in the
  // 64-bit intermediate type.
  EXPECT_EQ(::std::int64_t{1} << 31,
            view.narrow_quotient_by_negative_divisor().Read());
  EXPECT_EQ(0, view.narrow_remainder_by_negative_divisor().Read());
}

// A field whose size uses a `//` with a possibly-zero divisor works normally
// when the divisor is nonzero.
TEST(PayloadSizedByDivision, NonzeroDivisor) {
  static constexpr ::std::array</**/ ::std::uint8_t, 5> kBuf = {{
      0x04,                          // divisor = 4 -> 16 // 4 = 4 payload bytes
      0xaa, 0xbb, 0xcc, 0xdd,        // payload
  }};
  auto view = MakePayloadSizedByDivisionView(&kBuf);
  ASSERT_TRUE(view.Ok());
  EXPECT_EQ(5U, view.SizeInBytes());
  EXPECT_EQ(4U, view.payload().ElementCount());
}

// When the divisor is zero the payload size is undefined, so the structure's
// size is unknown and Ok() is false -- with no division-by-zero UB.
TEST(PayloadSizedByDivision, ZeroDivisorIsNotOk) {
  static constexpr ::std::array</**/ ::std::uint8_t, 5> kBuf = {{
      0x00,                          // divisor = 0 -> 16 // 0 undefined
      0xaa, 0xbb, 0xcc, 0xdd,
  }};
  auto view = MakePayloadSizedByDivisionView(&kBuf);
  EXPECT_FALSE(view.Ok());
  EXPECT_FALSE(view.SizeIsKnown());
  EXPECT_FALSE(view.IntrinsicSizeInBytes().Ok());
}

// A field guarded by an existence condition that divides by a field: the
// condition (and therefore Ok()) is well-defined for nonzero divisors...
TEST(FieldGatedByDivision, ConditionTrueAndFalse) {
  // divisor = 4 -> 12 // 4 == 3 -> gated present.
  static constexpr ::std::array</**/ ::std::uint8_t, 2> kPresent = {{0x04, 0x77}};
  auto present = MakeFieldGatedByDivisionView(&kPresent);
  ASSERT_TRUE(present.Ok());
  EXPECT_TRUE(present.has_gated().ValueOr(false));
  EXPECT_EQ(0x77U, present.gated().Read());

  // divisor = 5 -> 12 // 5 == 2 != 3 -> gated absent (only 1 byte needed).
  static constexpr ::std::array</**/ ::std::uint8_t, 1> kAbsent = {{0x05}};
  auto absent = MakeFieldGatedByDivisionView(&kAbsent);
  ASSERT_TRUE(absent.Ok());
  EXPECT_FALSE(absent.has_gated().ValueOr(true));
}

// ...and is *undefined* for a zero divisor.  The existence condition is Unknown,
// so the field's presence is unknown and Ok() must return false.  This is the
// soundness guard for the Ok()/switch discriminant optimization: an undefined
// existence condition must never be folded to a provably-known value.
TEST(FieldGatedByDivision, ZeroDivisorIsNotOk) {
  static constexpr ::std::array</**/ ::std::uint8_t, 2> kBuf = {{0x00, 0x77}};
  auto view = MakeFieldGatedByDivisionView(&kBuf);
  EXPECT_FALSE(view.Ok());
  EXPECT_FALSE(view.has_gated().Known());
}

// `0 // divisor` collapses to the single value {0}, but must not be folded to a
// literal: it is undefined when the divisor is zero.
TEST(CollapsingQuotient, DefinedForNonzeroDivisor) {
  static constexpr ::std::array</**/ ::std::uint8_t, 1> kBuf = {{0x07}};
  auto view = MakeCollapsingQuotientView(&kBuf);
  ASSERT_TRUE(view.Ok());
  EXPECT_TRUE(view.zero_or_undefined().Ok());
  EXPECT_EQ(0, view.zero_or_undefined().Read());
}

TEST(CollapsingQuotient, UndefinedForZeroDivisor) {
  static constexpr ::std::array</**/ ::std::uint8_t, 1> kBuf = {{0x00}};
  auto view = MakeCollapsingQuotientView(&kBuf);
  // The accessor is Unknown -- not a bogus literal 0.
  EXPECT_FALSE(view.zero_or_undefined().Ok());
}

}  // namespace
}  // namespace test
}  // namespace emboss
