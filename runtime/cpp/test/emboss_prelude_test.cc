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

#include "runtime/cpp/emboss_prelude.h"

#include <type_traits>

#include "gtest/gtest.h"
#include "runtime/cpp/emboss_cpp_util.h"
#include "runtime/cpp/emboss_text_util.h"

namespace emboss {
namespace prelude {
namespace test {

using ::emboss::support::OffsetBitBlock;
using ::emboss::support::ReadWriteContiguousBuffer;

template </**/ ::std::size_t kBits>
using BitBlockN = ::emboss::support::BitBlock<
    ::emboss::support::LittleEndianByteOrderer<ReadWriteContiguousBuffer>,
    kBits>;

template </**/ ::std::size_t kBits>
using ViewParameters = ::emboss::support::FixedSizeViewParameters<
    kBits, ::emboss::support::AllValuesAreOk>;

TEST(FlagView, Methods) {
  ::std::uint8_t byte = 0;
  auto flag_view =
      FlagView<ViewParameters<1>, OffsetBitBlock<BitBlockN<8>>>{BitBlockN<8>{
          ReadWriteContiguousBuffer{&byte, 1}}.GetOffsetStorage<1, 0>(0, 1)};
  EXPECT_FALSE(flag_view.Read());
  byte = 0xfe;
  EXPECT_FALSE(flag_view.Read());
  byte = 0x01;
  EXPECT_TRUE(flag_view.Read());
  byte = 0xff;
  EXPECT_TRUE(flag_view.Read());
  EXPECT_TRUE(flag_view.CouldWriteValue(false));
  EXPECT_TRUE(flag_view.CouldWriteValue(true));
  flag_view.Write(false);
  EXPECT_EQ(0xfe, byte);
  byte = 0xaa;
  flag_view.Write(true);
  EXPECT_EQ(0xab, byte);
}

TEST(FlagView, TextDecode) {
  ::std::uint8_t byte = 0;
  const auto flag_view =
      FlagView<ViewParameters<1>, OffsetBitBlock<BitBlockN<8>>>{BitBlockN<8>{
          ReadWriteContiguousBuffer{&byte, 1}}.GetOffsetStorage<1, 0>(0, 1)};
  EXPECT_FALSE(UpdateFromText(flag_view, ""));
  EXPECT_FALSE(UpdateFromText(flag_view, "FALSE"));
  EXPECT_FALSE(UpdateFromText(flag_view, "TRUE"));
  EXPECT_FALSE(UpdateFromText(flag_view, "+true"));
  EXPECT_TRUE(UpdateFromText(flag_view, "true"));
  EXPECT_EQ(0x01, byte);
  EXPECT_TRUE(UpdateFromText(flag_view, "false"));
  EXPECT_EQ(0x00, byte);
  EXPECT_TRUE(UpdateFromText(flag_view, " true"));
  EXPECT_EQ(0x01, byte);
  {
    auto stream = support::TextStream{" false  xxx"};
    EXPECT_TRUE(flag_view.UpdateFromTextStream(&stream));
    EXPECT_EQ(0x00, byte);
    ::std::string token;
    EXPECT_TRUE(::emboss::support::ReadToken(&stream, &token));
    EXPECT_EQ("xxx", token);
  }
}

TEST(FlagView, TextEncode) {
  ::std::uint8_t byte = 0;
  const auto flag_view =
      FlagView<ViewParameters<1>, OffsetBitBlock<BitBlockN<8>>>{BitBlockN<8>{
          ReadWriteContiguousBuffer{&byte, 1}}.GetOffsetStorage<1, 0>(0, 1)};
  EXPECT_EQ("false", WriteToString(flag_view));
  byte = 1;
  EXPECT_EQ("true", WriteToString(flag_view));
}

template <template <typename, typename> class ViewType, int kMaxBits>
void CheckViewSizeInBits() {
  const int size_in_bits =
      ViewType<ViewParameters<kMaxBits>, BitBlockN<64>>::SizeInBits();
  EXPECT_EQ(size_in_bits, kMaxBits);
  return CheckViewSizeInBits<ViewType, kMaxBits - 1>();
}

template <>
void CheckViewSizeInBits<UIntView, 0>() {
  return;
}

template <>
void CheckViewSizeInBits<IntView, 0>() {
  return;
}

template <>
void CheckViewSizeInBits<BcdView, 0>() {
  return;
}

#if EMBOSS_HAS_INT128
TEST(UIntView, SizeInBits) { CheckViewSizeInBits<UIntView, 128>(); }

TEST(IntView, SizeInBits) { CheckViewSizeInBits<IntView, 128>(); }
#else
TEST(UIntView, SizeInBits) { CheckViewSizeInBits<UIntView, 64>(); }

TEST(IntView, SizeInBits) { CheckViewSizeInBits<IntView, 64>(); }
#endif  // EMBOSS_HAS_INT128

TEST(BcdView, SizeInBits) { CheckViewSizeInBits<BcdView, 64>(); }

template </**/ ::std::size_t kBits>
using UIntViewN = UIntView<ViewParameters<kBits>, BitBlockN<kBits>>;

TEST(UIntView, ValueType) {
  using BitBlockType = BitBlockN<64>;
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint8_t,
               UIntView<ViewParameters<8>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint8_t,
               UIntView<ViewParameters<6>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint16_t,
               UIntView<ViewParameters<9>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint16_t,
               UIntView<ViewParameters<16>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint32_t,
               UIntView<ViewParameters<17>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint32_t,
               UIntView<ViewParameters<32>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint64_t,
               UIntView<ViewParameters<33>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint64_t,
               UIntView<ViewParameters<64>, BitBlockType>::ValueType>::value));
#if EMBOSS_HAS_INT128
  using BitBlockType128 = BitBlockN<128>;
  EXPECT_TRUE((::std::is_same<
               __uint128_t,
               UIntView<ViewParameters<65>, BitBlockType128>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               __uint128_t,
               UIntView<ViewParameters<96>, BitBlockType128>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               __uint128_t,
               UIntView<ViewParameters<128>, BitBlockType128>::ValueType>::value));
#endif  // EMBOSS_HAS_INT128
}

TEST(UIntView, CouldWriteValue) {
  EXPECT_TRUE(UIntViewN<8>::CouldWriteValue(0xff));
  EXPECT_TRUE(UIntViewN<8>::CouldWriteValue(0));
  EXPECT_FALSE(UIntViewN<8>::CouldWriteValue(0x100));
  EXPECT_FALSE(UIntViewN<8>::CouldWriteValue(-1));
  EXPECT_TRUE(UIntViewN<16>::CouldWriteValue(0xffff));
  EXPECT_TRUE(UIntViewN<16>::CouldWriteValue(0));
  EXPECT_FALSE(UIntViewN<16>::CouldWriteValue(0x10000));
  EXPECT_FALSE(UIntViewN<16>::CouldWriteValue(-1));
  EXPECT_TRUE(UIntViewN<32>::CouldWriteValue(0xffffffffU));
  EXPECT_TRUE(UIntViewN<32>::CouldWriteValue(0xffffffffL));
  EXPECT_TRUE(UIntViewN<32>::CouldWriteValue(0));
  EXPECT_FALSE(UIntViewN<32>::CouldWriteValue(0x100000000L));
  EXPECT_FALSE(UIntViewN<32>::CouldWriteValue(-1));
  EXPECT_TRUE(UIntViewN<48>::CouldWriteValue(0x0000ffffffffffffUL));
  EXPECT_TRUE(UIntViewN<48>::CouldWriteValue(0x0000ffffffffffffL));
  EXPECT_TRUE(UIntViewN<48>::CouldWriteValue(0));
  EXPECT_FALSE(UIntViewN<48>::CouldWriteValue(0x1000000000000UL));
  EXPECT_FALSE(UIntViewN<48>::CouldWriteValue(0x1000000000000L));
  EXPECT_FALSE(UIntViewN<48>::CouldWriteValue(-1));
  EXPECT_TRUE(UIntViewN<64>::CouldWriteValue(0xffffffffffffffffUL));
  EXPECT_TRUE(UIntViewN<64>::CouldWriteValue(0));
  EXPECT_FALSE(UIntViewN<64>::CouldWriteValue(-1));
}

TEST(UIntView, CouldWriteValueNarrowing) {
  auto narrowing_could_write = [](int value) {
    return UIntViewN<8>::CouldWriteValue(value);
  };
  EXPECT_TRUE(narrowing_could_write(0));
  EXPECT_TRUE(narrowing_could_write(255));
  EXPECT_FALSE(narrowing_could_write(-1));
  EXPECT_FALSE(narrowing_could_write(256));
}

TEST(UIntView, ReadAndWriteWithSufficientBuffer) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}};
  auto uint64_view =
      UIntViewN<64>{BitBlockN<64>{ReadWriteContiguousBuffer{bytes.data(), 8}}};
  EXPECT_EQ(0x090a0b0c0d0e0f10UL, uint64_view.Read());
  EXPECT_EQ(0x090a0b0c0d0e0f10UL, uint64_view.UncheckedRead());
  uint64_view.Write(0x100f0e0d0c0b0a09UL);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x08}}),
            bytes);
  uint64_view.UncheckedWrite(0x090a0b0c0d0e0f10UL);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}}),
            bytes);
  EXPECT_TRUE(uint64_view.TryToWrite(0x100f0e0d0c0b0a09UL));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x08}}),
            bytes);
  EXPECT_TRUE(uint64_view.TryToWrite(0x090a0b0c0d0e0f10UL));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}}),
            bytes);
  EXPECT_TRUE(uint64_view.Ok());
  EXPECT_TRUE(uint64_view.IsComplete());
}

