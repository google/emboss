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
#include <cstdint>
#include <type_traits>

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

// LeastWidthInteger<n_bits>::Unsigned is the smallest uintNN_t type that can
// hold n_bits or more.  LeastWidthInteger<n_bits>::Signed is the corresponding
// signed type.
template <int kBits>
struct LeastWidthInteger final {
  static_assert(kBits <= 64, "Only bit sizes up to 64 are supported.");
  using Unsigned = typename LeastWidthInteger<kBits + 1>::Unsigned;
  using Signed = typename LeastWidthInteger<kBits + 1>::Signed;
};
template <>
struct LeastWidthInteger<64> final {
  using Unsigned = ::std::uint64_t;
  using Signed = ::std::int64_t;
};
template <>
struct LeastWidthInteger<32> final {
  using Unsigned = ::std::uint32_t;
  using Signed = ::std::int32_t;
};
template <>
struct LeastWidthInteger<16> final {
  using Unsigned = ::std::uint16_t;
  using Signed = ::std::int16_t;
};
template <>
struct LeastWidthInteger<8> final {
  using Unsigned = ::std::uint8_t;
  using Signed = ::std::int8_t;
};

// IsChar<T>::value is true if T is a character type; i.e. const? volatile?
// (signed|unsigned)? char.
template <typename T>
struct IsChar {
  // Note that 'char' is a distinct type from 'signed char' and 'unsigned char'.
  static constexpr bool value =
      ::std::is_same<char, typename ::std::remove_cv<T>::type>::value ||
      ::std::is_same<unsigned char,
                     typename ::std::remove_cv<T>::type>::value ||
      ::std::is_same<signed char, typename ::std::remove_cv<T>::type>::value;
};

// The static member variable requires a definition.
template <typename T>
constexpr bool IsChar<T>::value;

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
