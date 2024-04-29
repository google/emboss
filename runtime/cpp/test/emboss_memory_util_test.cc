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

#include <array>
#include <string>
#if __cplusplus >= 201703L
#include <cstddef>  // std::byte
#include <string_view>
#endif  // __cplusplus >= 201703L
#include <vector>

#include "gtest/gtest.h"
#include "runtime/cpp/emboss_memory_util.h"
#include "runtime/cpp/emboss_prelude.h"

namespace emboss {
namespace support {
namespace test {

using ::emboss::prelude::IntView;
using ::emboss::prelude::UIntView;

template </**/ ::std::size_t kBits>
using BigEndianBitBlockN =
    BitBlock<BigEndianByteOrderer<ReadWriteContiguousBuffer>, kBits>;

template </**/ ::std::size_t kBits>
using LittleEndianBitBlockN =
    BitBlock<LittleEndianByteOrderer<ReadWriteContiguousBuffer>, kBits>;

template <typename T, typename... Args>
std::array<T, sizeof...(Args)> constexpr init_array(Args &&...args) {
  return {T(std::forward<Args>(args))...};
}

template <typename Container, typename... Args>
auto constexpr init_container(Args &&...args) -> Container {
  using CharType =
      typename ::std::remove_reference<decltype(*Container().data())>::type;
  return {CharType(std::forward<Args>(args))...};
}

TEST(GreatestCommonDivisor, GreatestCommonDivisor) {
  EXPECT_EQ(4U, GreatestCommonDivisor(12, 20));
  EXPECT_EQ(4U, GreatestCommonDivisor(20, 12));
  EXPECT_EQ(4U, GreatestCommonDivisor(20, 4));
  EXPECT_EQ(6U, GreatestCommonDivisor(12, 78));
  EXPECT_EQ(6U, GreatestCommonDivisor(6, 0));
  EXPECT_EQ(6U, GreatestCommonDivisor(0, 6));
  EXPECT_EQ(3U, GreatestCommonDivisor(9, 6));
  EXPECT_EQ(0U, GreatestCommonDivisor(0, 0));
}

// Because MemoryAccessor's parameters are template parameters, it is not
// possible to loop through them directly.  Instead, TestMemoryAccessor tests
// a particular MemoryAccessor's methods, then calls the next template to test
// the next set of template parameters to MemoryAccessor.
template <typename CharT, ::std::size_t kAlignment, ::std::size_t kOffset,
          ::std::size_t kBits>
void TestMemoryAccessor() {
  alignas(kAlignment) auto bytes =
      init_array<CharT>(0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08);
  EXPECT_EQ(
      0x0807060504030201UL & (~0x0UL >> (64 - kBits)),
      (MemoryAccessor<CharT, kAlignment, kOffset, kBits>::ReadLittleEndianUInt(
          bytes.data())))
      << "kAlignment = " << kAlignment << "; kOffset = " << kOffset
      << "; kBits = " << kBits;
  EXPECT_EQ(
      0x0102030405060708UL >> (64 - kBits),
      (MemoryAccessor<CharT, kAlignment, kOffset, kBits>::ReadBigEndianUInt(
          bytes.data())))
      << "kAlignment = " << kAlignment << "; kOffset = " << kOffset
      << "; kBits = " << kBits;

  MemoryAccessor<CharT, kAlignment, kOffset, kBits>::WriteLittleEndianUInt(
      bytes.data(), 0x7172737475767778UL & (~0x0UL >> (64 - kBits)));
  auto expected_vector_after_write = init_container<std::vector<CharT>>(
      0x78, 0x77, 0x76, 0x75, 0x74, 0x73, 0x72, 0x71);
  for (int i = kBits / 8; i < 8; ++i) {
    expected_vector_after_write[i] = CharT(i + 1);
  }
  EXPECT_EQ(expected_vector_after_write,
            ::std::vector<CharT>(std::begin(bytes), std::end(bytes)))
      << "kAlignment = " << kAlignment << "; kOffset = " << kOffset
      << "; kBits = " << kBits;

  MemoryAccessor<CharT, kAlignment, kOffset, kBits>::WriteBigEndianUInt(
      bytes.data(), 0x7172737475767778UL >> (64 - kBits));
  expected_vector_after_write = init_container<std::vector<CharT>>(
      0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78);
  for (int i = kBits / 8; i < 8; ++i) {
    expected_vector_after_write[i] = CharT(i + 1);
  }
  EXPECT_EQ(expected_vector_after_write,
            ::std::vector<CharT>(std::begin(bytes), std::end(bytes)))
      << "kAlignment = " << kAlignment << "; kOffset = " << kOffset
      << "; kBits = " << kBits;

  // Recursively iterate the template:
  //
  // For every kAlignment/kOffset pair, check kBits from 64 to 8 in increments
  // of 8.
  //
  // If kBits is 8, reset kBits to 64 and go to the next kAlignment/kOffset
  // pair.
  //
  // For each kAlignment, try all kOffsets from 0 to kAlignment - 1.
  //
  // If kBits is 8 and kOffset is kAlignment - 1, reset kBits to 64, kOffset to
  // 0, and halve kAlignment.
  //
  // Base cases below handle kAlignment == 0, terminating the recursion.
  TestMemoryAccessor<
      CharT,
      kBits == 8 && kAlignment == kOffset + 1 ? kAlignment / 2 : kAlignment,
      kBits == 8 ? kAlignment == kOffset + 1 ? 0 : kOffset + 1 : kOffset,
      kBits == 8 ? 64 : kBits - 8>();
}

template <>
void TestMemoryAccessor<char, 0, 0, 64>() {}

#if __cplusplus >= 201703L
template <>
void TestMemoryAccessor<std::byte, 0, 0, 64>() {}
#endif

template <>
void TestMemoryAccessor<unsigned char, 0, 0, 64>() {}

TEST(MemoryAccessor, LittleEndianReads) {
  TestMemoryAccessor<char, 8, 0, 64>();
#if __cplusplus >= 201703L
  TestMemoryAccessor<std::byte, 8, 0, 64>();
#endif
  TestMemoryAccessor<unsigned char, 8, 0, 64>();
}

TEST(ContiguousBuffer, OffsetStorageType) {
  EXPECT_TRUE((::std::is_same<
               ContiguousBuffer<char, 2, 0>,
               ContiguousBuffer<char, 2, 0>::OffsetStorageType<2, 0>>::value));
  EXPECT_TRUE((::std::is_same<
               ContiguousBuffer<char, 2, 0>,
               ContiguousBuffer<char, 2, 0>::OffsetStorageType<0, 0>>::value));
  EXPECT_TRUE((::std::is_same<
               ContiguousBuffer<char, 2, 0>,
               ContiguousBuffer<char, 2, 0>::OffsetStorageType<4, 0>>::value));
  EXPECT_TRUE((::std::is_same<
               ContiguousBuffer<char, 2, 0>,
               ContiguousBuffer<char, 4, 0>::OffsetStorageType<2, 0>>::value));
  EXPECT_TRUE((::std::is_same<
               ContiguousBuffer<char, 2, 0>,
               ContiguousBuffer<char, 4, 2>::OffsetStorageType<2, 0>>::value));
  EXPECT_TRUE((::std::is_same<
               ContiguousBuffer<char, 2, 0>,
               ContiguousBuffer<char, 4, 1>::OffsetStorageType<2, 1>>::value));
  EXPECT_TRUE((::std::is_same<
               ContiguousBuffer<char, 4, 2>,
               ContiguousBuffer<char, 4, 1>::OffsetStorageType<4, 1>>::value));
  EXPECT_TRUE((::std::is_same<
               ContiguousBuffer<char, 4, 1>,
               ContiguousBuffer<char, 4, 3>::OffsetStorageType<0, 2>>::value));
  EXPECT_TRUE((::std::is_same<
               ContiguousBuffer<char, 4, 1>,
               ContiguousBuffer<char, 4, 3>::OffsetStorageType<4, 2>>::value));
  EXPECT_TRUE((::std::is_same<
               ContiguousBuffer<char, 4, 1>,
               ContiguousBuffer<char, 4, 3>::OffsetStorageType<8, 6>>::value));
  EXPECT_TRUE((::std::is_same<
               ContiguousBuffer<char, 4, 1>,
               ContiguousBuffer<char, 4, 3>::OffsetStorageType<12, 6>>::value));
  EXPECT_TRUE((::std::is_same<
               ContiguousBuffer<char, 1, 0>,
               ContiguousBuffer<char, 4, 1>::OffsetStorageType<3, 1>>::value));
}

// Minimal class that forwards to std::allocator.  Used to test that
// ReadOnlyContiguousBuffer can be constructed from std::vector<> and
// std::basic_string<> with non-default trailing template parameters.
template <class T>
struct NonstandardAllocator {
  using value_type =
      typename ::std::allocator_traits<::std::allocator<T>>::value_type;
  using pointer =
      typename ::std::allocator_traits<::std::allocator<T>>::pointer;
  using const_pointer =
      typename ::std::allocator_traits<::std::allocator<T>>::const_pointer;
  using reference = typename ::std::allocator<T>::value_type &;
  using const_reference =
      const typename ::std::allocator_traits<::std::allocator<T>>::value_type &;
  using size_type =
      typename ::std::allocator_traits<::std::allocator<T>>::size_type;
  using difference_type =
      typename ::std::allocator_traits<::std::allocator<T>>::difference_type;