TEST(UIntView, ReadAndWriteWithInsufficientBuffer) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}};
  auto uint64_view =
      UIntViewN<64>{BitBlockN<64>{ReadWriteContiguousBuffer{bytes.data(), 4}}};
  EXPECT_EQ(0x090a0b0c0d0e0f10UL, uint64_view.UncheckedRead());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(uint64_view.Read(), "");
  EXPECT_DEATH(uint64_view.Write(0x100f0e0d0c0b0a09UL), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_FALSE(uint64_view.TryToWrite(0x100f0e0d0c0b0a09UL));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}}),
            bytes);
  uint64_view.UncheckedWrite(0x100f0e0d0c0b0a09UL);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x08}}),
            bytes);
  EXPECT_FALSE(uint64_view.Ok());
  EXPECT_FALSE(uint64_view.IsComplete());
  uint64_view.UncheckedWrite(0x090a0b0c0d0e0f10UL);
}

TEST(UIntView, NonPowerOfTwoSize) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x10, 0x0f, 0x0e, 0x0d}};
  auto uint24_view =
      UIntViewN<24>{BitBlockN<24>{ReadWriteContiguousBuffer{bytes.data(), 3}}};
  EXPECT_EQ(0x0e0f10U, uint24_view.Read());
  EXPECT_EQ(0x0e0f10U, uint24_view.UncheckedRead());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(uint24_view.Write(0x1000000), "");
