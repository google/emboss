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

// This file contains various C++ type aliases for use in Emboss.
#ifndef EMBOSS_RUNTIME_CPP_EMBOSS_CPP_TYPES_H_
#define EMBOSS_RUNTIME_CPP_EMBOSS_CPP_TYPES_H_

#include <climits>
#include <cstddef>
#include <cstdint>
#include <type_traits>

#include "runtime/cpp/emboss_defines.h"

namespace emboss {
namespace support {

static_assert(sizeof(long long) * CHAR_BIT >= 64,  // NOLINT
              "Emboss requires that long long is at least 64 bits.");

// FloatType<n_bits>::Type is the C++ floating-point type of the appropriate
// size.
template <int kBits>
struct FloatType final {
  static_assert(kBits == 32 || kBits == 64, "Unknown floating-point size.");
};
template <>
struct FloatType<64> final {
  static_assert(sizeof(double) * CHAR_BIT == 64,
                "C++ double type must be 64 bits!");
  using Type = double;
  using UIntType = ::std::uint64_t;
};
template <>
struct FloatType<32> final {
  static_assert(sizeof(float) * CHAR_BIT == 32,
                "C++ float type must be 32 bits!");
  using Type = float;
  using UIntType = ::std::uint32_t;
};

// kMaxIntegerWidth is the widest integer width, in bits, that Emboss supports
// on the current platform: 128 when the compiler provides 128-bit integers
// (EMBOSS_HAS_INT128), otherwise 64.
#if EMBOSS_HAS_INT128
constexpr int kMaxIntegerWidth = 128;
#else
constexpr int kMaxIntegerWidth = 64;
#endif  // EMBOSS_HAS_INT128

// ExactWidthInteger<width>::Unsigned and ::Signed are the integer types of
// exactly `width` bits.  Only the supported widths are defined.
template <int kWidth>
struct ExactWidthInteger;
template <>
struct ExactWidthInteger<8> final {
  using Unsigned = ::std::uint8_t;
  using Signed = ::std::int8_t;
};
template <>
struct ExactWidthInteger<16> final {
  using Unsigned = ::std::uint16_t;
  using Signed = ::std::int16_t;
};
template <>
struct ExactWidthInteger<32> final {
  using Unsigned = ::std::uint32_t;
  using Signed = ::std::int32_t;
};
template <>
struct ExactWidthInteger<64> final {
  using Unsigned = ::std::uint64_t;
  using Signed = ::std::int64_t;
};
#if EMBOSS_HAS_INT128
template <>
struct ExactWidthInteger<128> final {
  using Unsigned = EMBOSS_UINT128_T;
  using Signed = EMBOSS_INT128_T;
};
#endif  // EMBOSS_HAS_INT128

// LeastIntegerWidth(n_bits) is the width of the narrowest supported integer
// type that can hold n_bits bits.  Widths above kMaxIntegerWidth are clamped,
// so that LeastWidthInteger's static_assert is the only diagnostic for an
// unsupported width.
constexpr int LeastIntegerWidth(int n_bits) {
  return n_bits <= 8    ? 8
         : n_bits <= 16 ? 16
         : n_bits <= 32 ? 32
         : n_bits <= 64 ? 64
                        : kMaxIntegerWidth;
}

// LeastWidthInteger<n_bits>::Unsigned is the narrowest of the supported
// exact-width unsigned integer types that can hold n_bits bits; for example,
// LeastWidthInteger<12>::Unsigned is ::std::uint16_t.
// LeastWidthInteger<n_bits>::Signed is the corresponding signed type.
template <int kBits>
struct LeastWidthInteger final {
  static_assert(kBits <= 128, "Only bit widths up to 128 are supported.");
  static_assert(kBits > 128 || kBits <= kMaxIntegerWidth,
                "Bit widths over 64 require 128-bit integer support, which is "
                "not available on this platform (EMBOSS_HAS_INT128 is 0).");
  using Unsigned =
      typename ExactWidthInteger<LeastIntegerWidth(kBits)>::Unsigned;
  using Signed = typename ExactWidthInteger<LeastIntegerWidth(kBits)>::Signed;
};

// MaxWidthUnsigned and MaxWidthSigned are the widest unsigned and signed
// integer types that Emboss supports on the current platform.  They are used
// when a value of unknown (but supported) width must be compared without
// truncation -- for example, when range-checking a value before writing it to
// an integer field.
using MaxWidthUnsigned = ExactWidthInteger<kMaxIntegerWidth>::Unsigned;
using MaxWidthSigned = ExactWidthInteger<kMaxIntegerWidth>::Signed;

// IsAliasSafe<T>::value is true if T is an alias safe type; i.e. const?
// volatile? (unsigned)? char | std::byte.
template <typename T>
struct IsAliasSafe {
  // Note that 'char' is a distinct type from 'signed char' and 'unsigned char'.
  static constexpr bool value =
      ::std::is_same<char, typename ::std::remove_cv<T>::type>::value ||
      ::std::is_same<unsigned char, typename ::std::remove_cv<T>::type>::value
#if __cplusplus >= 201703
      || ::std::is_same<::std::byte, typename ::std::remove_cv<T>::type>::value
#endif
      ;
};

// The static member variable requires a definition.
template <typename T>
constexpr bool IsAliasSafe<T>::value;

// AddSourceConst<SourceT, DestT>::Type is DestT's base type with const added if
// SourceT is const.
template <typename SourceT, typename DestT>
struct AddSourceConst {
  using Type = typename ::std::conditional<
      /**/ ::std::is_const<SourceT>::value,
      typename ::std::add_const<DestT>::type, DestT>::type;
};

// AddSourceVolatile<SourceT, DestT>::Type is DestT's base type with volatile
// added if SourceT is volatile.
template <typename SourceT, typename DestT>
struct AddSourceVolatile {
  using Type = typename ::std::conditional<
      /**/ ::std::is_volatile<SourceT>::value,
      typename ::std::add_volatile<DestT>::type, DestT>::type;
};

// AddCV<SourceT, DestT>::Type is DestT's base type with SourceT's const and
// volatile qualifiers added, if any.
template <typename SourceT, typename DestT>
struct AddSourceCV {
  using Type = typename AddSourceConst<
      SourceT, typename AddSourceVolatile<SourceT, DestT>::Type>::Type;
};

}  // namespace support
}  // namespace emboss

#endif  // EMBOSS_RUNTIME_CPP_EMBOSS_CPP_TYPES_H_