  template <class U>
  struct rebind {
    using other = NonstandardAllocator<U>;
  };

  NonstandardAllocator() = default;
  // This constructor is *not* explicit in order to conform to the requirements
  // for an allocator.
  template <class U>
  NonstandardAllocator(const NonstandardAllocator<U> &) {}  // NOLINT

  T *allocate(::std::size_t n) { return ::std::allocator<T>().allocate(n); }
  void deallocate(T *p, ::std::size_t n) {
    ::std::allocator<T>().deallocate(p, n);
  }

  static size_type max_size() {
    return ::std::numeric_limits<size_type>::max() / sizeof(value_type);
  }
};

template <class T, class U>
bool operator==(const NonstandardAllocator<T> &,
                const NonstandardAllocator<U> &) {
  return true;
}

template <class T, class U>
bool operator!=(const NonstandardAllocator<T> &,
                const NonstandardAllocator<U> &) {
  return false;
}

// ContiguousBuffer tests for std::vector, std::array, and std::string types.
template <typename T>
class ReadOnlyContiguousBufferTest : public ::testing::Test {};
typedef ::testing::Types<
    /**/ ::std::vector<char>, ::std::array<char, 8>,
    ::std::vector<unsigned char>,
#if __cplusplus >= 201703L
    ::std::vector<std::byte>,
#endif
    ::std::string, ::std::basic_string<char>,
    ::std::vector<unsigned char, NonstandardAllocator<unsigned char>>,
    ::std::basic_string<char, ::std::char_traits<char>,
                        NonstandardAllocator<char>>>
    ReadOnlyContiguousContainerTypes;
TYPED_TEST_SUITE(ReadOnlyContiguousBufferTest,
                 ReadOnlyContiguousContainerTypes);

TYPED_TEST(ReadOnlyContiguousBufferTest, ConstructionFromContainers) {
  const TypeParam bytes =
      init_container<TypeParam>(0x08, 0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01);
  using CharType =
      typename ::std::remove_reference<decltype(*bytes.data())>::type;
  const auto buffer = ContiguousBuffer<const CharType, 1, 0>{&bytes};
  EXPECT_EQ(bytes.size(), buffer.SizeInBytes());
  EXPECT_TRUE(buffer.Ok());
  EXPECT_EQ(0x0807060504030201UL, buffer.template ReadBigEndianUInt<64>());

  const auto offset_buffer = buffer.template GetOffsetStorage<1, 0>(4, 4);
  EXPECT_EQ(4U, offset_buffer.SizeInBytes());
  EXPECT_EQ(0x04030201U, offset_buffer.template ReadBigEndianUInt<32>());

  // The size of the resulting buffer should be the minimum of the available
  // size and the requested size.
  EXPECT_EQ(bytes.size() - 4,
            (buffer.template GetOffsetStorage<1, 0>(2, bytes.size() - 4)
                 .SizeInBytes()));
  EXPECT_EQ(
      0U,
      (buffer.template GetOffsetStorage<1, 0>(bytes.size(), 4).SizeInBytes()));
}

// ContiguousBuffer tests for std::vector and std::array types.
template <typename T>
class ReadWriteContiguousBufferTest : public ::testing::Test {};
typedef ::testing::Types</**/ ::std::vector<char>, ::std::array<char, 8>,
#if __cplusplus >= 201703L
                         ::std::vector<std::byte>,
#endif
                         ::std::vector<unsigned char>>
    ReadWriteContiguousContainerTypes;
TYPED_TEST_SUITE(ReadWriteContiguousBufferTest,
                 ReadWriteContiguousContainerTypes);

TYPED_TEST(ReadWriteContiguousBufferTest, ConstructionFromContainers) {
  TypeParam bytes =
      init_container<TypeParam>(0x08, 0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01);
  using CharType =
      typename ::std::remove_reference<decltype(*bytes.data())>::type;
  const auto buffer = ContiguousBuffer<CharType, 1, 0>{&bytes};

  // Read and Ok methods should work just as in ReadOnlyContiguousBuffer.
  EXPECT_EQ(bytes.size(), buffer.SizeInBytes());
  EXPECT_TRUE(buffer.Ok());
  EXPECT_EQ(0x0807060504030201UL, buffer.template ReadBigEndianUInt<64>());

  buffer.template WriteBigEndianUInt<64>(0x0102030405060708UL);
  EXPECT_EQ((init_container<TypeParam>(0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
                                       0x08)),
            bytes);

  bytes[4] = static_cast<CharType>(255);
  EXPECT_EQ(0x1020304ff060708UL, buffer.template ReadBigEndianUInt<64>());
}

TEST(ContiguousBuffer, ReturnTypeOfReadUInt) {
  const auto buffer = ContiguousBuffer<char, 1, 0>();

  EXPECT_TRUE((::std::is_same<decltype(buffer.ReadBigEndianUInt<64>()),
                              ::std::uint64_t>::value));
  EXPECT_TRUE((::std::is_same<decltype(buffer.ReadBigEndianUInt<48>()),
                              ::std::uint64_t>::value));
  EXPECT_TRUE((::std::is_same<decltype(buffer.ReadBigEndianUInt<32>()),
                              ::std::uint32_t>::value));
  EXPECT_TRUE((::std::is_same<decltype(buffer.ReadBigEndianUInt<16>()),
                              ::std::uint16_t>::value));
  EXPECT_TRUE((::std::is_same<decltype(buffer.ReadBigEndianUInt<8>()),
                              ::std::uint8_t>::value));

  EXPECT_TRUE((::std::is_same<decltype(buffer.ReadLittleEndianUInt<64>()),
                              ::std::uint64_t>::value));
  EXPECT_TRUE((::std::is_same<decltype(buffer.ReadLittleEndianUInt<48>()),
                              ::std::uint64_t>::value));
  EXPECT_TRUE((::std::is_same<decltype(buffer.ReadLittleEndianUInt<32>()),
                              ::std::uint32_t>::value));
  EXPECT_TRUE((::std::is_same<decltype(buffer.ReadLittleEndianUInt<16>()),
                              ::std::uint16_t>::value));
  EXPECT_TRUE((::std::is_same<decltype(buffer.ReadLittleEndianUInt<8>()),
                              ::std::uint8_t>::value));

  EXPECT_TRUE((::std::is_same<decltype(buffer.UncheckedReadBigEndianUInt<64>()),
                              ::std::uint64_t>::value));
  EXPECT_TRUE((::std::is_same<decltype(buffer.UncheckedReadBigEndianUInt<48>()),
                              ::std::uint64_t>::value));
  EXPECT_TRUE((::std::is_same<decltype(buffer.UncheckedReadBigEndianUInt<32>()),
                              ::std::uint32_t>::value));
  EXPECT_TRUE((::std::is_same<decltype(buffer.UncheckedReadBigEndianUInt<16>()),
                              ::std::uint16_t>::value));
  EXPECT_TRUE((::std::is_same<decltype(buffer.UncheckedReadBigEndianUInt<8>()),
                              ::std::uint8_t>::value));

  EXPECT_TRUE(
      (::std::is_same<decltype(buffer.UncheckedReadLittleEndianUInt<64>()),
                      ::std::uint64_t>::value));
  EXPECT_TRUE(
      (::std::is_same<decltype(buffer.UncheckedReadLittleEndianUInt<48>()),
                      ::std::uint64_t>::value));
  EXPECT_TRUE(
      (::std::is_same<decltype(buffer.UncheckedReadLittleEndianUInt<32>()),
                      ::std::uint32_t>::value));
  EXPECT_TRUE(
      (::std::is_same<decltype(buffer.UncheckedReadLittleEndianUInt<16>()),
                      ::std::uint16_t>::value));
  EXPECT_TRUE(
      (::std::is_same<decltype(buffer.UncheckedReadLittleEndianUInt<8>()),
                      ::std::uint8_t>::value));
}

TEST(ReadOnlyContiguousBuffer, Methods) {
  const ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08, 0x07, 0x06, 0x05,
       0x04, 0x03, 0x02, 0x01}};
  const auto buffer = ReadOnlyContiguousBuffer{bytes.data(), bytes.size() - 4};
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(buffer.ReadBigEndianUInt<64>(), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_TRUE(buffer.Ok());
  EXPECT_EQ(bytes.size() - 4, buffer.SizeInBytes());
  EXPECT_EQ(0x100f0e0d0c0b0a09UL, buffer.UncheckedReadBigEndianUInt<64>());
  EXPECT_EQ(0x090a0b0c0d0e0f10UL, buffer.UncheckedReadLittleEndianUInt<64>());

  const auto offset_buffer = buffer.GetOffsetStorage<1, 0>(4, 4);
  EXPECT_EQ(0x0c0b0a09U, offset_buffer.ReadBigEndianUInt<32>());
  EXPECT_EQ(0x090a0b0cU, offset_buffer.ReadLittleEndianUInt<32>());
  EXPECT_EQ(0x0c0b0a0908070605UL,
            offset_buffer.UncheckedReadBigEndianUInt<64>());
  EXPECT_EQ(4U, offset_buffer.SizeInBytes());
  EXPECT_TRUE(offset_buffer.Ok());

  const auto small_offset_buffer = buffer.GetOffsetStorage<1, 0>(4, 1);
  EXPECT_EQ(0x0cU, small_offset_buffer.ReadBigEndianUInt<8>());
  EXPECT_EQ(0x0cU, small_offset_buffer.ReadLittleEndianUInt<8>());
  EXPECT_EQ(1U, small_offset_buffer.SizeInBytes());
  EXPECT_TRUE(small_offset_buffer.Ok());

  EXPECT_FALSE(ReadOnlyContiguousBuffer().Ok());
  EXPECT_FALSE(
      (ReadOnlyContiguousBuffer{static_cast<char *>(nullptr), 12}.Ok()));
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH((ReadOnlyContiguousBuffer{static_cast<char *>(nullptr), 4}
                    .ReadBigEndianUInt<32>()),
               "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_EQ(0U, ReadOnlyContiguousBuffer().SizeInBytes());
  EXPECT_EQ(0U, (ReadOnlyContiguousBuffer{static_cast<char *>(nullptr), 12}
                     .SizeInBytes()));
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(
      (ReadOnlyContiguousBuffer{bytes.data(), 0}.ReadBigEndianUInt<8>()), "");
#endif  // EMBOSS_CHECK_ABORTS

  // The size of the resulting buffer should be the minimum of the available
  // size and the requested size.
  EXPECT_EQ(bytes.size() - 8,
            (buffer.GetOffsetStorage<1, 0>(4, bytes.size() - 4).SizeInBytes()));
  EXPECT_EQ(4U, (buffer.GetOffsetStorage<1, 0>(0, 4).SizeInBytes()));
  EXPECT_EQ(0U, (buffer.GetOffsetStorage<1, 0>(bytes.size(), 4).SizeInBytes()));
  EXPECT_FALSE((ReadOnlyContiguousBuffer().GetOffsetStorage<1, 0>(0, 0).Ok()));
}

TEST(ReadWriteContiguousBuffer, Methods) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x0c, 0x0b, 0x0a, 0x09, 0x08, 0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01}};
  const auto buffer = ReadWriteContiguousBuffer{bytes.data(), bytes.size() - 4};
  // Read and Ok methods should work just as in ReadOnlyContiguousBuffer.
  EXPECT_TRUE(buffer.Ok());
  EXPECT_EQ(bytes.size() - 4U, buffer.SizeInBytes());
  EXPECT_EQ(0x0c0b0a0908070605UL, buffer.ReadBigEndianUInt<64>());