#endif  // EMBOSS_CHECK_ABORTS
  uint24_view.Write(0x100f0e);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x0e, 0x0f, 0x10, 0x0d}}),
            bytes);
  uint24_view.UncheckedWrite(0x1000000);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x00, 0x00, 0x00, 0x0d}}),
            bytes);
  EXPECT_TRUE(uint24_view.Ok());
  EXPECT_TRUE(uint24_view.IsComplete());
}

TEST(UIntView, NonPowerOfTwoSizeInsufficientBuffer) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x10, 0x0f, 0x0e, 0x0d}};
  auto uint24_view =
      UIntViewN<24>{BitBlockN<24>{ReadWriteContiguousBuffer{bytes.data(), 2}}};
  EXPECT_EQ(0x0e0f10U, uint24_view.UncheckedRead());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(uint24_view.Read(), "");
  EXPECT_DEATH(uint24_view.Write(0x100f0e), "");
#endif  // EMBOSS_CHECK_ABORTS
  uint24_view.UncheckedWrite(0x100f0e);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x0e, 0x0f, 0x10, 0x0d}}),
            bytes);
  uint24_view.UncheckedWrite(0x1000000);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x00, 0x00, 0x00, 0x0d}}),
            bytes);
  EXPECT_FALSE(uint24_view.Ok());
  EXPECT_FALSE(uint24_view.IsComplete());
}

TEST(UIntView, NonByteSize) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x00, 0x00, 0x80, 0x80}};
  auto uint23_view =
      UIntView<ViewParameters<23>, OffsetBitBlock<BitBlockN<24>>>{BitBlockN<24>{
          ReadWriteContiguousBuffer{bytes.data(),
                                    3}}.GetOffsetStorage<1, 0>(0, 23)};
  EXPECT_EQ(0x0U, uint23_view.Read());
  EXPECT_FALSE(uint23_view.CouldWriteValue(0x800f0e));
  EXPECT_FALSE(uint23_view.CouldWriteValue(0x800000));
  EXPECT_TRUE(uint23_view.CouldWriteValue(0x7fffff));
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(uint23_view.Write(0x800f0e), "");
#endif  // EMBOSS_CHECK_ABORTS
  uint23_view.Write(0x400f0e);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x0e, 0x0f, 0xc0, 0x80}}),
            bytes);
  uint23_view.UncheckedWrite(0x1000000);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x00, 0x00, 0x80, 0x80}}),
            bytes);
  EXPECT_TRUE(uint23_view.Ok());
  EXPECT_TRUE(uint23_view.IsComplete());
}

TEST(UIntView, TextDecode) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x00, 0x00, 0x00, 0xff}};
  const auto uint24_view =
      UIntViewN<24>{BitBlockN<24>{ReadWriteContiguousBuffer{bytes.data(), 3}}};
  EXPECT_TRUE(UpdateFromText(uint24_view, "23"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{23, 0x00, 0x00, 0xff}}),
            bytes);
  EXPECT_EQ(23U, uint24_view.Read());
  EXPECT_FALSE(UpdateFromText(uint24_view, "16777216"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{23, 0x00, 0x00, 0xff}}),
            bytes);
  EXPECT_TRUE(UpdateFromText(uint24_view, "16777215"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0xff, 0xff, 0xff, 0xff}}),
            bytes);
  EXPECT_TRUE(UpdateFromText(uint24_view, "0x01_0203"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x03, 0x02, 0x01, 0xff}}),
            bytes);
}

