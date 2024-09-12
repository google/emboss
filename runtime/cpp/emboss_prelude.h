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

// This header contains implementations of the types in the Emboss Prelude
// (UInt, Int, Flag, etc.)
#ifndef EMBOSS_RUNTIME_CPP_EMBOSS_PRELUDE_H_
#define EMBOSS_RUNTIME_CPP_EMBOSS_PRELUDE_H_

#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <limits>
#include <type_traits>
#include <utility>

#include "runtime/cpp/emboss_cpp_util.h"

// Forward declarations for optional text processing helpers.
namespace emboss {
class TextOutputOptions;
namespace support {
template <class Stream, class View>
bool ReadBooleanFromTextStream(View *view, Stream *stream);
template <class Stream, class View>
void WriteBooleanViewToTextStream(View *view, Stream *stream,
                                  const TextOutputOptions &);

template <class Stream, class View>
bool ReadIntegerFromTextStream(View *view, Stream *stream);
template <class Stream, class View>
void WriteIntegerViewToTextStream(View *view, Stream *stream,
                                  const TextOutputOptions &options);

template <class Stream, class View>
bool ReadFloatFromTextStream(View *view, Stream *stream);
template <class Stream, class Float>
void WriteFloatToTextStream(Float n, Stream *stream,
                            const TextOutputOptions &options);
}  // namespace support
}  // namespace emboss

// This namespace must match the [(cpp) namespace] in the Emboss prelude.
namespace emboss {
namespace prelude {

// FlagView is the C++ implementation of the Emboss "Flag" type, which is a
// 1-bit value.
template <class Parameters, class BitBlock>
class FlagView final {
 public:
  static_assert(Parameters::kBits == 1, "FlagView must be 1 bit.");

  explicit FlagView(BitBlock bits) : bit_block_{bits} {}
  FlagView() : bit_block_() {}
  FlagView(const FlagView &) = default;
  FlagView(FlagView &&) = default;
  FlagView &operator=(const FlagView &) = default;
  FlagView &operator=(FlagView &&) = default;
  ~FlagView() = default;

  bool Read() const {
    bool result = bit_block_.ReadUInt();
    EMBOSS_CHECK(Parameters::ValueIsOk(result));
    return result;
  }
  bool UncheckedRead() const { return bit_block_.UncheckedReadUInt(); }
  void Write(bool value) const {
    const bool result = TryToWrite(value);
    (void)result;
    EMBOSS_CHECK(result);
  }
  bool TryToWrite(bool value) const {
    if (!CouldWriteValue(value)) return false;
    if (!IsComplete()) return false;
    bit_block_.WriteUInt(value);
    return true;
  }
  static constexpr bool CouldWriteValue(bool value) {
    return Parameters::ValueIsOk(value);
  }
  void UncheckedWrite(bool value) const {
    bit_block_.UncheckedWriteUInt(value);
  }

  template <typename OtherView>
  void CopyFrom(const OtherView &other) const {
    Write(other.Read());
  }
  template <typename OtherView>
  void UncheckedCopyFrom(const OtherView &other) const {
    UncheckedWrite(other.UncheckedRead());
  }
  template <typename OtherView>
  bool TryToCopyFrom(const OtherView &other) const {
    return TryToWrite(other.Read());
  }

  bool Ok() const {
    return IsComplete() && Parameters::ValueIsOk(UncheckedRead());
  }
  template <class OtherBitBlock>
  bool Equals(const FlagView<Parameters, OtherBitBlock> &other) const {
    return Read() == other.Read();
  }
  template <class OtherBitBlock>
  bool UncheckedEquals(const FlagView<Parameters, OtherBitBlock> &other) const {
    return UncheckedRead() == other.UncheckedRead();
  }
  bool IsComplete() const {
    return bit_block_.Ok() && bit_block_.SizeInBits() > 0;
  }

  template <class Stream>
  bool UpdateFromTextStream(Stream *stream) const {
    return ::emboss::support::ReadBooleanFromTextStream(this, stream);
  }