  buffer.WriteBigEndianUInt<64>(0x05060708090a0b0c);
  EXPECT_EQ(
      (::std::vector</**/ ::std::uint8_t>{0x05, 0x06, 0x07, 0x08, 0x09, 0x0a,
                                          0x0b, 0x0c, 0x04, 0x03, 0x02, 0x01}),
      bytes);
  buffer.WriteLittleEndianUInt<64>(0x05060708090a0b0c);
  EXPECT_EQ(
      (::std::vector</**/ ::std::uint8_t>{0x0c, 0x0b, 0x0a, 0x09, 0x08, 0x07,
                                          0x06, 0x05, 0x04, 0x03, 0x02, 0x01}),
      bytes);

  const auto offset_buffer = buffer.GetOffsetStorage<1, 0>(4, 4);
  offset_buffer.WriteBigEndianUInt<32>(0x05060708);
  EXPECT_EQ(
      (::std::vector</**/ ::std::uint8_t>{0x0c, 0x0b, 0x0a, 0x09, 0x05, 0x06,
                                          0x07, 0x08, 0x04, 0x03, 0x02, 0x01}),
      bytes);
  offset_buffer.WriteLittleEndianUInt<32>(0x05060708);
  EXPECT_EQ(
      (::std::vector</**/ ::std::uint8_t>{0x0c, 0x0b, 0x0a, 0x09, 0x08, 0x07,
                                          0x06, 0x05, 0x04, 0x03, 0x02, 0x01}),
      bytes);

