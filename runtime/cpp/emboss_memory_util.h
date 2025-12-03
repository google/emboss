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

// Utilities for efficiently reading and writing to/from memory.
#ifndef EMBOSS_RUNTIME_CPP_EMBOSS_MEMORY_UTIL_H_
#define EMBOSS_RUNTIME_CPP_EMBOSS_MEMORY_UTIL_H_

#include <algorithm>
#include <cstddef>
#include <cstring>

#include "runtime/cpp/emboss_bit_util.h"
#include "runtime/cpp/emboss_cpp_types.h"
#include "runtime/cpp/emboss_defines.h"

namespace emboss {
namespace support {

// MemoryAccessor reads and writes big- and little-endian unsigned integers in
// and out of memory, using optimized routines where possible.
//
// The default MemoryAccessor just proxies to the MemoryAccessor with the
// next-smallest alignment and equivalent offset: MemoryAccessor<C, 8, 0, 32>
// and MemoryAccessor<C, 8, 4, 32> will proxy to MemoryAccessor<C, 4, 0, 32>,
// since an 8-byte-aligned pointer is also 4-byte-aligned, as is a pointer that
// is 4 bytes away from 8-byte alignment.
template <typename CharT, ::std::size_t kAlignment, ::std::size_t kOffset,
          ::std::size_t kBits>
struct MemoryAccessor {
  static_assert(IsPowerOfTwo(kAlignment),
                "MemoryAccessor requires power-of-two alignment.");
  static_assert(
      kOffset < kAlignment,
      "MemoryAccessor requires offset to be strictly less than alignment.");

  using ChainedAccessor =
      MemoryAccessor<CharT, kAlignment / 2, kOffset % (kAlignment / 2), kBits>;
  using Unsigned = typename LeastWidthInteger<kBits>::Unsigned;
  static inline Unsigned ReadLittleEndianUInt(const CharT *bytes) {
    return ChainedAccessor::ReadLittleEndianUInt(bytes);
  }
  static inline void WriteLittleEndianUInt(CharT *bytes, Unsigned value) {
    ChainedAccessor::WriteLittleEndianUInt(bytes, value);
  }
  static inline Unsigned ReadBigEndianUInt(const CharT *bytes) {
    return ChainedAccessor::ReadBigEndianUInt(bytes);
  }
  static inline void WriteBigEndianUInt(CharT *bytes, Unsigned value) {
    ChainedAccessor::WriteBigEndianUInt(bytes, value);
  }
};

// The least-aligned case for MemoryAccessor is 8-bit alignment, and the default
// version of MemoryAccessor will devolve to this one if there is no more
// specific override.
//
// If the system byte order is known, then these routines can use memcpy and
// (possibly) a byte swap; otherwise they can read individual bytes and
// shift+or them together in the appropriate order.  I (bolms@) haven't found a
// compiler that will optimize the multiple reads, shifts, and ors into a single
// read, so the memcpy version is *much* faster for 32-bit and larger reads.
template <typename CharT, ::std::size_t kBits>
struct MemoryAccessor<CharT, 1, 0, kBits> {
  static_assert(kBits % 8 == 0,
                "MemoryAccessor can only read and write whole-byte values.");
  static_assert(IsAliasSafe<CharT>::value,
                "MemoryAccessor can only be used on pointers to char types.");

  using Unsigned = typename LeastWidthInteger<kBits>::Unsigned;

#if defined(EMBOSS_LITTLE_ENDIAN_TO_NATIVE)
  static inline Unsigned ReadLittleEndianUInt(const CharT *bytes) {
    Unsigned result = 0;
    ::std::memcpy(&result, bytes, kBits / 8);
    return EMBOSS_LITTLE_ENDIAN_TO_NATIVE(result);
  }
#else
  static inline Unsigned ReadLittleEndianUInt(const CharT *bytes) {
    Unsigned result = 0;
    for (decltype(kBits) i = 0; i < kBits / 8; ++i) {
      result |=
          static_cast<Unsigned>(static_cast</**/ ::std::uint8_t>(bytes[i]))
          << i * 8;
    }
    return result;
  }
#endif

#if defined(EMBOSS_NATIVE_TO_LITTLE_ENDIAN)
  static inline void WriteLittleEndianUInt(CharT *bytes, Unsigned value) {
    value = EMBOSS_NATIVE_TO_LITTLE_ENDIAN(value);
    ::std::memcpy(bytes, &value, kBits / 8);
  }
#else
  static inline void WriteLittleEndianUInt(CharT *bytes, Unsigned value) {
    for (decltype(kBits) i = 0; i < kBits / 8; ++i) {
      bytes[i] = static_cast<CharT>(static_cast</**/ ::std::uint8_t>(value));
      if (sizeof value > 1) {
        // Shifting an 8-bit type by 8 bits is undefined behavior, so skip this
        // step for uint8_t.
        value >>= 8;
      }
    }
  }
#endif

#if defined(EMBOSS_BIG_ENDIAN_TO_NATIVE)
  static inline Unsigned ReadBigEndianUInt(const CharT *bytes) {
    Unsigned result = 0;
    // When a big-endian source integer is smaller than the result, the source
    // bytes must be copied into the final bytes of the destination.  This is
    // true whether the host is big- or little-endian.
    //
    // For a little-endian host:
    //
    // source (big-endian value 0x112233):
    //
    //   byte 0   byte 1   byte 2
    // +--------+--------+--------+
    // | 0x11   | 0x22   | 0x33   |
    // +--------+--------+--------+
    //
    // result after memcpy (host-interpreted value 0x33221100):
    //
    //   byte 0   byte 1   byte 2   byte 3
    // +--------+--------+--------+--------+
    // | 0x00   | 0x11   | 0x22   | 0x33   |
    // +--------+--------+--------+--------+
    //
    // result after 32-bit byte swap (host-interpreted value 0x112233):
    //
    //   byte 0   byte 1   byte 2   byte 3
    // +--------+--------+--------+--------+
    // | 0x33   | 0x22   | 0x11   | 0x00   |
    // +--------+--------+--------+--------+
    //
    // For a big-endian host:
    //
    // source (value 0x112233):
    //
    //   byte 0   byte 1   byte 2
    // +--------+--------+--------+
    // | 0x11   | 0x22   | 0x33   |
    // +--------+--------+--------+
    //
    // result after memcpy (value 0x112233) -- no byte swap needed:
    //
    //   byte 0   byte 1   byte 2   byte 3
    // +--------+--------+--------+--------+
    // | 0x00   | 0x11   | 0x22   | 0x33   |
    // +--------+--------+--------+--------+
    ::std::memcpy(reinterpret_cast<char *>(&result) + sizeof result - kBits / 8,
                  bytes, kBits / 8);
    result = EMBOSS_BIG_ENDIAN_TO_NATIVE(result);
    return result;
  }
#else
  static inline Unsigned ReadBigEndianUInt(const CharT *bytes) {
    Unsigned result = 0;
    for (decltype(kBits) i = 0; i < kBits / 8; ++i) {
      result |=
          static_cast<Unsigned>(static_cast</**/ ::std::uint8_t>(bytes[i]))
          << (kBits - 8 - i * 8);
    }
    return result;
  }
#endif

#if defined(EMBOSS_NATIVE_TO_BIG_ENDIAN)
  static inline void WriteBigEndianUInt(CharT *bytes, Unsigned value) {
    value = EMBOSS_NATIVE_TO_BIG_ENDIAN(value);
    ::std::memcpy(bytes,
                  reinterpret_cast<char *>(&value) + sizeof value - kBits / 8,
                  kBits / 8);
  }
#else
  static inline void WriteBigEndianUInt(CharT *bytes, Unsigned value) {
    for (decltype(kBits) i = 0; i < kBits / 8; ++i) {
      bytes[kBits / 8 - 1 - i] =
          static_cast<CharT>(static_cast</**/ ::std::uint8_t>(value));
      if (sizeof value > 1) {
        // Shifting an 8-bit type by 8 bits is undefined behavior, so skip this
        // step for uint8_t.
        value >>= 8;
      }
    }
  }
#endif
};

// Specialization of UIntMemoryAccessor for 16- 32- and 64-bit-aligned reads and
// writes, using EMBOSS_ALIAS_SAFE_POINTER_CAST instead of memcpy.
#if defined(EMBOSS_ALIAS_SAFE_POINTER_CAST) && \
    defined(EMBOSS_LITTLE_ENDIAN_TO_NATIVE) && \
    defined(EMBOSS_BIG_ENDIAN_TO_NATIVE) &&    \
    defined(EMBOSS_NATIVE_TO_LITTLE_ENDIAN) && \
    defined(EMBOSS_NATIVE_TO_BIG_ENDIAN)
template <typename CharT>
struct MemoryAccessor<CharT, 8, 0, 64> {
  static inline ::std::uint64_t ReadLittleEndianUInt(const CharT *bytes) {
    return EMBOSS_LITTLE_ENDIAN_TO_NATIVE(
        *EMBOSS_ALIAS_SAFE_POINTER_CAST(const ::std::uint64_t, bytes));
  }