  template <class Stream>
  void WriteToTextStream(Stream *stream,
                         const ::emboss::TextOutputOptions &options) const {
    ::emboss::support::WriteBooleanViewToTextStream(this, stream, options);
  }

  static constexpr bool IsAggregate() { return false; }

 private:
  BitBlock bit_block_;
};

// UIntView is a view for UInts inside of bitfields.
template <class Parameters, class BitViewType>
class UIntView final {
 public:
  using ValueType = typename ::emboss::support::LeastWidthInteger<
      Parameters::kBits>::Unsigned;

  static_assert(
      Parameters::kBits <= sizeof(ValueType) * 8,
      "UIntView requires sizeof(ValueType) * 8 >= Parameters::kBits.");

  template <typename... Args>
  explicit UIntView(Args &&...args) : buffer_{::std::forward<Args>(args)...} {}
  UIntView() : buffer_() {}
  UIntView(const UIntView &) = default;
  UIntView(UIntView &&) = default;
  UIntView &operator=(const UIntView &) = default;
  UIntView &operator=(UIntView &&) = default;
  ~UIntView() = default;

  ValueType Read() const {
    ValueType result = static_cast<ValueType>(buffer_.ReadUInt());
    EMBOSS_CHECK(Parameters::ValueIsOk(result));
    return result;
  }
  ValueType UncheckedRead() const { return buffer_.UncheckedReadUInt(); }

  // The Write, TryToWrite, and CouldWriteValue methods are templated in order
  // to avoid surprises due to implicit narrowing.
  //
  // In C++, you can pass (say) an `int` to a function expecting `uint8_t`, and
  // the compiler will silently cast the `int` to `uint8_t`, which can change
  // the value.  Even with fairly aggressive warnings, something like this will
  // silently compile, and print `256 is not >= 128!`:
  //
  //    bool is_big_uint8(uint8_t value) { return value >= 128; }
  //    bool is_big(uint32_t value) { return is_big_uint8(value); }
  //    int main() {
  //        assert(!is_big(256));  // big is truncated to 0.
  //        std::cout << 256 << " is not >= 128!\n";
  //        return 0;
  //    }
  //
  // (Most compilers will give a warning when directly passing a *constant* that
  // gets truncated; for example, GCC will throw -Woverflow on
  // `is_big_uint8(256U)`.)
  template <typename IntT,
            typename = typename ::std::enable_if<
                (::std::numeric_limits<typename ::std::remove_cv<
                     typename ::std::remove_reference<IntT>::type>::type>::
                     is_integer &&
                 !::std::is_same<bool, typename ::std::remove_cv<
                                           typename ::std::remove_reference<
                                               IntT>::type>::type>::value) ||
                ::std::is_enum<IntT>::value>::type>
  void Write(IntT value) const {
    const bool result = TryToWrite(value);
    (void)result;
    EMBOSS_CHECK(result);
  }

  template <typename IntT,
            typename = typename ::std::enable_if<
                (::std::numeric_limits<typename ::std::remove_cv<
                     typename ::std::remove_reference<IntT>::type>::type>::
                     is_integer &&
                 !::std::is_same<bool, typename ::std::remove_cv<
                                           typename ::std::remove_reference<
                                               IntT>::type>::type>::value) ||
                ::std::is_enum<IntT>::value>::type>
  bool TryToWrite(IntT value) const {
    if (!CouldWriteValue(value)) return false;
    if (!IsComplete()) return false;
    buffer_.WriteUInt(static_cast<ValueType>(value));
    return true;
  }