  const auto small_offset_buffer = buffer.GetOffsetStorage<1, 0>(4, 1);
  small_offset_buffer.WriteBigEndianUInt<8>(0x80);
  EXPECT_EQ(
      (::std::vector</**/ ::std::uint8_t>{0x0c, 0x0b, 0x0a, 0x09, 0x80, 0x07,
                                          0x06, 0x05, 0x04, 0x03, 0x02, 0x01}),
      bytes);
  small_offset_buffer.WriteLittleEndianUInt<8>(0x08);
  EXPECT_EQ(
      (::std::vector</**/ ::std::uint8_t>{0x0c, 0x0b, 0x0a, 0x09, 0x08, 0x07,
                                          0x06, 0x05, 0x04, 0x03, 0x02, 0x01}),
      bytes);

#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(ReadWriteContiguousBuffer().ReadLittleEndianUInt<8>(), "");
  EXPECT_DEATH(
      (ReadWriteContiguousBuffer{static_cast<unsigned char *>(nullptr), 1}
           .ReadLittleEndianUInt<8>()),
      "");
  EXPECT_DEATH(
      (ReadWriteContiguousBuffer{static_cast<unsigned char *>(nullptr), 1}
           .WriteLittleEndianUInt<8>(0xff)),
      "");
#endif  // EMBOSS_CHECK_ABORTS
}