template </**/ ::std::size_t kBits>
using IntViewN = IntView<ViewParameters<kBits>, BitBlockN<kBits>>;

TEST(IntView, ValueType) {
  using BitBlockType = BitBlockN<64>;
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::int8_t,
               IntView<ViewParameters<8>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::int8_t,
               IntView<ViewParameters<6>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::int16_t,
               IntView<ViewParameters<9>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::int16_t,
               IntView<ViewParameters<16>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::int32_t,
               IntView<ViewParameters<17>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::int32_t,
               IntView<ViewParameters<32>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::int64_t,
               IntView<ViewParameters<33>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::int64_t,
               IntView<ViewParameters<64>, BitBlockType>::ValueType>::value));
#if EMBOSS_HAS_INT128
  using BitBlockType128 = BitBlockN<128>;
  EXPECT_TRUE((::std::is_same<
               __int128_t,
               IntView<ViewParameters<65>, BitBlockType128>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               __int128_t,
               IntView<ViewParameters<96>, BitBlockType128>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               __int128_t,
               IntView<ViewParameters<128>, BitBlockType128>::ValueType>::value));
#endif  // EMBOSS_HAS_INT128
}

TEST(IntView, CouldWriteValue) {
  // Note that many values are in decimal in order to avoid C++'s implicit
  // conversions to unsigned for hex constants.
  EXPECT_TRUE(IntViewN<8>::CouldWriteValue(0x7f));
  EXPECT_TRUE(IntViewN<8>::CouldWriteValue(-0x80));
  EXPECT_FALSE(IntViewN<8>::CouldWriteValue(0x80));
  EXPECT_FALSE(IntViewN<8>::CouldWriteValue(0x8000000000000000UL));
  EXPECT_FALSE(IntViewN<8>::CouldWriteValue(-0x81));
  EXPECT_TRUE(IntViewN<16>::CouldWriteValue(32767));
  EXPECT_TRUE(IntViewN<16>::CouldWriteValue(0));
  EXPECT_FALSE(IntViewN<16>::CouldWriteValue(0x8000));
  EXPECT_FALSE(IntViewN<16>::CouldWriteValue(-0x8001));
  EXPECT_TRUE(IntViewN<32>::CouldWriteValue(0x7fffffffU));
  EXPECT_TRUE(IntViewN<32>::CouldWriteValue(0x7fffffffL));
  EXPECT_FALSE(IntViewN<32>::CouldWriteValue(0x80000000U));
  EXPECT_FALSE(IntViewN<32>::CouldWriteValue(-2147483649L));
  EXPECT_TRUE(IntViewN<48>::CouldWriteValue(0x00007fffffffffffUL));
  EXPECT_FALSE(IntViewN<48>::CouldWriteValue(140737488355328L));
  EXPECT_FALSE(IntViewN<48>::CouldWriteValue(-140737488355329L));
  EXPECT_TRUE(IntViewN<64>::CouldWriteValue(0x7fffffffffffffffUL));
  EXPECT_TRUE(IntViewN<64>::CouldWriteValue(9223372036854775807L));
  EXPECT_TRUE(IntViewN<64>::CouldWriteValue(-9223372036854775807L - 1));
  EXPECT_FALSE(IntViewN<64>::CouldWriteValue(0x8000000000000000UL));
}

TEST(IntView, CouldWriteValueNarrowing) {
  auto narrowing_could_write = [](int value) {
    return IntViewN<8>::CouldWriteValue(value);
  };
  EXPECT_TRUE(narrowing_could_write(-128));
  EXPECT_TRUE(narrowing_could_write(127));
  EXPECT_FALSE(narrowing_could_write(-129));
  EXPECT_FALSE(narrowing_could_write(128));
}

TEST(IntView, ReadAndWriteWithSufficientBuffer) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}};
  auto int64_view =
      IntViewN<64>{BitBlockN<64>{ReadWriteContiguousBuffer{bytes.data(), 8}}};
  EXPECT_EQ(0x090a0b0c0d0e0f10L, int64_view.Read());
  EXPECT_EQ(0x090a0b0c0d0e0f10L, int64_view.UncheckedRead());
  int64_view.Write(0x100f0e0d0c0b0a09L);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x08}}),
            bytes);
  int64_view.UncheckedWrite(0x090a0b0c0d0e0f10L);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}}),
            bytes);
  EXPECT_TRUE(int64_view.TryToWrite(0x100f0e0d0c0b0a09L));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x08}}),
            bytes);
  int64_view.Write(-0x100f0e0d0c0b0a09L);
  EXPECT_EQ(-0x100f0e0d0c0b0a09L, int64_view.Read());
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0xf7, 0xf5, 0xf4, 0xf3, 0xf2, 0xf1, 0xf0, 0xef, 0x08}}),
            bytes);
  EXPECT_TRUE(int64_view.Ok());
  EXPECT_TRUE(int64_view.IsComplete());
}