  static inline void WriteLittleEndianUInt(CharT *bytes,
                                           ::std::uint64_t value) {
    *EMBOSS_ALIAS_SAFE_POINTER_CAST(::std::uint64_t, bytes) =
        EMBOSS_NATIVE_TO_LITTLE_ENDIAN(value);
  }

  static inline ::std::uint64_t ReadBigEndianUInt(const CharT *bytes) {
    return EMBOSS_BIG_ENDIAN_TO_NATIVE(
        *EMBOSS_ALIAS_SAFE_POINTER_CAST(const ::std::uint64_t, bytes));
  }

  static inline void WriteBigEndianUInt(CharT *bytes, ::std::uint64_t value) {
    *EMBOSS_ALIAS_SAFE_POINTER_CAST(::std::uint64_t, bytes) =
        EMBOSS_NATIVE_TO_BIG_ENDIAN(value);
  }
};

template <typename CharT>
struct MemoryAccessor<CharT, 4, 0, 32> {
  static inline ::std::uint32_t ReadLittleEndianUInt(const CharT *bytes) {
    return EMBOSS_LITTLE_ENDIAN_TO_NATIVE(
        *EMBOSS_ALIAS_SAFE_POINTER_CAST(const ::std::uint32_t, bytes));
  }

  static inline void WriteLittleEndianUInt(CharT *bytes,
                                           ::std::uint32_t value) {
    *EMBOSS_ALIAS_SAFE_POINTER_CAST(::std::uint32_t, bytes) =
        EMBOSS_NATIVE_TO_LITTLE_ENDIAN(value);
  }

  static inline ::std::uint32_t ReadBigEndianUInt(const CharT *bytes) {
    return EMBOSS_BIG_ENDIAN_TO_NATIVE(
        *EMBOSS_ALIAS_SAFE_POINTER_CAST(const ::std::uint32_t, bytes));
  }

  static inline void WriteBigEndianUInt(CharT *bytes, ::std::uint32_t value) {
    *EMBOSS_ALIAS_SAFE_POINTER_CAST(::std::uint32_t, bytes) =
        EMBOSS_NATIVE_TO_BIG_ENDIAN(value);
  }
};

template <typename CharT>
struct MemoryAccessor<CharT, 2, 0, 16> {
  static inline ::std::uint16_t ReadLittleEndianUInt(const CharT *bytes) {
    return EMBOSS_LITTLE_ENDIAN_TO_NATIVE(
        *EMBOSS_ALIAS_SAFE_POINTER_CAST(const ::std::uint16_t, bytes));
  }

  static inline void WriteLittleEndianUInt(CharT *bytes,
                                           ::std::uint16_t value) {
    *EMBOSS_ALIAS_SAFE_POINTER_CAST(::std::uint16_t, bytes) =
        EMBOSS_NATIVE_TO_LITTLE_ENDIAN(value);
  }

  static inline ::std::uint16_t ReadBigEndianUInt(const CharT *bytes) {
    return EMBOSS_BIG_ENDIAN_TO_NATIVE(
        *EMBOSS_ALIAS_SAFE_POINTER_CAST(const ::std::uint16_t, bytes));
  }