TEST(ContiguousBuffer, AssignmentFromCompatibleContiguousBuffers) {
  alignas(4) char data[8];
  ContiguousBuffer<const unsigned char, 1, 0> buffer;
  buffer = ContiguousBuffer<char, 4, 1>(data + 1, sizeof data - 1);
  EXPECT_TRUE(buffer.Ok());
  EXPECT_EQ(buffer.data(), reinterpret_cast<unsigned char *>(data + 1));

  ContiguousBuffer<const unsigned char, 2, 1> aligned_buffer;
  aligned_buffer =
      ContiguousBuffer<unsigned char, 4, 3>(data + 3, sizeof data - 3);
  EXPECT_TRUE(aligned_buffer.Ok());
  EXPECT_EQ(aligned_buffer.data(), reinterpret_cast<unsigned char *>(data + 3));
}

TEST(ContiguousBuffer, ConstructionFromCompatibleContiguousBuffers) {
  alignas(4) char data[8];
  ContiguousBuffer<const unsigned char, 1, 0> buffer{
      ContiguousBuffer<char, 4, 1>(data + 1, sizeof data - 1)};
  EXPECT_TRUE(buffer.Ok());
  EXPECT_EQ(buffer.data(), reinterpret_cast<unsigned char *>(data + 1));

  ContiguousBuffer<const char, 2, 1> aligned_buffer{
      ContiguousBuffer<unsigned char, 4, 3>(data + 3, sizeof data - 3)};
  EXPECT_TRUE(aligned_buffer.Ok());
  EXPECT_EQ(aligned_buffer.data(), reinterpret_cast<char *>(data + 3));
}