  template <typename IntT,
            typename = typename ::std::enable_if<
                (::std::numeric_limits<typename ::std::remove_cv<
                     typename ::std::remove_reference<IntT>::type>::type>::
                     is_integer &&
                 !::std::is_same<bool, typename ::std::remove_cv<
                                           typename ::std::remove_reference<
                                               IntT>::type>::type>::value) ||
                ::std::is_enum<IntT>::value>::type>
  static constexpr bool CouldWriteValue(IntT value) {
    // Implicit conversions are doing some work here, but the upshot is that the
    // value must be at least 0, and at most (2**kBits)-1.  The clause to
    // compute (2**kBits)-1 should not be "simplified" further.
    //
    // Because of C++ implicit integer promotions, the (2**kBits)-1 computation
    // works differently when `ValueType` is smaller than `unsigned int` than it
    // does when `ValueType` is at least as big as `unsigned int`.
    //
    // For example, when `ValueType` is `uint8_t` and `kBits` is 8:
    //
    // 1.   `static_cast<ValueType>(1)` becomes `uint8_t(1)`.
    // 2.   `uint8_t(1) << (kBits - 1)` is `uint8_t(1) << 7`.
    // 3.   The shift operator `<<` promotes its left operand to `unsigned`,
    //      giving `unsigned(1) << 7`.
    // 4.   `unsigned(1) << 7` becomes `unsigned(0x80)`.
    // 5.   `unsigned(0x80) << 1` becomes `unsigned(0x100)`.
    // 6.   Finally, `unsigned(0x100) - 1` is `unsigned(0xff)`.
    //
    // (Note that the cases where `kBits` is less than `sizeof(ValueType) * 8`
    // are very similar.)
    //
    // When `ValueType` is `uint32_t`, `unsigned` is 32 bits, and `kBits` is 32:
    //
    // 1.   `static_cast<ValueType>(1)` becomes `uint32_t(1)`.
    // 2.   `uint32_t(1) << (kBits - 1)` is `uint32_t(1) << 31`.
    // 3.   The shift operator `<<` does *not* further promote `uint32_t`.
    // 4.   `uint32_t(1) << 31` becomes `uint32_t(0x80000000)`.  Note that
    //      `uint32_t(1) << 32` would be undefined behavior (shift of >= the
    //      size of the left operand type), which is why the shift is broken
    //      into two parts.
    // 5.   `uint32_t(0x80000000) << 1` overflows, leaving `uint32_t(0)`.
    // 6.   `uint32_t(0) - 1` underflows, leaving `uint32_t(0xffffffff)`.
    //
    // Because unsigned overflow and underflow are defined to be modulo 2**N,
    // where N is the number of bits in the type, this is entirely
    // standards-compliant.
    return value >= 0 &&
           static_cast</**/ ::std::uint64_t>(value) <=
               ((static_cast<ValueType>(1) << (Parameters::kBits - 1)) << 1) -
                   1 &&
           Parameters::ValueIsOk(static_cast<ValueType>(value));
  }
  void UncheckedWrite(ValueType value) const {
    buffer_.UncheckedWriteUInt(value);
  }

  template <typename OtherView>
  void CopyFrom(const OtherView &other) const {
    Write(other.Read());
  }
  template <typename OtherView>
  void UncheckedCopyFrom(const OtherView &other) const {
    UncheckedWrite(other.UncheckedRead());
  }
  template <typename OtherView>
  bool TryToCopyFrom(const OtherView &other) const {
    return other.Ok() && TryToWrite(other.Read());
  }

  // All bit patterns in the underlying buffer are valid, so Ok() is always
  // true if IsComplete() is true.
  bool Ok() const {
    return IsComplete() && Parameters::ValueIsOk(UncheckedRead());
  }
  template <class OtherBitViewType>
  bool Equals(const UIntView<Parameters, OtherBitViewType> &other) const {
    return Read() == other.Read();
  }
  template <class OtherBitViewType>
  bool UncheckedEquals(
      const UIntView<Parameters, OtherBitViewType> &other) const {
    return UncheckedRead() == other.UncheckedRead();
  }
  bool IsComplete() const {
    return buffer_.Ok() && buffer_.SizeInBits() >= Parameters::kBits;
  }

  template <class Stream>
  bool UpdateFromTextStream(Stream *stream) const {
    return support::ReadIntegerFromTextStream(this, stream);
  }

  template <class Stream>
  void WriteToTextStream(Stream *stream,
                         ::emboss::TextOutputOptions &options) const {
    support::WriteIntegerViewToTextStream(this, stream, options);
  }

  static constexpr bool IsAggregate() { return false; }

  static constexpr int SizeInBits() { return Parameters::kBits; }