  static inline void WriteBigEndianUInt(CharT *bytes, ::std::uint16_t value) {
    *EMBOSS_ALIAS_SAFE_POINTER_CAST(::std::uint16_t, bytes) =
        EMBOSS_NATIVE_TO_BIG_ENDIAN(value);
  }
};
#endif  // defined(EMBOSS_ALIAS_SAFE_POINTER_CAST) &&
        // defined(EMBOSS_LITTLE_ENDIAN_TO_NATIVE) &&
        // defined(EMBOSS_BIG_ENDIAN_TO_NATIVE) &&
        // defined(EMBOSS_NATIVE_TO_LITTLE_ENDIAN) &&
        // defined(EMBOSS_NATIVE_TO_BIG_ENDIAN)

// This is the Euclidean GCD algorithm, in C++11-constexpr-safe form.  The
// initial is-b-greater-than-a-if-so-swap is omitted, since gcd(b % a, a) is the
// same as gcd(b, a) when a > b.
inline constexpr ::std::size_t GreatestCommonDivisor(::std::size_t a,
                                                     ::std::size_t b) {
  return a == 0 ? b : GreatestCommonDivisor(b % a, a);
}

// ContiguousBuffer is a direct view of a fixed number of contiguous bytes in
// memory.  If Byte is a const type, it will be a read-only view; if Byte is
// non-const, then writes will be allowed.
//
// The kAlignment and kOffset parameters are used to optimize certain reads and
// writes.  static_cast<uintptr_t>(bytes_) % kAlignment must equal kOffset.
//
// This class is used extensively by generated code, and is not intended to be
// heavily used by hand-written code -- some interfaces can be tricky to call
// correctly.
template <typename Byte, ::std::size_t kAlignment, ::std::size_t kOffset>
class ContiguousBuffer final {
  // There aren't many systems with non-8-bit chars, and a quirk of POSIX
  // requires that POSIX C systems have CHAR_BIT == 8, but some DSPs use wider
  // chars.
  static_assert(CHAR_BIT == 8, "ContiguousBuffer requires 8-bit chars.");

  // ContiguousBuffer assumes that its backing store is byte-oriented.  The
  // previous check ensures that chars are 8 bits, and this one ensures that the
  // backing store uses chars.
  //
  // Note that this check is explicitly that Byte is one of the three standard
  // char types, and not that (say) it is a one-byte type with an assignment
  // operator that can be static_cast<> to and from uint8_t.  I (bolms@) have
  // chosen to lock it down to just char types to avoid running afoul of strict
  // aliasing rules anywhere.
  //
  // Of somewhat academic interest, uint8_t is not required to be a char type
  // (https://gcc.gnu.org/bugzilla/show_bug.cgi?id=66110#c10), though it is
  // unlikely that any compiler vendor will actually change it, as there is
  // probably enough real-world code that relies on uint8_t being allowed to
  // alias.
  static_assert(IsAliasSafe<Byte>::value,
                "ContiguousBuffer requires char type.");

  // Because real-world processors only care about power-of-2 alignments,
  // ContiguousBuffer only supports power-of-2 alignments.  Note that
  // GetOffsetStorage can handle non-power-of-2 alignments.
  static_assert(IsPowerOfTwo(kAlignment),
                "ContiguousBuffer requires power-of-two alignment.");

  // To avoid template variant explosion, ContiguousBuffer requires kOffset to
  // be strictly less than kAlignment.  Users of ContiguousBuffer are expected
  // to take the modulus of kOffset by kAlignment before passing it in as a
  // parameter.
  static_assert(
      kOffset < kAlignment,
      "ContiguousBuffer requires offset to be strictly less than alignment.");

 public:
  using ByteType = Byte;
  // OffsetStorageType<kSubAlignment, kSubOffset> is the return type of
  // GetOffsetStorage<kSubAlignment, kSubOffset>(...).  This is used in a number
  // of places in generated code to specify deeply-nested template values.
  //
  // In theory, anything that cared about this type could use
  // decltype(declval(ContiguousBuffer<...>).GetOffsetStorage<kSubAlignment,
  // kSubOffset>(0, 0)) instead, but that is much more cumbersome, and it
  // appears that at least some versions of GCC do not handle it correctly.
  template </**/ ::std::size_t kSubAlignment, ::std::size_t kSubOffset>
  using OffsetStorageType =
      ContiguousBuffer<Byte, GreatestCommonDivisor(kAlignment, kSubAlignment),
                       (kOffset + kSubOffset) %
                           GreatestCommonDivisor(kAlignment, kSubAlignment)>;

  // Constructs a default ContiguousBuffer.
  ContiguousBuffer() : bytes_(nullptr), size_(0) {}

  // Constructs a ContiguousBuffer from a contiguous container type over some
  // `char` type, such as std::string, std::vector<signed char>,
  // std::array<unsigned char, N>, or std::string_view.
  //
  // This template is only enabled if:
  //
  // 1. bytes->data() returns a pointer to some char type.
  // 2. Byte is at least as cv-qualified as decltype(*bytes->data()).
  //
  // The first requirement means that this constructor won't work on, e.g.,
  // std::vector<int> -- this is mostly a precautionary measure, since
  // ContiguousBuffer only uses alias-safe operations anyway.
  //
  // The second requirement means that const and volatile are respected in the
  // expected way: a ContiguousBuffer<const unsigned char, ...> may be
  // initialized from std::vector<char>, but a ContiguousBuffer<unsigned char,
  // ...> may not be initialized from std::string_view.
  template <
      typename T,
      typename = typename ::std::enable_if<
          IsAliasSafe<typename ::std::remove_cv<
              typename ::std::remove_reference<decltype(*(
                  ::std::declval<T>().data()))>::type>::type>::value && ::std::
              is_same<typename AddSourceCV<
                          decltype(*::std::declval<T>().data()), Byte>::Type,
                      Byte>::value>::type>
  explicit ContiguousBuffer(T *bytes)
      : bytes_{reinterpret_cast<Byte *>(bytes->data())}, size_{bytes->size()} {
    if (bytes != nullptr)
      EMBOSS_DCHECK_POINTER_ALIGNMENT(bytes, kAlignment, kOffset);
  }

  // Constructs a ContiguousBuffer from a pointer to a char type and a size.  As
  // with the constructor from a container, above, Byte must be at least as
  // cv-qualified as T.
  template <typename T,
            typename = typename ::std::enable_if<
                IsAliasSafe<T>::value && ::std::is_same<
                    typename AddSourceCV<T, Byte>::Type, Byte>::value>>
  explicit ContiguousBuffer(T *bytes, ::std::size_t size)
      : bytes_{reinterpret_cast<Byte *>(bytes)},
        size_{bytes == nullptr ? 0 : size} {
    if (bytes != nullptr)
      EMBOSS_DCHECK_POINTER_ALIGNMENT(bytes, kAlignment, kOffset);
  }

  // Constructs a ContiguousBuffer from nullptr.  Equivalent to
  // ContiguousBuffer().
  //
  // TODO(bolms): Update callers and remove this constructor.
  explicit ContiguousBuffer(::std::nullptr_t) : bytes_{nullptr}, size_{0} {}