TEST(ContiguousBuffer, ToString) {
  const ::std::vector</**/ ::std::uint8_t> bytes = {
      {'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'}};
  const auto buffer = ReadOnlyContiguousBuffer{bytes.data(), bytes.size() - 4};
  auto str = buffer.ToString</**/ ::std::string>();
  EXPECT_TRUE((::std::is_same</**/ ::std::string, decltype(str)>::value));
  EXPECT_EQ(str, "abcd");
#if __cplusplus >= 201703L
  auto str_view = buffer.ToString</**/ ::std::string_view>();
  EXPECT_TRUE(
      (::std::is_same</**/ ::std::string_view, decltype(str_view)>::value));
  EXPECT_EQ(str_view, "abcd");
#endif  // __cplusplus >= 201703L
}

TEST(LittleEndianByteOrderer, Methods) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {21, 22, 1, 2, 3, 4, 5, 6, 7, 8, 23, 24}};
  const int buffer_start = 2;
  const auto buffer = LittleEndianByteOrderer<ReadWriteContiguousBuffer>{
      ReadWriteContiguousBuffer{bytes.data() + buffer_start, 8}};
  EXPECT_EQ(8U, buffer.SizeInBytes());
  EXPECT_TRUE(buffer.Ok());
  EXPECT_EQ(0x0807060504030201UL, buffer.ReadUInt<64>());
  EXPECT_EQ(0x0807060504030201UL, buffer.UncheckedReadUInt<64>());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(buffer.ReadUInt<56>(), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_EQ(0x07060504030201UL, buffer.UncheckedReadUInt<56>());
  buffer.WriteUInt<64>(0x0102030405060708);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{21, 22, 8, 7, 6, 5, 4, 3, 2, 1,
                                                23, 24}),
            bytes);
  buffer.UncheckedWriteUInt<64>(0x0807060504030201);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{21, 22, 1, 2, 3, 4, 5, 6, 7, 8,
                                                23, 24}),
            bytes);
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(buffer.WriteUInt<56>(0x77777777777777), "");
#endif  // EMBOSS_CHECK_ABORTS

  EXPECT_FALSE(LittleEndianByteOrderer<ReadOnlyContiguousBuffer>().Ok());
  EXPECT_EQ(0U,
            LittleEndianByteOrderer<ReadOnlyContiguousBuffer>().SizeInBytes());
  EXPECT_EQ(bytes[1], (LittleEndianByteOrderer<ReadOnlyContiguousBuffer>{
                          ReadOnlyContiguousBuffer{bytes.data() + 1, 0}}
                           .UncheckedReadUInt<8>()));
  EXPECT_TRUE((LittleEndianByteOrderer<ReadOnlyContiguousBuffer>{
      ReadOnlyContiguousBuffer{bytes.data(), 0}}
                   .Ok()));
}