 private:
  BitViewType buffer_;
};

// IntView is a view for Ints inside of bitfields.
template <class Parameters, class BitViewType>
class IntView final {
 public:
  using ValueType =
      typename ::emboss::support::LeastWidthInteger<Parameters::kBits>::Signed;

  static_assert(Parameters::kBits <= sizeof(ValueType) * 8,
                "IntView requires sizeof(ValueType) * 8 >= Parameters::kBits.");

  template <typename... Args>
  explicit IntView(Args &&...args) : buffer_{::std::forward<Args>(args)...} {}
  IntView() : buffer_() {}
  IntView(const IntView &) = default;
  IntView(IntView &&) = default;
  IntView &operator=(const IntView &) = default;
  IntView &operator=(IntView &&) = default;
  ~IntView() = default;

  ValueType Read() const {
    ValueType value = ConvertToSigned(buffer_.ReadUInt());
    EMBOSS_CHECK(Parameters::ValueIsOk(value));
    return value;
  }
  ValueType UncheckedRead() const {
    return ConvertToSigned(buffer_.UncheckedReadUInt());
  }
  // As with UIntView, above, Write, TryToWrite, and CouldWriteValue need to be
  // templated in order to avoid surprises due to implicit narrowing
  // conversions.
  template <typename IntT,
            typename = typename ::std::enable_if<
                (::std::numeric_limits<typename ::std::remove_cv<
                     typename ::std::remove_reference<IntT>::type>::type>::
                     is_integer &&
                 !::std::is_same<bool, typename ::std::remove_cv<
                                           typename ::std::remove_reference<
                                               IntT>::type>::type>::value) ||
                ::std::is_enum<IntT>::value>::type>
  void Write(IntT value) const {
    const bool result = TryToWrite(value);
    (void)result;
    EMBOSS_CHECK(result);
  }

  template <typename IntT,
            typename = typename ::std::enable_if<
                (::std::numeric_limits<typename ::std::remove_cv<
                     typename ::std::remove_reference<IntT>::type>::type>::
                     is_integer &&
                 !::std::is_same<bool, typename ::std::remove_cv<
                                           typename ::std::remove_reference<
                                               IntT>::type>::type>::value) ||
                ::std::is_enum<IntT>::value>::type>
  bool TryToWrite(IntT value) const {
    if (!CouldWriteValue(value)) return false;
    if (!IsComplete()) return false;
    buffer_.WriteUInt(::emboss::support::MaskToNBits(
        static_cast<typename BitViewType::ValueType>(value),
        Parameters::kBits));
    return true;
  }

  template <typename IntT,
            typename = typename ::std::enable_if<
                (::std::numeric_limits<typename ::std::remove_cv<
                     typename ::std::remove_reference<IntT>::type>::type>::
                     is_integer &&
                 !::std::is_same<bool, typename ::std::remove_cv<
                                           typename ::std::remove_reference<
                                               IntT>::type>::type>::value) ||
                ::std::is_enum<IntT>::value>::type>
  static constexpr bool CouldWriteValue(IntT value) {
    // This effectively checks that value >= -(2**(kBits-1) and value <=
    // (2**(kBits-1))-1.
    //
    // This has to be done somewhat piecemeal, in order to avoid various bits of
    // undefined and implementation-defined behavior.
    //
    // First, if IntT is an unsigned type, the check that value >=
    // -(2**(kBits-1)) is skipped, in order to avoid any signed <-> unsigned
    // conversions.
    //
    // Second, if kBits is 1, then the limits -1 and 0 are explicit, so that
    // there is never a shift by -1 (which is undefined behavior).
    //
    // Third, the shifts are by (kBits - 2), so that they do not alter sign
    // bits.  To get the final bounds, we use a bit of addition and
    // multiplication.  For example, for 8 bits, the lower bound is (1 << 6) *
    // -2, which is 64 * -2, which is -128.  The corresponding upper bound is
    // ((1 << 6) - 1) * 2 + 1, which is (64 - 1) * 2 + 1, which is 63 * 2 + 1,
    // which is 126 + 1, which is 127.  The upper bound must be computed in
    // multiple steps like this in order to avoid overflow.
    return (!::std::is_signed<typename ::std::remove_cv<
                typename ::std::remove_reference<IntT>::type>::type>::value ||
            static_cast</**/ ::std::int64_t>(value) >=
                (Parameters::kBits == 1
                     ? -1
                     : (static_cast<ValueType>(1) << (Parameters::kBits - 2)) *
                           -2)) &&
           value <=
               (Parameters::kBits == 1
                    ? 0
                    : ((static_cast<ValueType>(1) << (Parameters::kBits - 2)) -
                       1) * 2 +
                          1) &&
           Parameters::ValueIsOk(static_cast<ValueType>(value));

  }