TEST(IntView, ReadAndWriteWithInsufficientBuffer) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}};
  auto int64_view =
      IntViewN<64>{BitBlockN<64>{ReadWriteContiguousBuffer{bytes.data(), 4}}};
  EXPECT_EQ(0x090a0b0c0d0e0f10L, int64_view.UncheckedRead());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(int64_view.Read(), "");
  EXPECT_DEATH(int64_view.Write(0x100f0e0d0c0b0a09L), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_FALSE(int64_view.TryToWrite(0x100f0e0d0c0b0a09L));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}}),
            bytes);
  int64_view.UncheckedWrite(0x100f0e0d0c0b0a09L);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x08}}),
            bytes);
  EXPECT_FALSE(int64_view.Ok());
  EXPECT_FALSE(int64_view.IsComplete());
}

TEST(IntView, NonPowerOfTwoSize) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x10, 0x0f, 0x0e, 0x0d}};
  auto int24_view =
      IntViewN<24>{BitBlockN<24>{ReadWriteContiguousBuffer{bytes.data(), 3}}};
  EXPECT_EQ(0x0e0f10, int24_view.Read());
  EXPECT_EQ(0x0e0f10, int24_view.UncheckedRead());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(int24_view.Write(0x1000000), "");
#endif  // EMBOSS_CHECK_ABORTS
  int24_view.Write(0x100f0e);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x0e, 0x0f, 0x10, 0x0d}}),
            bytes);
  int24_view.Write(-0x100f0e);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0xf2, 0xf0, 0xef, 0x0d}}),
            bytes);
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(int24_view.Write(0x1000000), "");
#endif  // EMBOSS_CHECK_ABORTS
  int24_view.UncheckedWrite(0x1000000);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x00, 0x00, 0x00, 0x0d}}),
            bytes);
  EXPECT_TRUE(int24_view.Ok());
  EXPECT_TRUE(int24_view.IsComplete());
}

TEST(IntView, NonPowerOfTwoSizeInsufficientBuffer) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x10, 0x0f, 0x0e, 0x0d}};
  auto int24_view =
      IntViewN<24>{BitBlockN<24>{ReadWriteContiguousBuffer{bytes.data(), 2}}};
  EXPECT_EQ(0x0e0f10, int24_view.UncheckedRead());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(int24_view.Read(), "");
  EXPECT_DEATH(int24_view.Write(0x100f0e), "");
#endif  // EMBOSS_CHECK_ABORTS
  int24_view.UncheckedWrite(0x100f0e);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x0e, 0x0f, 0x10, 0x0d}}),
            bytes);
  int24_view.UncheckedWrite(0x1000000);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x00, 0x00, 0x00, 0x0d}}),
            bytes);
  EXPECT_FALSE(int24_view.Ok());
  EXPECT_FALSE(int24_view.IsComplete());
}

TEST(IntView, NonByteSize) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x00, 0x00, 0x80, 0x80}};
  auto int23_view =
      IntView<ViewParameters<23>, OffsetBitBlock<BitBlockN<24>>>{BitBlockN<24>{
          ReadWriteContiguousBuffer{bytes.data(),
                                    3}}.GetOffsetStorage<1, 0>(0, 23)};
  EXPECT_EQ(0x0, int23_view.Read());
  EXPECT_FALSE(int23_view.CouldWriteValue(0x400f0e));
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(int23_view.Write(0x400f0e), "");
#endif  // EMBOSS_CHECK_ABORTS
  int23_view.Write(0x200f0e);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x0e, 0x0f, 0xa0, 0x80}}),
            bytes);
  int23_view.Write(-0x400000);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x00, 0x00, 0xc0, 0x80}}),
            bytes);
  int23_view.UncheckedWrite(0x1000000);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x00, 0x00, 0x80, 0x80}}),
            bytes);
  EXPECT_TRUE(int23_view.Ok());
  EXPECT_TRUE(int23_view.IsComplete());
}