  // Implicitly construct or assign a ContiguousBuffer from a ContiguousBuffer.
#if !EMBOSS_GCC_BUG_115033
  ContiguousBuffer(const ContiguousBuffer &other) = default;
  ContiguousBuffer &operator=(const ContiguousBuffer &other) = default;
#else
  // See https://gcc.gnu.org/bugzilla/show_bug.cgi?id=115033 for details on the
  // bug (determined by bisecting GCC).
  // https://gcc.gnu.org/bugzilla/show_bug.cgi?id=114207 may also be relevant.
  //
  // A minimized example is available at https://godbolt.org/z/489z7z135
  //
  // It is not entirely clear how these definitions work around the GCC bug,
  // but they appear to.  One notable difference (and also the main reason that
  // we only use these definitions for affected versions of GCC) is that they
  // change the ABI of ContiguousBuffer, at least in the minimized case.
  ContiguousBuffer(const ContiguousBuffer &other)
      : bytes_{other.bytes_}, size_{other.size_} {}
  ContiguousBuffer &operator=(const ContiguousBuffer &other) {
    bytes_ = other.bytes_;
    size_ = other.size_;
    return *this;
  }
#endif

  // Explicitly construct a ContiguousBuffers from another, compatible
  // ContiguousBuffer.  A compatible ContiguousBuffer has an
  // equally-or-less-cv-qualified Byte type, an alignment that is an exact
  // multiple of this ContiguousBuffer's alignment, and an offset that is the
  // same when reduced to this ContiguousBuffer's alignment.
  //
  // The final !::std::is_same<...> clause prevents this constructor from
  // overlapping with the *implicit* copy constructor.
  template <
      typename OtherByte, ::std::size_t kOtherAlignment,
      ::std::size_t kOtherOffset,
      typename = typename ::std::enable_if<
          kOtherAlignment % kAlignment == 0 &&
          kOtherOffset % kAlignment ==
              kOffset && ::std::is_same<
                  typename AddSourceCV<OtherByte, Byte>::Type, Byte>::value &&
          !::std::is_same<ContiguousBuffer,
                          ContiguousBuffer<OtherByte, kOtherAlignment,
                                           kOtherOffset>>::value>::type>
  explicit ContiguousBuffer(
      const ContiguousBuffer<OtherByte, kOtherAlignment, kOtherOffset> &other)
      : bytes_{reinterpret_cast<Byte *>(other.data())},
        size_{other.SizeInBytes()} {}

  // Compare a ContiguousBuffers to another, compatible ContiguousBuffer.
  template <typename OtherByte, ::std::size_t kOtherAlignment,
            ::std::size_t kOtherOffset,
            typename = typename ::std::enable_if<
                kOtherAlignment % kAlignment == 0 &&
                kOtherOffset % kAlignment ==
                    kOffset && ::std::is_same<
                        typename AddSourceCV<OtherByte, Byte>::Type,
                        Byte>::value>::type>
  bool operator==(const ContiguousBuffer<OtherByte, kOtherAlignment,
                                         kOtherOffset> &other) const {
    return bytes_ == reinterpret_cast<Byte *>(other.data()) &&
           size_ == other.SizeInBytes();
  }

  // Compare a ContiguousBuffers to another, compatible ContiguousBuffer.
  template <typename OtherByte, ::std::size_t kOtherAlignment,
            ::std::size_t kOtherOffset,
            typename = typename ::std::enable_if<
                kOtherAlignment % kAlignment == 0 &&
                kOtherOffset % kAlignment ==
                    kOffset && ::std::is_same<
                        typename AddSourceCV<OtherByte, Byte>::Type,
                        Byte>::value>::type>
  bool operator!=(const ContiguousBuffer<OtherByte, kOtherAlignment,
                                         kOtherOffset> &other) const {
    return !(*this == other);
  }

  // Assignment from a compatible ContiguousBuffer.
  template <typename OtherByte, ::std::size_t kOtherAlignment,
            ::std::size_t kOtherOffset,
            typename = typename ::std::enable_if<
                kOtherAlignment % kAlignment == 0 &&
                kOtherOffset % kAlignment ==
                    kOffset && ::std::is_same<
                        typename AddSourceCV<OtherByte, Byte>::Type,
                        Byte>::value>::type>
  ContiguousBuffer &operator=(
      const ContiguousBuffer<OtherByte, kOtherAlignment, kOtherOffset> &other) {
    bytes_ = reinterpret_cast<Byte *>(other.data());
    size_ = other.SizeInBytes();
    return *this;
  }

  // GetOffsetStorage returns a new ContiguousBuffer that is a subsection of
  // this ContiguousBuffer, with appropriate alignment assertions.  The new
  // ContiguousBuffer will point to a region `offset` bytes into the original
  // ContiguousBuffer, with a size of `max(size, original_size - offset)`.
  //
  // The kSubAlignment and kSubOffset template parameters act as assertions
  // about the value of `offset`: `offset % (kSubAlignment / 8) - (kSubOffset /
  // 8)` must be zero.  That is, if `kSubAlignment` is 16 and `kSubOffset` is 8,
  // then `offset` may be 1, 3, 5, 7, etc.
  //
  // As a special case, if `kSubAlignment` is 0, then `offset` must exactly
  // equal `kSubOffset`.
  //
  // This method is used by generated structure views to get backing buffers for
  // views of their fields; the code generator can determine proper values for
  // `kSubAlignment` and `kSubOffset`.
  template </**/ ::std::size_t kSubAlignment, ::std::size_t kSubOffset>
  OffsetStorageType<kSubAlignment, kSubOffset> GetOffsetStorage(
      ::std::size_t offset, ::std::size_t size) const {
    static_assert(kSubAlignment == 0 || kSubAlignment > kSubOffset,
                  "kSubAlignment must be greater than kSubOffset.");
    // Emboss provides a fast, unchecked path for reads and writes like:
    //
    // view.field().subfield().UncheckedWrite().
    //
    // Each of .field() and .subfield() call GetOffsetStorage(), so
    // GetOffsetStorage() must be small and fast.
    if (kSubAlignment == 0) {
      EMBOSS_DCHECK_EQ(offset, kSubOffset);
    } else {
      // The weird ?:, below, silences -Werror=div-by-zero on versions of GCC
      // that aren't smart enough to figure out that kSubAlignment can't be zero
      // in this branch.
      EMBOSS_DCHECK_EQ(offset % (kSubAlignment == 0 ? 1 : kSubAlignment),
                       kSubOffset);
    }
    using ResultStorageType = OffsetStorageType<kSubAlignment, kSubOffset>;
    return bytes_ == nullptr
               ? ResultStorageType{nullptr}
               : ResultStorageType{
                     bytes_ + offset,
                     size_ < offset ? 0 : ::std::min(size, size_ - offset)};
  }