  void UncheckedWrite(ValueType value) const {
    buffer_.UncheckedWriteUInt(::emboss::support::MaskToNBits(
        static_cast<typename BitViewType::ValueType>(value),
        Parameters::kBits));
  }

  template <typename OtherView>
  void CopyFrom(const OtherView &other) const {
    Write(other.Read());
  }
  template <typename OtherView>
  void UncheckedCopyFrom(const IntView &other) const {
    UncheckedWrite(other.UncheckedRead());
  }
  template <typename OtherView>
  bool TryToCopyFrom(const OtherView &other) const {
    return other.Ok() && TryToWrite(other.Read());
  }

  // All bit patterns in the underlying buffer are valid, so Ok() is always
  // true if IsComplete() is true.
  bool Ok() const {
    return IsComplete() && Parameters::ValueIsOk(UncheckedRead());
  }
  template <class OtherBitViewType>
  bool Equals(const IntView<Parameters, OtherBitViewType> &other) const {
    return Read() == other.Read();
  }
  template <class OtherBitViewType>
  bool UncheckedEquals(
      const IntView<Parameters, OtherBitViewType> &other) const {
    return UncheckedRead() == other.UncheckedRead();
  }
  bool IsComplete() const {
    return buffer_.Ok() && buffer_.SizeInBits() >= Parameters::kBits;
  }

  template <class Stream>
  bool UpdateFromTextStream(Stream *stream) const {
    return support::ReadIntegerFromTextStream(this, stream);
  }

  template <class Stream>
  void WriteToTextStream(Stream *stream,
                         ::emboss::TextOutputOptions &options) const {
    support::WriteIntegerViewToTextStream(this, stream, options);
  }

  static constexpr bool IsAggregate() { return false; }

  static constexpr int SizeInBits() { return Parameters::kBits; }

 private:
  static ValueType ConvertToSigned(typename BitViewType::ValueType data) {
    static_assert(sizeof(ValueType) <= sizeof(typename BitViewType::ValueType),
                  "Integer types wider than BitViewType::ValueType are not "
                  "supported.");
#if EMBOSS_SYSTEM_IS_TWOS_COMPLEMENT
    // static_cast from unsigned to signed is implementation-defined when the
    // value does not fit in the signed type (in this case, when the final value
    // should be negative).  Most implementations use a reasonable definition,
    // so on most systems we can just cast.
    //
    // If the integer does not take up the full width of ValueType, it needs to
    // be sign-extended until it does.  The easiest way to do this is to shift
    // until the sign bit is in the topmost position, then cast to signed, then
    // shift back.  The shift back will copy the sign bit.
    return static_cast<ValueType>(
               data << (sizeof(ValueType) * 8 - Parameters::kBits)) >>
           (sizeof(ValueType) * 8 - Parameters::kBits);
#else
    // Otherwise, in order to convert without running into
    // implementation-defined behavior, first mask out the sign bit.  This
    // results in (final result MOD 2 ** (width of int in bits - 1)).  That
    // value can be safely converted to the signed ValueType.
    //
    // Finally, if the sign bit was set, subtract (2 ** (width of int in bits -
    // 2)) twice.
    //
    // The 1-bit signed integer case must be handled separately, but it is
    // (fortunately) quite easy to enumerate both possible values.
    if (Parameters::kBits == 1) {
      if (data == 0) {
        return 0;
      } else if (data == 1) {
        return -1;
      } else {
        EMBOSS_CHECK(false);
        return -1;  // Return value if EMBOSS_CHECK is disabled.
      }
    } else {
      typename BitViewType::ValueType sign_bit =
          static_cast<typename BitViewType::ValueType>(1)
          << (Parameters::kBits - 1);
      typename BitViewType::ValueType mask = sign_bit - 1;
      typename BitViewType::ValueType data_mod2_to_n = mask & data;
      ValueType result_sign_bit =
          static_cast<ValueType>((data & sign_bit) >> 1);
      return data_mod2_to_n - result_sign_bit - result_sign_bit;
    }
#endif
  }