TEST(IntView, OneBit) {
  ::std::uint8_t bytes[] = {0xfe};
  auto int1_view =
      IntView<ViewParameters<1>, OffsetBitBlock<BitBlockN<8>>>{BitBlockN<8>{
          ReadWriteContiguousBuffer{bytes, 1}}.GetOffsetStorage<1, 0>(0, 1)};
  EXPECT_TRUE(int1_view.Ok());
  EXPECT_TRUE(int1_view.IsComplete());
  EXPECT_EQ(0, int1_view.Read());
  EXPECT_FALSE(int1_view.CouldWriteValue(1));
  EXPECT_TRUE(int1_view.CouldWriteValue(0));
  EXPECT_TRUE(int1_view.CouldWriteValue(-1));
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(int1_view.Write(1), "");
#endif  // EMBOSS_CHECK_ABORTS
  int1_view.Write(-1);
  EXPECT_EQ(0xff, bytes[0]);
  EXPECT_EQ(-1, int1_view.Read());
  int1_view.Write(0);
  EXPECT_EQ(0xfe, bytes[0]);
  bytes[0] = 0;
  int1_view.Write(-1);
  EXPECT_EQ(0x01, bytes[0]);
}

TEST(IntView, TextDecode) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x00, 0x00, 0x00, 0xff}};
  const auto int24_view =
      IntViewN<24>{BitBlockN<24>{ReadWriteContiguousBuffer{bytes.data(), 3}}};
  EXPECT_TRUE(UpdateFromText(int24_view, "23"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{23, 0x00, 0x00, 0xff}}),
            bytes);
  EXPECT_EQ(23, int24_view.Read());
  EXPECT_FALSE(UpdateFromText(int24_view, "16777216"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{23, 0x00, 0x00, 0xff}}),
            bytes);
  EXPECT_FALSE(UpdateFromText(int24_view, "16777215"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{23, 0x00, 0x00, 0xff}}),
            bytes);
  EXPECT_FALSE(UpdateFromText(int24_view, "8388608"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{23, 0x00, 0x00, 0xff}}),
            bytes);
  EXPECT_TRUE(UpdateFromText(int24_view, "8388607"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0xff, 0xff, 0x7f, 0xff}}),
            bytes);
  EXPECT_TRUE(UpdateFromText(int24_view, "-8388608"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x00, 0x00, 0x80, 0xff}}),
            bytes);
  EXPECT_TRUE(UpdateFromText(int24_view, "-1"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0xff, 0xff, 0xff, 0xff}}),
            bytes);
  EXPECT_TRUE(UpdateFromText(int24_view, "0x01_0203"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x03, 0x02, 0x01, 0xff}}),
            bytes);
  EXPECT_TRUE(UpdateFromText(int24_view, "-0x01_0203"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0xfd, 0xfd, 0xfe, 0xff}}),
            bytes);
  EXPECT_FALSE(UpdateFromText(int24_view, "- 0x01_0203"));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0xfd, 0xfd, 0xfe, 0xff}}),
            bytes);
}

TEST(MaxBcd, Values) {
  EXPECT_EQ(0U, MaxBcd</**/ ::std::uint64_t>(0));
  EXPECT_EQ(1U, MaxBcd</**/ ::std::uint64_t>(1));
  EXPECT_EQ(3U, MaxBcd</**/ ::std::uint64_t>(2));
  EXPECT_EQ(7U, MaxBcd</**/ ::std::uint64_t>(3));
  EXPECT_EQ(9U, MaxBcd</**/ ::std::uint64_t>(4));
  EXPECT_EQ(19U, MaxBcd</**/ ::std::uint64_t>(5));
  EXPECT_EQ(39U, MaxBcd</**/ ::std::uint64_t>(6));
  EXPECT_EQ(79U, MaxBcd</**/ ::std::uint64_t>(7));
  EXPECT_EQ(99U, MaxBcd</**/ ::std::uint64_t>(8));
  EXPECT_EQ(199U, MaxBcd</**/ ::std::uint64_t>(9));
  EXPECT_EQ(999U, MaxBcd</**/ ::std::uint64_t>(12));
  EXPECT_EQ(9999U, MaxBcd</**/ ::std::uint64_t>(16));
  EXPECT_EQ(999999U, MaxBcd</**/ ::std::uint64_t>(24));
  EXPECT_EQ(3999999999999999UL, MaxBcd</**/ ::std::uint64_t>(62));
  EXPECT_EQ(7999999999999999UL, MaxBcd</**/ ::std::uint64_t>(63));
  EXPECT_EQ(9999999999999999UL, MaxBcd</**/ ::std::uint64_t>(64));
  // Max uint64_t is 18446744073709551616, which is big enough to hold a 76-bit
  // BCD value.
  EXPECT_EQ(19999999999999999UL, MaxBcd</**/ ::std::uint64_t>(65));
  EXPECT_EQ(39999999999999999UL, MaxBcd</**/ ::std::uint64_t>(66));
  EXPECT_EQ(99999999999999999UL, MaxBcd</**/ ::std::uint64_t>(68));
  EXPECT_EQ(999999999999999999UL, MaxBcd</**/ ::std::uint64_t>(72));
  EXPECT_EQ(9999999999999999999UL, MaxBcd</**/ ::std::uint64_t>(76));
}