  // ReadLittleEndianUInt, ReadBigEndianUInt, and the unchecked versions thereof
  // provide efficient multibyte read access to the underlying buffer.  The
  // kBits template parameter should always equal the buffer size when these are
  // called.
  //
  // Generally, types other than unsigned integers can be relatively efficiently
  // converted from unsigned integers, and views should use Read...UInt to read
  // the raw value, then convert.
  //
  // Read...UInt always reads the entire buffer; to read a smaller section, use
  // GetOffsetStorage first.
  template </**/ ::std::size_t kBits>
  typename LeastWidthInteger<kBits>::Unsigned ReadLittleEndianUInt() const {
    EMBOSS_CHECK_EQ(SizeInBytes() * 8, kBits);
    EMBOSS_CHECK_POINTER_ALIGNMENT(bytes_, kAlignment, kOffset);
    return UncheckedReadLittleEndianUInt<kBits>();
  }
  template </**/ ::std::size_t kBits>
  typename LeastWidthInteger<kBits>::Unsigned UncheckedReadLittleEndianUInt()
      const {
    static_assert(kBits % 8 == 0,
                  "ContiguousBuffer::ReadLittleEndianUInt() can only read "
                  "whole-byte values.");
    return MemoryAccessor<Byte, kAlignment, kOffset,
                          kBits>::ReadLittleEndianUInt(bytes_);
  }
  template </**/ ::std::size_t kBits>
  typename LeastWidthInteger<kBits>::Unsigned ReadBigEndianUInt() const {
    EMBOSS_CHECK_EQ(SizeInBytes() * 8, kBits);
    EMBOSS_CHECK_POINTER_ALIGNMENT(bytes_, kAlignment, kOffset);
    return UncheckedReadBigEndianUInt<kBits>();
  }
  template </**/ ::std::size_t kBits>
  typename LeastWidthInteger<kBits>::Unsigned UncheckedReadBigEndianUInt()
      const {
    static_assert(kBits % 8 == 0,
                  "ContiguousBuffer::ReadBigEndianUInt() can only read "
                  "whole-byte values.");
    return MemoryAccessor<Byte, kAlignment, kOffset, kBits>::ReadBigEndianUInt(
        bytes_);
  }

  // WriteLittleEndianUInt, WriteBigEndianUInt, and the unchecked versions
  // thereof provide efficient write access to the buffer.  Similar to the Read
  // methods above, they write the entire buffer from an unsigned integer;
  // non-unsigned values should be converted to the equivalent bit pattern, then
  // written, and to write a subsection of the buffer use GetOffsetStorage
  // first.
  template </**/ ::std::size_t kBits>
  void WriteLittleEndianUInt(
      typename LeastWidthInteger<kBits>::Unsigned value) const {
    EMBOSS_CHECK_EQ(SizeInBytes() * 8, kBits);
    EMBOSS_CHECK_POINTER_ALIGNMENT(bytes_, kAlignment, kOffset);
    UncheckedWriteLittleEndianUInt<kBits>(value);
  }
  template </**/ ::std::size_t kBits>
  void UncheckedWriteLittleEndianUInt(
      typename LeastWidthInteger<kBits>::Unsigned value) const {
    static_assert(kBits % 8 == 0,
                  "ContiguousBuffer::WriteLittleEndianUInt() can only write "
                  "whole-byte values.");
    MemoryAccessor<Byte, kAlignment, kOffset, kBits>::WriteLittleEndianUInt(
        bytes_, value);
  }
  template </**/ ::std::size_t kBits>
  void WriteBigEndianUInt(
      typename LeastWidthInteger<kBits>::Unsigned value) const {
    EMBOSS_CHECK_EQ(SizeInBytes() * 8, kBits);
    EMBOSS_CHECK_POINTER_ALIGNMENT(bytes_, kAlignment, kOffset);
    return UncheckedWriteBigEndianUInt<kBits>(value);
  }
  template </**/ ::std::size_t kBits>
  void UncheckedWriteBigEndianUInt(
      typename LeastWidthInteger<kBits>::Unsigned value) const {
    static_assert(kBits % 8 == 0,
                  "ContiguousBuffer::WriteBigEndianUInt() can only write "
                  "whole-byte values.");
    MemoryAccessor<Byte, kAlignment, kOffset, kBits>::WriteBigEndianUInt(bytes_,
                                                                         value);
  }

  template <typename OtherByte, ::std::size_t kOtherAlignment,
            ::std::size_t kOtherOffset>
  void UncheckedCopyFrom(
      const ContiguousBuffer<OtherByte, kOtherAlignment, kOtherOffset> &other,
      ::std::size_t size) const {
    memmove(data(), other.data(), size);
  }
  template <typename OtherByte, ::std::size_t kOtherAlignment,
            ::std::size_t kOtherOffset>
  void CopyFrom(
      const ContiguousBuffer<OtherByte, kOtherAlignment, kOtherOffset> &other,
      ::std::size_t size) const {
    EMBOSS_CHECK(Ok());
    EMBOSS_CHECK(other.Ok());
    // It is OK if either buffer contains extra bytes that are not being copied.
    EMBOSS_CHECK_GE(SizeInBytes(), size);
    EMBOSS_CHECK_GE(other.SizeInBytes(), size);
    UncheckedCopyFrom(other, size);
  }
  template <typename OtherByte, ::std::size_t kOtherAlignment,
            ::std::size_t kOtherOffset>
  bool TryToCopyFrom(
      const ContiguousBuffer<OtherByte, kOtherAlignment, kOtherOffset> &other,
      ::std::size_t size) const {
    if (Ok() && other.Ok() && SizeInBytes() >= size &&
        other.SizeInBytes() >= size) {
      UncheckedCopyFrom(other, size);
      return true;
    }
    return false;
  }
  ::std::size_t SizeInBytes() const { return size_; }
  bool Ok() const { return bytes_ != nullptr; }
  Byte *data() const { return bytes_; }
  Byte *begin() const { return bytes_; }
  Byte *end() const { return bytes_ + size_; }