  BitViewType buffer_;
};

// The maximum Binary-Coded Decimal (BCD) value that fits in a particular number
// of bits.
template <typename ValueType>
constexpr inline ValueType MaxBcd(int bits) {
  return bits < 4 ? (1 << bits) - 1
                  : 10 * (MaxBcd<ValueType>(bits - 4) + 1) - 1;
}

template <typename ValueType>
inline bool IsBcd(ValueType x) {
  // Adapted from:
  // https://graphics.stanford.edu/~seander/bithacks.html#HasLessInWord
  //
  // This determines if any nibble has a value greater than 9.  It does
  // this by treating operations on the n-bit value as parallel operations
  // on n/4 4-bit values.
  //
  // The result is computed in the high bit of each nibble: if any of those
  // bits is set in the end, then at least one nibble had a value in the
  // range 10-15.
  //
  // The first check is subtle: ~x is equivalent to (nibble = 15 - nibble).
  // Then, 6 is subtracted from each nibble.  This operation will underflow
  // if the original value was more than 9, leaving the high bit of the
  // nibble set.  It will also leave the high bit of the nibble set
  // (without underflow) if the original value was 0 or 1.
  //
  // The second check is just x: the high bit of each nibble in x is set if
  // that nibble's value is 8-15.
  //
  // Thus, the first check leaves the high bit set in any nibble with the
  // value 0, 1, or 10-15, and the second check leaves the high bit set in
  // any nibble with the value 8-15.  Bitwise-anding these results, high
  // bits are only set if the original value was 10-15.
  //
  // The underflow condition in the first check can screw up the condition
  // for nibbles in higher positions than the underflowing nibble.  This
  // cannot affect the overall boolean result, because the underflow
  // condition only happens if a nibble was greater than 9, and therefore
  // *that* nibble's final value will be nonzero, and therefore the whole
  // result will be nonzero, no matter what happens in the higher-order
  // nibbles.
  //
  // A couple of examples in 16 bit:
  //
  // x = 0x09a8
  // (~0x09a8 - 0x6666) & 0x09a8 & 0x8888
  // ( 0xf657 - 0x6666) & 0x09a8 & 0x8888
  //            0x8ff1  & 0x09a8 & 0x8888
  //                      0x09a0 & 0x8888
  //                               0x0880  Note the underflow into nibble 2
  //
  // x = 0x1289
  // (~0x1289 - 0x6666) & 0x1289 & 0x8888
  // ( 0xed76 - 0x6666) & 0x1289 & 0x8888
  //            0x8710  & 0x1289 & 0x8888
  //                      0x0200 & 0x8888
  //                               0x0000
  static_assert(!::std::is_signed<ValueType>::value,
                "IsBcd only works on unsigned values.");
  if (sizeof(ValueType) < sizeof(unsigned)) {
    // For types with lower integer conversion rank than unsigned int, integer
    // promotion rules cause many implicit conversions to signed int in the math
    // below, which makes the math go wrong.  Rather than add a dozen explicit
    // casts back to ValueType, just do the math as 'unsigned'.
    return IsBcd<unsigned>(x);
  } else {
    return ((~x - (~ValueType{0} / 0xf * 0x6 /* 0x6666...6666 */)) & x &
            (~ValueType{0} / 0xf * 0x8 /* 0x8888...8888 */)) == 0;
  }
}

// Base template for Binary-Coded Decimal (BCD) unsigned integer readers.
template <class Parameters, class BitViewType>
class BcdView final {
 public:
  using ValueType = typename ::emboss::support::LeastWidthInteger<
      Parameters::kBits>::Unsigned;