TEST(IsBcd, Values) {
  EXPECT_TRUE(IsBcd(0x00U));
  EXPECT_TRUE(IsBcd(0x12U));
  EXPECT_TRUE(IsBcd(0x91U));
  EXPECT_TRUE(IsBcd(0x99U));
  EXPECT_TRUE(IsBcd(::std::uint8_t{0x00}));
  EXPECT_TRUE(IsBcd(::std::uint8_t{0x99}));
  EXPECT_TRUE(IsBcd(::std::uint16_t{0x0000}));
  EXPECT_TRUE(IsBcd(::std::uint16_t{0x9999}));
  EXPECT_TRUE(IsBcd(0x9999999999999999UL));
  EXPECT_FALSE(IsBcd(::std::uint8_t{0x0a}));
  EXPECT_FALSE(IsBcd(::std::uint8_t{0xa0}));
  EXPECT_FALSE(IsBcd(::std::uint8_t{0xff}));
  EXPECT_FALSE(IsBcd(::std::uint16_t{0x0a00}));
  EXPECT_FALSE(IsBcd(::std::uint16_t{0x000a}));
  EXPECT_FALSE(IsBcd(0x999999999999999aUL));
  EXPECT_FALSE(IsBcd(0xaUL));
  EXPECT_FALSE(IsBcd(0xa000000000000000UL));
  EXPECT_FALSE(IsBcd(0xf000000000000000UL));
  EXPECT_FALSE(IsBcd(0xffffffffffffffffUL));
}

TEST(BcdView, ValueType) {
  using BitBlockType = BitBlockN<64>;
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint8_t,
               BcdView<ViewParameters<8>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint8_t,
               BcdView<ViewParameters<6>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint16_t,
               BcdView<ViewParameters<9>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint16_t,
               BcdView<ViewParameters<16>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint32_t,
               BcdView<ViewParameters<17>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint32_t,
               BcdView<ViewParameters<32>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint64_t,
               BcdView<ViewParameters<33>, BitBlockType>::ValueType>::value));
  EXPECT_TRUE((::std::is_same<
               /**/ ::std::uint64_t,
               BcdView<ViewParameters<64>, BitBlockType>::ValueType>::value));
}

TEST(BcdView, CouldWriteValue) {
  EXPECT_TRUE((BcdView<ViewParameters<64>, int>::CouldWriteValue(0)));
  EXPECT_TRUE(
      (BcdView<ViewParameters<64>, int>::CouldWriteValue(9999999999999999)));
  EXPECT_FALSE(
      (BcdView<ViewParameters<64>, int>::CouldWriteValue(10000000000000000)));
  EXPECT_FALSE((
      BcdView<ViewParameters<64>, int>::CouldWriteValue(0xffffffffffffffffUL)));
  EXPECT_FALSE(
      (BcdView<ViewParameters<48>, int>::CouldWriteValue(9999999999999999)));
  EXPECT_TRUE(
      (BcdView<ViewParameters<48>, int>::CouldWriteValue(999999999999)));
  EXPECT_TRUE((BcdView<ViewParameters<48>, int>::CouldWriteValue(0)));
  EXPECT_FALSE((BcdView<ViewParameters<48>, int>::CouldWriteValue(
      (0xffUL << 48) + 999999999999)));
  EXPECT_FALSE(
      (BcdView<ViewParameters<48>, int>::CouldWriteValue(10000000000000000)));
  EXPECT_FALSE((
      BcdView<ViewParameters<48>, int>::CouldWriteValue(0xffffffffffffffffUL)));
}

template </**/ ::std::size_t kBits>
using BcdViewN = BcdView<ViewParameters<kBits>, BitBlockN<kBits>>;

TEST(BcdView, ReadAndWriteWithSufficientBuffer) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x16, 0x15, 0x14, 0x13, 0x12, 0x11, 0x10, 0x09, 0x08}};
  auto bcd64_view =
      BcdViewN<64>{BitBlockN<64>{ReadWriteContiguousBuffer{bytes.data(), 8}}};
  EXPECT_EQ(910111213141516UL, bcd64_view.Read());
  EXPECT_EQ(910111213141516UL, bcd64_view.UncheckedRead());
  bcd64_view.Write(1615141312111009);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x09, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x08}}),
            bytes);
  bcd64_view.UncheckedWrite(910111213141516UL);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x16, 0x15, 0x14, 0x13, 0x12, 0x11, 0x10, 0x09, 0x08}}),
            bytes);
  EXPECT_TRUE(bcd64_view.TryToWrite(1615141312111009));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x09, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x08}}),
            bytes);
  EXPECT_TRUE(bcd64_view.Ok());
  EXPECT_TRUE(bcd64_view.IsComplete());
}