TEST(BigEndianByteOrderer, Methods) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {21, 22, 1, 2, 3, 4, 5, 6, 7, 8, 23, 24}};
  const int buffer_start = 2;
  const auto buffer = BigEndianByteOrderer<ReadWriteContiguousBuffer>{
      ReadWriteContiguousBuffer{bytes.data() + buffer_start, 8}};
  EXPECT_EQ(8U, buffer.SizeInBytes());
  EXPECT_TRUE(buffer.Ok());
  EXPECT_EQ(0x0102030405060708UL, buffer.ReadUInt<64>());
  EXPECT_EQ(0x0102030405060708UL, buffer.UncheckedReadUInt<64>());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(buffer.ReadUInt<56>(), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_EQ(0x01020304050607UL, buffer.UncheckedReadUInt<56>());
  buffer.WriteUInt<64>(0x0807060504030201);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{21, 22, 8, 7, 6, 5, 4, 3, 2, 1,
                                                23, 24}),
            bytes);
  buffer.UncheckedWriteUInt<64>(0x0102030405060708);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{21, 22, 1, 2, 3, 4, 5, 6, 7, 8,
                                                23, 24}),
            bytes);
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(buffer.WriteUInt<56>(0x77777777777777), "");
#endif  // EMBOSS_CHECK_ABORTS

  EXPECT_FALSE(BigEndianByteOrderer<ReadOnlyContiguousBuffer>().Ok());
  EXPECT_EQ(0U, BigEndianByteOrderer<ReadOnlyContiguousBuffer>().SizeInBytes());
  EXPECT_EQ(bytes[1], (BigEndianByteOrderer<ReadOnlyContiguousBuffer>{
                          ReadOnlyContiguousBuffer{bytes.data() + 1, 0}}
                           .UncheckedReadUInt<8>()));
  EXPECT_TRUE((BigEndianByteOrderer<ReadOnlyContiguousBuffer>{
      ReadOnlyContiguousBuffer{bytes.data(), 0}}
                   .Ok()));
}

TEST(NullByteOrderer, Methods) {
  ::std::uint8_t bytes[] = {0xdb, 0x0f, 0x0e, 0x0d};
  const auto buffer = NullByteOrderer<ReadWriteContiguousBuffer>{
      ReadWriteContiguousBuffer{bytes, 1}};
  EXPECT_EQ(bytes[0], buffer.ReadUInt<8>());
  EXPECT_EQ(bytes[0], buffer.UncheckedReadUInt<8>());
  // NullByteOrderer::UncheckedRead ignores its argument.
  EXPECT_EQ(bytes[0], buffer.UncheckedReadUInt<8>());
  buffer.WriteUInt<8>(0x24);
  EXPECT_EQ(0x24U, bytes[0]);
  buffer.UncheckedWriteUInt<8>(0x25);
  EXPECT_EQ(0x25U, bytes[0]);
  EXPECT_EQ(1U, buffer.SizeInBytes());
  EXPECT_TRUE(buffer.Ok());

  EXPECT_FALSE(NullByteOrderer<ReadOnlyContiguousBuffer>().Ok());
  EXPECT_EQ(0U, NullByteOrderer<ReadOnlyContiguousBuffer>().SizeInBytes());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH((NullByteOrderer<ReadOnlyContiguousBuffer>{
                   ReadOnlyContiguousBuffer{bytes, 0}}
                    .ReadUInt<8>()),
               "");
  EXPECT_DEATH((NullByteOrderer<ReadOnlyContiguousBuffer>{
                   ReadOnlyContiguousBuffer{bytes, 2}}
                    .ReadUInt<8>()),
               "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_EQ(bytes[0], (NullByteOrderer<ReadOnlyContiguousBuffer>{
                          ReadOnlyContiguousBuffer{bytes, 0}}
                           .UncheckedReadUInt<8>()));
  EXPECT_TRUE((NullByteOrderer<ReadOnlyContiguousBuffer>{
      ReadOnlyContiguousBuffer{bytes, 0}}
                   .Ok()));
}

TEST(BitBlock, BigEndianMethods) {
  ::std::uint8_t bytes[] = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                            0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10};
  const auto big_endian =
      BigEndianBitBlockN<64>{ReadWriteContiguousBuffer{bytes + 4, 8}};
  EXPECT_EQ(64U, big_endian.SizeInBits());
  EXPECT_TRUE(big_endian.Ok());
  EXPECT_EQ(0x05060708090a0b0cUL, big_endian.ReadUInt());
  EXPECT_EQ(0x05060708090a0b0cUL, big_endian.UncheckedReadUInt());
  EXPECT_FALSE(BigEndianBitBlockN<64>().Ok());
  EXPECT_EQ(64U, BigEndianBitBlockN<64>().SizeInBits());
  EXPECT_FALSE(
      (BigEndianBitBlockN<64>{ReadWriteContiguousBuffer{bytes, 0}}.Ok()));
}