  // Constructs a string type from the underlying data; mostly intended to be
  // called as:
  //
  //     buffer.ToString<std::string>();
  //
  // or:
  //
  //     buffer.ToString<std::string_view>();
  //
  // ... but it should also work with any similar-enough classes, such as
  // std::basic_string_view<unsigned char> or Google's absl::string_view.
  //
  // Note that this may or may not make a copy of the underlying data,
  // depending on the behavior of the given string type.
  template <typename String>
  typename ::std::enable_if<
      IsAliasSafe<typename ::std::remove_reference<
          decltype(*::std::declval<String>().data())>::type>::value,
      String>::type
  ToString() const {
    return String(
        reinterpret_cast<
            const typename ::std::remove_reference<typename ::std::remove_cv<
                decltype(*::std::declval<String>().data())>::type>::type *>(
            bytes_),
        size_);
  }

 private:
  Byte *bytes_ = nullptr;
  ::std::size_t size_ = 0;
};

// TODO(bolms): Remove these aliases.
using ReadWriteContiguousBuffer = ContiguousBuffer<unsigned char, 1, 0>;
using ReadOnlyContiguousBuffer = ContiguousBuffer<const unsigned char, 1, 0>;

// LittleEndianByteOrderer is a pass-through adapter for a byte buffer class.
// It is used to implement little-endian bit blocks.
//
// When used by BitBlock, the resulting bits are numbered as if they are
// little-endian:
//
//                      bit addresses of each bit in each byte
//           +----+----+----+----+----+----+----+----+----+----+----+----+----
// bit in  7 |  7 | 15 | 23 | 31 | 39 | 47 | 55 | 63 | 71 | 79 | 87 | 95 |
// byte    6 |  6 | 14 | 22 | 30 | 38 | 46 | 54 | 62 | 70 | 78 | 86 | 94 |
//         5 |  5 | 13 | 21 | 29 | 37 | 45 | 53 | 61 | 69 | 77 | 85 | 93 |
//         4 |  4 | 12 | 20 | 28 | 36 | 44 | 52 | 60 | 68 | 76 | 84 | 92 |
//         3 |  3 | 11 | 19 | 27 | 35 | 43 | 51 | 59 | 67 | 75 | 83 | 91 | ...
//         2 |  2 | 10 | 18 | 26 | 34 | 42 | 50 | 58 | 66 | 74 | 82 | 90 |
//         1 |  1 |  9 | 17 | 25 | 33 | 41 | 49 | 57 | 65 | 73 | 81 | 89 |
//         0 |  0 |  8 | 16 | 24 | 32 | 40 | 48 | 56 | 64 | 72 | 80 | 88 |
//           +----+----+----+----+----+----+----+----+----+----+----+----+----
//              0    1    2    3    4    5    6    7    8    9   10   11   ...
//                                  byte address
//
// Because endian-specific reads and writes are handled in ContiguousBuffer,
// this class exists mostly to translate VerbUInt calls to VerbLittleEndianUInt.
template <class BufferT>
class LittleEndianByteOrderer final {
 public:
  // Type declaration so that BitBlock can use BufferType::BufferType.
  using BufferType = BufferT;

  LittleEndianByteOrderer() : buffer_() {}
  explicit LittleEndianByteOrderer(BufferType buffer) : buffer_{buffer} {}
  LittleEndianByteOrderer(const LittleEndianByteOrderer &other) = default;
  LittleEndianByteOrderer(LittleEndianByteOrderer &&other) = default;
  LittleEndianByteOrderer &operator=(const LittleEndianByteOrderer &other) =
      default;

  // LittleEndianByteOrderer just passes straight through to the underlying
  // buffer.
  bool Ok() const { return buffer_.Ok(); }
  ::std::size_t SizeInBytes() const { return buffer_.SizeInBytes(); }

  template </**/ ::std::size_t kBits>
  typename LeastWidthInteger<kBits>::Unsigned ReadUInt() const {
    return buffer_.template ReadLittleEndianUInt<kBits>();
  }
  template </**/ ::std::size_t kBits>
  typename LeastWidthInteger<kBits>::Unsigned UncheckedReadUInt() const {
    return buffer_.template UncheckedReadLittleEndianUInt<kBits>();
  }
  template </**/ ::std::size_t kBits>
  void WriteUInt(typename LeastWidthInteger<kBits>::Unsigned value) const {
    buffer_.template WriteLittleEndianUInt<kBits>(value);
  }
  template </**/ ::std::size_t kBits>
  void UncheckedWriteUInt(
      typename LeastWidthInteger<kBits>::Unsigned value) const {
    buffer_.template UncheckedWriteLittleEndianUInt<kBits>(value);
  }

 private:
  BufferType buffer_;
};

// BigEndianByteOrderer is an adapter for a byte buffer class which reverses
// the addresses of the underlying byte buffer.  It is used to implement
// big-endian bit blocks.
//
// When used by BitBlock, the resulting bits are numbered with "bit 0" as the
// lowest-order bit of the *last* byte in the buffer.  For example, for a
// 12-byte buffer, the bit ordering looks like:
//
//                      bit addresses of each bit in each byte
//           +----+----+----+----+----+----+----+----+----+----+----+----+
// bit in  7 | 95 | 87 | 79 | 71 | 63 | 55 | 47 | 39 | 31 | 23 | 15 |  7 |
// byte    6 | 94 | 86 | 78 | 70 | 62 | 54 | 46 | 38 | 30 | 22 | 14 |  6 |
//         5 | 93 | 85 | 77 | 69 | 61 | 53 | 45 | 37 | 29 | 21 | 13 |  5 |
//         4 | 92 | 84 | 76 | 68 | 60 | 52 | 44 | 36 | 28 | 20 | 12 |  4 |
//         3 | 91 | 83 | 75 | 67 | 59 | 51 | 43 | 35 | 27 | 19 | 11 |  3 |
//         2 | 90 | 82 | 74 | 66 | 58 | 50 | 42 | 34 | 26 | 18 | 10 |  2 |
//         1 | 89 | 81 | 73 | 65 | 57 | 49 | 41 | 33 | 25 | 17 |  9 |  1 |
//         0 | 88 | 80 | 72 | 64 | 56 | 48 | 40 | 32 | 24 | 16 |  8 |  0 |
//           +----+----+----+----+----+----+----+----+----+----+----+----+
//              0    1    2    3    4    5    6    7    8    9   10   11
//                                  byte address
//
// Note that some big-endian protocols are documented with "bit 0" being the
// *high-order* bit of a number, in which case "bit 0" would be the
// highest-order bit of the first byte in the buffer.  The "bit 0 is the
// high-order bit" style seems to be more common in older documents (e.g., RFCs
// 791 and 793, for IP and TCP), while the Emboss-style "bit 0 is in the last
// byte" seems to be more common in newer documents (e.g., the hardware user
// manuals bolms@ examined).
// TODO(bolms): Examine more documents to see if the old vs new pattern holds.
//
// Because endian-specific reads and writes are handled in ContiguousBuffer,
// this class exists mostly to translate VerbUInt calls to VerbBigEndianUInt.
template <class BufferT>
class BigEndianByteOrderer final {
 public:
  // Type declaration so that BitBlock can use BufferType::BufferType.
  using BufferType = BufferT;