TEST(BcdView, ReadAndWriteWithInsufficientBuffer) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x16, 0x15, 0x14, 0x13, 0x12, 0x11, 0x10, 0x09, 0x08}};
  auto bcd64_view =
      BcdViewN<64>{BitBlockN<64>{ReadWriteContiguousBuffer{bytes.data(), 4}}};
  EXPECT_EQ(910111213141516UL, bcd64_view.UncheckedRead());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(bcd64_view.Read(), "");
  EXPECT_DEATH(bcd64_view.Write(1615141312111009), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_FALSE(bcd64_view.TryToWrite(1615141312111009));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x16, 0x15, 0x14, 0x13, 0x12, 0x11, 0x10, 0x09, 0x08}}),
            bytes);
  bcd64_view.UncheckedWrite(1615141312111009);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{
                {0x09, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x08}}),
            bytes);
  EXPECT_FALSE(bcd64_view.Ok());
  EXPECT_FALSE(bcd64_view.IsComplete());
}

TEST(BcdView, NonPowerOfTwoSize) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x16, 0x15, 0x14, 0x13}};
  auto bcd24_view =
      BcdViewN<24>{BitBlockN<24>{ReadWriteContiguousBuffer{bytes.data(), 3}}};
  EXPECT_EQ(141516U, bcd24_view.Read());
  EXPECT_EQ(141516U, bcd24_view.UncheckedRead());
  bcd24_view.Write(161514);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x14, 0x15, 0x16, 0x13}}),
            bytes);
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(bcd24_view.Write(1000000), "");
#endif  // EMBOSS_CHECK_ABORTS
  bcd24_view.UncheckedWrite(1000000);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x00, 0x00, 0x00, 0x13}}),
            bytes);
  bcd24_view.UncheckedWrite(141516);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x16, 0x15, 0x14, 0x13}}),
            bytes);
  EXPECT_TRUE(bcd24_view.Ok());
  EXPECT_TRUE(bcd24_view.IsComplete());
}

TEST(BcdView, NonPowerOfTwoSizeInsufficientBuffer) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x16, 0x15, 0x14, 0x13}};
  auto bcd24_view =
      BcdViewN<24>{BitBlockN<24>{ReadWriteContiguousBuffer{bytes.data(), 2}}};
  EXPECT_EQ(141516U, bcd24_view.UncheckedRead());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(bcd24_view.Read(), "");
  EXPECT_DEATH(bcd24_view.Write(161514), "");
#endif  // EMBOSS_CHECK_ABORTS
  bcd24_view.UncheckedWrite(161514);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x14, 0x15, 0x16, 0x13}}),
            bytes);
  bcd24_view.UncheckedWrite(1000000);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x00, 0x00, 0x00, 0x13}}),
            bytes);
  EXPECT_FALSE(bcd24_view.Ok());
  EXPECT_FALSE(bcd24_view.IsComplete());
}

TEST(BcdView, NonByteSize) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x00, 0x00, 0x80, 0x80}};
  auto bcd23_view =
      BcdView<ViewParameters<23>, OffsetBitBlock<BitBlockN<24>>>{BitBlockN<24>{
          ReadWriteContiguousBuffer{bytes.data(),
                                    3}}.GetOffsetStorage<1, 0>(0, 23)};
  EXPECT_EQ(0x0U, bcd23_view.Read());
  EXPECT_FALSE(bcd23_view.CouldWriteValue(800000));
  EXPECT_TRUE(bcd23_view.CouldWriteValue(799999));
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(bcd23_view.Write(800000), "");
#endif  // EMBOSS_CHECK_ABORTS
  bcd23_view.Write(432198);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x98, 0x21, 0xc3, 0x80}}),
            bytes);
  bcd23_view.UncheckedWrite(800000);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{{0x00, 0x00, 0x80, 0x80}}),
            bytes);
  EXPECT_TRUE(bcd23_view.Ok());
  EXPECT_TRUE(bcd23_view.IsComplete());
}

TEST(BcdLittleEndianView, AllByteValues) {
  ::std::uint8_t byte = 0;
  auto bcd8_view =
      BcdViewN<8>{BitBlockN<8>{ReadWriteContiguousBuffer{&byte, 1}}};
  for (int i = 0; i < 15; ++i) {
    for (int j = 0; j < 15; ++j) {
      byte = i * 16 + j;
      if (i > 9 || j > 9) {
        EXPECT_FALSE(bcd8_view.Ok()) << i << ", " << j;
      } else {
        EXPECT_TRUE(bcd8_view.Ok()) << i << ", " << j;
      }
    }
  }
}

}  // namespace test
}  // namespace prelude
}  // namespace emboss
