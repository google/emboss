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

#include <cstddef>

#include "runtime/cpp/emboss_cpp_types.h"

#include "gtest/gtest.h"

namespace emboss {
namespace support {
namespace test {

TEST(FloatTypes, Types) {
  EXPECT_EQ(32U / CHAR_BIT, sizeof(FloatType<32>::Type));
  EXPECT_EQ(64U / CHAR_BIT, sizeof(FloatType<64>::Type));
  EXPECT_EQ(32U / CHAR_BIT, sizeof(FloatType<32>::UIntType));
  EXPECT_EQ(64U / CHAR_BIT, sizeof(FloatType<64>::UIntType));
  EXPECT_TRUE(::std::is_floating_point<FloatType<32>::Type>::value);
  EXPECT_TRUE(::std::is_floating_point<FloatType<64>::Type>::value);
  EXPECT_TRUE(
      (::std::is_same<FloatType<32>::UIntType, ::std::uint32_t>::value));
  EXPECT_TRUE(
      (::std::is_same<FloatType<64>::UIntType, ::std::uint64_t>::value));
}

TEST(LeastWidthInteger, Types) {
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<1>::Unsigned, ::std::uint8_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<1>::Signed, ::std::int8_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<4>::Unsigned, ::std::uint8_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<4>::Signed, ::std::int8_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<7>::Unsigned, ::std::uint8_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<7>::Signed, ::std::int8_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<8>::Unsigned, ::std::uint8_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<8>::Signed, ::std::int8_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<9>::Unsigned, ::std::uint16_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<9>::Signed, ::std::int16_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<12>::Unsigned, ::std::uint16_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<12>::Signed, ::std::int16_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<15>::Unsigned, ::std::uint16_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<15>::Signed, ::std::int16_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<16>::Unsigned, ::std::uint16_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<16>::Signed, ::std::int16_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<17>::Unsigned, ::std::uint32_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<17>::Signed, ::std::int32_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<28>::Unsigned, ::std::uint32_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<28>::Signed, ::std::int32_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<31>::Unsigned, ::std::uint32_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<31>::Signed, ::std::int32_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<32>::Unsigned, ::std::uint32_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<32>::Signed, ::std::int32_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<33>::Unsigned, ::std::uint64_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<33>::Signed, ::std::int64_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<60>::Unsigned, ::std::uint64_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<60>::Signed, ::std::int64_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<63>::Unsigned, ::std::uint64_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<63>::Signed, ::std::int64_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<64>::Unsigned, ::std::uint64_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<64>::Signed, ::std::int64_t>::value));
#if EMBOSS_HAS_INT128
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<65>::Unsigned, __uint128_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<65>::Signed, __int128_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<96>::Unsigned, __uint128_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<96>::Signed, __int128_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<127>::Unsigned, __uint128_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<127>::Signed, __int128_t>::value));
  EXPECT_TRUE((
      ::std::is_same<LeastWidthInteger<128>::Unsigned, __uint128_t>::value));
  EXPECT_TRUE(
      (::std::is_same<LeastWidthInteger<128>::Signed, __int128_t>::value));
#endif  // EMBOSS_HAS_INT128
}

TEST(IsAliasSafe, CharTypes) {
  EXPECT_TRUE(IsAliasSafe<char>::value);
  EXPECT_TRUE(IsAliasSafe<unsigned char>::value);
  EXPECT_TRUE(IsAliasSafe<const char>::value);
  EXPECT_TRUE(IsAliasSafe<const unsigned char>::value);
  EXPECT_TRUE(IsAliasSafe<volatile char>::value);
  EXPECT_TRUE(IsAliasSafe<volatile unsigned char>::value);
  EXPECT_TRUE(IsAliasSafe<const volatile char>::value);
  EXPECT_TRUE(IsAliasSafe<const volatile unsigned char>::value);
#if __cplusplus >= 201703
  EXPECT_TRUE(IsAliasSafe<::std::byte>::value);
  EXPECT_TRUE(IsAliasSafe<const ::std::byte>::value);
  EXPECT_TRUE(IsAliasSafe<volatile ::std::byte>::value);
  EXPECT_TRUE(IsAliasSafe<const volatile ::std::byte>::value);
#endif
}

TEST(IsAliasSafe, NonCharTypes) {
  struct OneByte {
    char c;
  };
  EXPECT_EQ(1U, sizeof(OneByte));
  EXPECT_FALSE(IsAliasSafe<int>::value);
  EXPECT_FALSE(IsAliasSafe<unsigned>::value);
  EXPECT_FALSE(IsAliasSafe<const int>::value);
  EXPECT_FALSE(IsAliasSafe<OneByte>::value);

  EXPECT_FALSE(IsAliasSafe<signed char>::value);
  EXPECT_FALSE(IsAliasSafe<const signed char>::value);
  EXPECT_FALSE(IsAliasSafe<volatile signed char>::value);
  EXPECT_FALSE(IsAliasSafe<const volatile signed char>::value);
}

TEST(AddSourceConst, AddSourceConst) {
  EXPECT_TRUE(
      (::std::is_same<const char,
                      typename AddSourceConst<const int, char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<
          const volatile char,
          typename AddSourceConst<const int, volatile char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<char, typename AddSourceConst<int, char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<
          char, typename AddSourceConst<volatile int, char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<const char,
                      typename AddSourceConst<int, const char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<const char, typename AddSourceConst<
                                      const int, const char>::Type>::value));
}

TEST(AddSourceVolatile, AddSourceVolatile) {
  EXPECT_TRUE(
      (::std::is_same<volatile char, typename AddSourceVolatile<
                                         volatile int, char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<
          const volatile char,
          typename AddSourceVolatile<volatile int, const char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<char,
                      typename AddSourceVolatile<int, char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<
          char, typename AddSourceVolatile<const int, char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<volatile char, typename AddSourceVolatile<
                                         int, volatile char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<volatile char,
                      typename AddSourceVolatile<volatile int,
                                                 volatile char>::Type>::value));
}

TEST(AddSourceCV, AddSourceCV) {
  EXPECT_TRUE(
      (::std::is_same<const char,
                      typename AddSourceCV<const int, char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<volatile char,
                      typename AddSourceCV<volatile int, char>::Type>::value));
  EXPECT_TRUE((::std::is_same<
               const volatile char,
               typename AddSourceCV<volatile int, const char>::Type>::value));
  EXPECT_TRUE((::std::is_same<
               const volatile char,
               typename AddSourceCV<const int, volatile char>::Type>::value));
  EXPECT_TRUE((::std::is_same<
               const volatile char,
               typename AddSourceCV<const volatile int, char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<char, typename AddSourceCV<int, char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<volatile char,
                      typename AddSourceCV<int, volatile char>::Type>::value));
  EXPECT_TRUE(
      (::std::is_same<
          volatile char,
          typename AddSourceCV<volatile int, volatile char>::Type>::value));
}
}  // namespace test
}  // namespace support
}  // namespace emboss