  BigEndianByteOrderer() : buffer_() {}
  explicit BigEndianByteOrderer(BufferType buffer) : buffer_{buffer} {}
  BigEndianByteOrderer(const BigEndianByteOrderer &other) = default;
  BigEndianByteOrderer(BigEndianByteOrderer &&other) = default;
  BigEndianByteOrderer &operator=(const BigEndianByteOrderer &other) = default;

  // Ok() and SizeInBytes() get passed through with no changes.
  bool Ok() const { return buffer_.Ok(); }
  ::std::size_t SizeInBytes() const { return buffer_.SizeInBytes(); }

  template </**/ ::std::size_t kBits>
  typename LeastWidthInteger<kBits>::Unsigned ReadUInt() const {
    return buffer_.template ReadBigEndianUInt<kBits>();
  }
  template </**/ ::std::size_t kBits>
  typename LeastWidthInteger<kBits>::Unsigned UncheckedReadUInt() const {
    return buffer_.template UncheckedReadBigEndianUInt<kBits>();
  }
  template </**/ ::std::size_t kBits>
  void WriteUInt(typename LeastWidthInteger<kBits>::Unsigned value) const {
    buffer_.template WriteBigEndianUInt<kBits>(value);
  }
  template </**/ ::std::size_t kBits>
  void UncheckedWriteUInt(
      typename LeastWidthInteger<kBits>::Unsigned value) const {
    buffer_.template UncheckedWriteBigEndianUInt<kBits>(value);
  }

 private:
  BufferType buffer_;
};

// NullByteOrderer is a pass-through adapter for a byte buffer class.  It is
// used to implement single-byte bit blocks, where byte order does not matter.
//
// Technically, it should be valid to swap in BigEndianByteOrderer or
// LittleEndianByteOrderer anywhere that NullByteOrderer is used, but
// NullByteOrderer contains a few extra CHECKs to ensure it is being used
// correctly.
template <class BufferT>
class NullByteOrderer final {
 public:
  // Type declaration so that BitBlock can use BufferType::BufferType.
  using BufferType = BufferT;

  NullByteOrderer() : buffer_() {}
  explicit NullByteOrderer(BufferType buffer) : buffer_{buffer} {}
  NullByteOrderer(const NullByteOrderer &other) = default;
  NullByteOrderer(NullByteOrderer &&other) = default;
  NullByteOrderer &operator=(const NullByteOrderer &other) = default;

  bool Ok() const { return buffer_.Ok(); }
  ::std::size_t SizeInBytes() const { return Ok() ? 1 : 0; }

  template </**/ ::std::size_t kBits>
  typename LeastWidthInteger<kBits>::Unsigned ReadUInt() const {
    static_assert(kBits == 8, "NullByteOrderer may only read 8-bit values.");
    return buffer_.template ReadLittleEndianUInt<kBits>();
  }
  template </**/ ::std::size_t kBits>
  typename LeastWidthInteger<kBits>::Unsigned UncheckedReadUInt() const {
    static_assert(kBits == 8, "NullByteOrderer may only read 8-bit values.");
    return buffer_.template UncheckedReadLittleEndianUInt<kBits>();
  }
  template </**/ ::std::size_t kBits>
  void WriteUInt(typename LeastWidthInteger<kBits>::Unsigned value) const {
    static_assert(kBits == 8, "NullByteOrderer may only read 8-bit values.");
    buffer_.template WriteBigEndianUInt<kBits>(value);
  }
  template </**/ ::std::size_t kBits>
  void UncheckedWriteUInt(
      typename LeastWidthInteger<kBits>::Unsigned value) const {
    static_assert(kBits == 8, "NullByteOrderer may only read 8-bit values.");
    buffer_.template UncheckedWriteBigEndianUInt<kBits>(value);
  }

 private:
  BufferType buffer_;
};

// OffsetBitBlock is a filter on another BitBlock class, which adds a fixed
// offset to reads from underlying bit block.  This is used by Emboss generated
// classes to read bitfields: the parent provides an OffsetBitBlock of its
// buffer to the child's view.
//
// OffsetBitBlock is always statically sized, but because
// BitBlock::GetOffsetStorage and OffsetBitBlock::GetOffsetStorage must have the
// same signature as ContiguousBuffer::GetOffsetStorage, OffsetBitBlock's size
// parameter must be a runtime value.
//
// TODO(bolms): Figure out how to add size as a template parameter to
// OffsetBitBlock.
template <class UnderlyingBitBlockType>
class OffsetBitBlock final {
 public:
  using ValueType = typename UnderlyingBitBlockType::ValueType;
  // Bit blocks do not use alignment information, but generated code expects bit
  // blocks to have the same methods and types as byte blocks, so even though
  // kNewAlignment and kNewOffset are unused, they must be present as template
  // parameters.
  template </**/ ::std::size_t kNewAlignment, ::std::size_t kNewOffset>
  using OffsetStorageType = OffsetBitBlock<UnderlyingBitBlockType>;

  OffsetBitBlock() : bit_block_(), offset_(0), size_(0), ok_(false) {}
  explicit OffsetBitBlock(UnderlyingBitBlockType bit_block,
                          ::std::size_t offset, ::std::size_t size, bool ok)
      : bit_block_{bit_block},
        offset_{static_cast</**/ ::std::uint8_t>(offset)},
        size_{static_cast</**/ ::std::uint8_t>(size)},
        ok_{offset == offset_ && size == size_ && ok} {}
  OffsetBitBlock(const OffsetBitBlock &other) = default;
  OffsetBitBlock &operator=(const OffsetBitBlock &other) = default;

  template </**/ ::std::size_t kNewAlignment, ::std::size_t kNewOffset>
  OffsetStorageType<kNewAlignment, kNewOffset> GetOffsetStorage(
      ::std::size_t offset, ::std::size_t size) const {
    return OffsetStorageType<kNewAlignment, kNewOffset>{
        bit_block_, offset_ + offset, size, ok_ && offset + size <= size_};
  }