  static_assert(Parameters::kBits <= sizeof(ValueType) * 8,
                "BcdView requires sizeof(ValueType) * 8 >= Parameters::kBits.");

  template <typename... Args>
  explicit BcdView(Args &&...args) : buffer_{::std::forward<Args>(args)...} {}
  BcdView() : buffer_() {}
  BcdView(const BcdView &) = default;
  BcdView(BcdView &&) = default;
  BcdView &operator=(const BcdView &) = default;
  BcdView &operator=(BcdView &&) = default;
  ~BcdView() = default;

  ValueType Read() const {
    EMBOSS_CHECK(Ok());
    return ConvertToBinary(buffer_.ReadUInt());
  }
  ValueType UncheckedRead() const {
    return ConvertToBinary(buffer_.UncheckedReadUInt());
  }
  void Write(ValueType value) const {
    const bool result = TryToWrite(value);
    (void)result;
    EMBOSS_CHECK(result);
  }
  bool TryToWrite(ValueType value) const {
    if (!CouldWriteValue(value)) return false;
    if (!IsComplete()) return false;
    buffer_.WriteUInt(ConvertToBcd(value));
    return true;
  }
  static constexpr bool CouldWriteValue(ValueType value) {
    return value <= MaxValue() && Parameters::ValueIsOk(value);
  }
  void UncheckedWrite(ValueType value) const {
    buffer_.UncheckedWriteUInt(ConvertToBcd(value));
  }

  template <class Stream>
  bool UpdateFromTextStream(Stream *stream) const {
    return support::ReadIntegerFromTextStream(this, stream);
  }

  template <class Stream>
  void WriteToTextStream(Stream *stream,
                         ::emboss::TextOutputOptions &options) const {
    // TODO(bolms): This shares the numeric_base() option with IntView and
    // UIntView (and EnumView, for unknown enum values).  It seems like an end
    // user might prefer to see BCD values in decimal, even if they want to see
    // values of other numeric types in hex or binary.  It seems like there
    // could be some fancy C++ trickery to allow separate options for separate
    // view types.
    support::WriteIntegerViewToTextStream(this, stream, options);
  }

  static constexpr bool IsAggregate() { return false; }

  template <typename OtherView>
  void CopyFrom(const OtherView &other) const {
    Write(other.Read());
  }
  template <typename OtherView>
  void UncheckedCopyFrom(const OtherView &other) const {
    UncheckedWrite(other.UncheckedRead());
  }
  template <typename OtherView>
  bool TryToCopyFrom(const OtherView &other) const {
    return other.Ok() && TryToWrite(other.Read());
  }

  bool Ok() const {
    if (!IsComplete()) return false;
    if (!IsBcd(buffer_.ReadUInt())) return false;
    if (!Parameters::ValueIsOk(UncheckedRead())) return false;
    return true;
  }
  template <class OtherBitViewType>
  bool Equals(const BcdView<Parameters, OtherBitViewType> &other) const {
    return Read() == other.Read();
  }
  template <class OtherBitViewType>
  bool UncheckedEquals(
      const BcdView<Parameters, OtherBitViewType> &other) const {
    return UncheckedRead() == other.UncheckedRead();
  }
  bool IsComplete() const {
    return buffer_.Ok() && buffer_.SizeInBits() >= Parameters::kBits;
  }

  static constexpr int SizeInBits() { return Parameters::kBits; }

 private:
  static ValueType ConvertToBinary(ValueType bcd_value) {
    ValueType result = 0;
    ValueType multiplier = 1;
    for (int shift = 0; shift < Parameters::kBits; shift += 4) {
      result += ((bcd_value >> shift) & 0xf) * multiplier;
      multiplier *= 10;
    }
    return result;
  }

  static ValueType ConvertToBcd(ValueType value) {
    ValueType bcd_value = 0;
    for (int shift = 0; shift < Parameters::kBits; shift += 4) {
      bcd_value |= (value % 10) << shift;
      value /= 10;
    }
    return bcd_value;
  }

  static constexpr ValueType MaxValue() {
    return MaxBcd<ValueType>(Parameters::kBits);
  }