TEST(BitBlock, LittleEndianMethods) {
  ::std::uint8_t bytes[] = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                            0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10};
  const auto little_endian =
      LittleEndianBitBlockN<64>{ReadWriteContiguousBuffer{bytes + 4, 8}};
  EXPECT_EQ(64U, little_endian.SizeInBits());
  EXPECT_TRUE(little_endian.Ok());
  EXPECT_EQ(0x0c0b0a0908070605UL, little_endian.ReadUInt());
  EXPECT_EQ(0x0c0b0a0908070605UL, little_endian.UncheckedReadUInt());
  EXPECT_FALSE(LittleEndianBitBlockN<64>().Ok());
  EXPECT_EQ(64U, LittleEndianBitBlockN<64>().SizeInBits());
  EXPECT_FALSE(
      (LittleEndianBitBlockN<64>{ReadWriteContiguousBuffer{bytes, 0}}.Ok()));
}

TEST(BitBlock, GetOffsetStorage) {
  ::std::uint8_t bytes[] = {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09,
                            0x08, 0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01};
  const auto bit_block =
      LittleEndianBitBlockN<64>{ReadWriteContiguousBuffer{bytes, 8}};
  const OffsetBitBlock<LittleEndianBitBlockN<64>> offset_block =
      bit_block.GetOffsetStorage<1, 0>(4, 8);
  EXPECT_EQ(8U, offset_block.SizeInBits());
  EXPECT_EQ(0xf1U, offset_block.ReadUInt());
  EXPECT_EQ(bit_block.SizeInBits(),
            (bit_block.GetOffsetStorage<1, 0>(8, bit_block.SizeInBits())
                 .SizeInBits()));
  EXPECT_FALSE(
      (bit_block.GetOffsetStorage<1, 0>(8, bit_block.SizeInBits()).Ok()));
  EXPECT_EQ(10U, (bit_block.GetOffsetStorage<1, 0>(bit_block.SizeInBits(), 10)
                      .SizeInBits()));
}

TEST(OffsetBitBlock, Methods) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09}};
  const auto bit_block =
      LittleEndianBitBlockN<64>{ReadWriteContiguousBuffer{&bytes}};
  EXPECT_FALSE((bit_block.GetOffsetStorage<1, 0>(0, 96).Ok()));
  EXPECT_TRUE((bit_block.GetOffsetStorage<1, 0>(0, 64).Ok()));

  const auto offset_block = bit_block.GetOffsetStorage<1, 0>(8, 48);
  EXPECT_FALSE((offset_block.GetOffsetStorage<1, 0>(40, 16).Ok()));
  EXPECT_EQ(0x0a0b0c0d0e0fUL, offset_block.ReadUInt());
  EXPECT_EQ(0x0a0b0c0d0e0fUL, offset_block.UncheckedReadUInt());
  offset_block.WriteUInt(0x0f0e0d0c0b0a);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x10, 0x0a, 0x0b, 0x0c, 0x0d,
                                                0x0e, 0x0f, 0x09}),
            bytes);
  offset_block.UncheckedWriteUInt(0x0a0b0c0d0e0f);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x10, 0x0f, 0x0e, 0x0d, 0x0c,
                                                0x0b, 0x0a, 0x09}),
            bytes);
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(offset_block.WriteUInt(0x10f0e0d0c0b0a), "");
#endif  // EMBOSS_CHECK_ABORTS
  offset_block.UncheckedWriteUInt(0x10f0e0d0c0b0a);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x10, 0x0a, 0x0b, 0x0c, 0x0d,
                                                0x0e, 0x0f, 0x09}),
            bytes);

  const auto offset_offset_block = offset_block.GetOffsetStorage<1, 0>(16, 16);
  EXPECT_FALSE((offset_offset_block.GetOffsetStorage<1, 0>(8, 16).Ok()));
  EXPECT_EQ(0x0d0cU, offset_offset_block.ReadUInt());
  EXPECT_EQ(0x0d0cU, offset_offset_block.UncheckedReadUInt());
  offset_offset_block.WriteUInt(0x0c0d);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x10, 0x0a, 0x0b, 0x0d, 0x0c,
                                                0x0e, 0x0f, 0x09}),
            bytes);
  offset_offset_block.UncheckedWriteUInt(0x0d0c);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x10, 0x0a, 0x0b, 0x0c, 0x0d,
                                                0x0e, 0x0f, 0x09}),
            bytes);
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(offset_offset_block.WriteUInt(0x10c0d), "");
#endif  // EMBOSS_CHECK_ABORTS
  offset_offset_block.UncheckedWriteUInt(0x20c0d);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x10, 0x0a, 0x0b, 0x0d, 0x0c,
                                                0x0e, 0x0f, 0x09}),
            bytes);

  const auto null_offset_block = OffsetBitBlock<BigEndianBitBlockN<32>>();
  EXPECT_FALSE(null_offset_block.Ok());
  EXPECT_EQ(0U, null_offset_block.SizeInBits());
}

}  // namespace test
}  // namespace support
}  // namespace emboss