  // ReadUInt reads the entire underlying bit block, then shifts and masks to
  // the appropriate size.
  ValueType ReadUInt() const {
    EMBOSS_CHECK_GE(bit_block_.SizeInBits(), offset_ + size_);
    EMBOSS_CHECK_GE(bit_block_.SizeInBits(),
                    static_cast</**/ ::std::uint64_t>(offset_ + size_));
    EMBOSS_CHECK(Ok());
    return MaskToNBits(bit_block_.ReadUInt(), offset_ + size_) >> offset_;
  }
  ValueType UncheckedReadUInt() const {
    return MaskToNBits(bit_block_.UncheckedReadUInt(), offset_ + size_) >>
           offset_;
  }

  // WriteUInt writes the entire underlying bit block; in order to only write
  // the specific bits that should be changed, the current value is first read,
  // then masked out and or'ed with the new value, and finally the result is
  // written back to memory.
  void WriteUInt(ValueType value) const {
    EMBOSS_CHECK_EQ(value, MaskToNBits(value, size_));
    EMBOSS_CHECK(Ok());
    // OffsetBitBlock::WriteUInt *always* does a read-modify-write because it is
    // assumed that if the user wanted to read or write the entire value they
    // would just use the underlying BitBlock directly.  This is mostly true for
    // code generated by Emboss, which only uses OffsetBitBlock for subfields of
    // `bits` types; bit-oriented types such as `UInt` will use BitBlock
    // directly when they are placed directly in a `struct`.
    bit_block_.WriteUInt(MaskInValue(bit_block_.ReadUInt(), value));
  }
  void UncheckedWriteUInt(ValueType value) const {
    bit_block_.UncheckedWriteUInt(
        MaskInValue(bit_block_.UncheckedReadUInt(), value));
  }

  ::std::size_t SizeInBits() const { return size_; }
  bool Ok() const { return ok_; }

 private:
  ValueType MaskInValue(ValueType original_value, ValueType new_value) const {
    ValueType original_mask = static_cast<ValueType>(~(
        MaskToNBits(static_cast<ValueType>(~ValueType{0}), size_) << offset_));
    return static_cast<ValueType>((original_value & original_mask) |
                                  (new_value << offset_));
  }

  const UnderlyingBitBlockType bit_block_;
  const ::std::uint8_t offset_;
  const ::std::uint8_t size_;
  const ::std::uint8_t ok_;
};

// BitBlock is a view of a short, fixed-size sequence of bits somewhere in
// memory.  Big- and little-endian values are handled by BufferType, which is
// typically BigEndianByteOrderer<ContiguousBuffer<...>> or
// LittleEndianByteOrderer<ContiguousBuffer<...>>.
//
// BitBlock is implemented such that it always reads and writes its entire
// buffer; unlike ContiguousBuffer for bytes, there is no way to modify part of
// the underlying data without doing a read-modify-write of the full value.
// This sidesteps a lot of weirdness with converting between bit addresses and
// byte addresses for big-endian values, though it does mean that in certain
// cases excess bits will be read or written, particularly if care is not taken
// in the .emb definition to keep `bits` types to a minimum size.
template <class BufferType, ::std::size_t kBufferSizeInBits>
class BitBlock final {
  static_assert(kBufferSizeInBits % 8 == 0,
                "BitBlock can only operate on byte buffers.");
#if EMBOSS_HAS_INT128
  static_assert(kBufferSizeInBits <= 128,
                "BitBlock can only operate on buffers up to 128 bits.");
#else
  static_assert(kBufferSizeInBits <= 64,
                "BitBlock can only operate on small buffers.");
#endif  // EMBOSS_HAS_INT128

 public:
  using ValueType = typename LeastWidthInteger<kBufferSizeInBits>::Unsigned;
  // As with OffsetBitBlock::OffsetStorageType, the kNewAlignment and kNewOffset
  // values are not used, but they must be template parameters so that generated
  // code can work with both BitBlock and ContiguousBuffer.
  template </**/ ::std::size_t kNewAlignment, ::std::size_t kNewOffset>
  using OffsetStorageType =
      OffsetBitBlock<BitBlock<BufferType, kBufferSizeInBits>>;

  explicit BitBlock() : buffer_() {}
  explicit BitBlock(BufferType buffer) : buffer_{buffer} {}
  explicit BitBlock(typename BufferType::BufferType buffer) : buffer_{buffer} {}
  BitBlock(const BitBlock &) = default;
  BitBlock(BitBlock &&) = default;
  BitBlock &operator=(const BitBlock &) = default;
  BitBlock &operator=(BitBlock &&) = default;
  ~BitBlock() = default;

  static constexpr ::std::size_t Bits() { return kBufferSizeInBits; }

  template </**/ ::std::size_t kNewAlignment, ::std::size_t kNewOffset>
  OffsetStorageType<kNewAlignment, kNewOffset> GetOffsetStorage(
      ::std::size_t offset, ::std::size_t size) const {
    return OffsetStorageType<kNewAlignment, kNewOffset>{
        *this, offset, size, Ok() && offset + size <= kBufferSizeInBits};
  }

  // BitBlock clients must read or write the entire BitBlock value as an
  // unsigned integer.  OffsetBitBlock can be used to extract a portion of the
  // value via shift and mask, and individual view types such as IntView or
  // BcdView are expected to convert ValueType to/from their desired types.
  ValueType ReadUInt() const {
    return buffer_.template ReadUInt<kBufferSizeInBits>();
  }
  ValueType UncheckedReadUInt() const {
    return buffer_.template UncheckedReadUInt<kBufferSizeInBits>();
  }
  void WriteUInt(ValueType value) const {
    EMBOSS_CHECK_EQ(value, MaskToNBits(value, kBufferSizeInBits));
    buffer_.template WriteUInt<kBufferSizeInBits>(value);
  }
  void UncheckedWriteUInt(ValueType value) const {
    buffer_.template UncheckedWriteUInt<kBufferSizeInBits>(value);
  }

  ::std::size_t SizeInBits() const { return kBufferSizeInBits; }
  bool Ok() const {
    return buffer_.Ok() && buffer_.SizeInBytes() * 8 == kBufferSizeInBits;
  }

 private:
  BufferType buffer_;
};

}  // namespace support
}  // namespace emboss

#endif  // EMBOSS_RUNTIME_CPP_EMBOSS_MEMORY_UTIL_H_