  BitViewType buffer_;
};

// FloatView is the view for the Emboss Float type.
template <class Parameters, class BitViewType>
class FloatView final {
  static_assert(Parameters::kBits == 32 || Parameters::kBits == 64,
                "Only 32- and 64-bit floats are currently supported.");

 public:
  using ValueType = typename support::FloatType<Parameters::kBits>::Type;

  template <typename... Args>
  explicit FloatView(Args &&...args) : buffer_{::std::forward<Args>(args)...} {}
  FloatView() : buffer_() {}
  FloatView(const FloatView &) = default;
  FloatView(FloatView &&) = default;
  FloatView &operator=(const FloatView &) = default;
  FloatView &operator=(FloatView &&) = default;
  ~FloatView() = default;

  ValueType Read() const { return ConvertToFloat(buffer_.ReadUInt()); }
  ValueType UncheckedRead() const {
    return ConvertToFloat(buffer_.UncheckedReadUInt());
  }
  void Write(ValueType value) const {
    const bool result = TryToWrite(value);
    (void)result;
    EMBOSS_CHECK(result);
  }
  bool TryToWrite(ValueType value) const {
    if (!CouldWriteValue(value)) return false;
    if (!IsComplete()) return false;
    buffer_.WriteUInt(ConvertToUInt(value));
    return true;
  }
  static constexpr bool CouldWriteValue(ValueType value) {
    // Avoid unused parameters error:
    static_cast<void>(value);
    return true;
  }
  void UncheckedWrite(ValueType value) const {
    buffer_.UncheckedWriteUInt(ConvertToUInt(value));
  }

  template <typename OtherView>
  void CopyFrom(const OtherView &other) const {
    Write(other.Read());
  }
  template <typename OtherView>
  void UncheckedCopyFrom(const OtherView &other) const {
    UncheckedWrite(other.UncheckedRead());
  }
  template <typename OtherView>
  bool TryToCopyFrom(const OtherView &other) const {
    return other.Ok() && TryToWrite(other.Read());
  }

  // All bit patterns in the underlying buffer are valid, so Ok() is always
  // true if IsComplete() is true.
  bool Ok() const { return IsComplete(); }
  template <class OtherBitViewType>
  bool Equals(const FloatView<Parameters, OtherBitViewType> &other) const {
    return Read() == other.Read();
  }
  template <class OtherBitViewType>
  bool UncheckedEquals(
      const FloatView<Parameters, OtherBitViewType> &other) const {
    return UncheckedRead() == other.UncheckedRead();
  }
  bool IsComplete() const {
    return buffer_.Ok() && buffer_.SizeInBits() >= Parameters::kBits;
  }

  template <class Stream>
  bool UpdateFromTextStream(Stream *stream) const {
    return support::ReadFloatFromTextStream(this, stream);
  }

  template <class Stream>
  void WriteToTextStream(Stream *stream,
                         ::emboss::TextOutputOptions &options) const {
    support::WriteFloatToTextStream(Read(), stream, options);
  }

  static constexpr bool IsAggregate() { return false; }

  static constexpr int SizeInBits() { return Parameters::kBits; }

 private:
  using UIntType = typename support::FloatType<Parameters::kBits>::UIntType;
  static ValueType ConvertToFloat(UIntType bits) {
    // TODO(bolms): This method assumes a few things that are not always
    // strictly true; e.g., that uint32_t and float have the same endianness.
    ValueType result;
    memcpy(static_cast<void *>(&result), static_cast<void *>(&bits),
           sizeof result);
    return result;
  }

  static UIntType ConvertToUInt(ValueType value) {
    // TODO(bolms): This method assumes a few things that are not always
    // strictly true; e.g., that uint32_t and float have the same endianness.
    UIntType bits;
    memcpy(static_cast<void *>(&bits), static_cast<void *>(&value),
           sizeof bits);
    return bits;
  }

  BitViewType buffer_;
};

}  // namespace prelude
}  // namespace emboss

#endif  // EMBOSS_RUNTIME_CPP_EMBOSS_PRELUDE_H_
