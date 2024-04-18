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

#include "runtime/cpp/emboss_enum_view.h"

#include "gtest/gtest.h"
#include "runtime/cpp/emboss_prelude.h"
#include "runtime/cpp/emboss_text_util.h"

namespace emboss {
namespace support {
namespace test {

template </**/ ::std::size_t kBits>
using LittleEndianBitBlockN =
    BitBlock<LittleEndianByteOrderer<ReadWriteContiguousBuffer>, kBits>;

enum class Foo : ::std::int64_t {
  kMin = -0x7fffffffffffffffL - 1,
  kOne = 1,
  kTwo = 2,
  kBig = 0x0e0f10,
  kBigBackwards = 0x100f0e,
  kReallyBig = 0x090a0b0c0d0e0f10L,
  kReallyBigBackwards = 0x100f0e0d0c0b0a09L,
  k2to24MinusOne = (1L << 24) - 1,
  k2to24 = 1L << 24,
  kMax = 0x7fffffffffffffffL,
};

static inline bool TryToGetEnumFromName(const char *name, Foo *result) {
  if (!strcmp("kMin", name)) {
    *result = Foo::kMin;
    return true;
  }
  if (!strcmp("kOne", name)) {
    *result = Foo::kOne;
    return true;
  }
  if (!strcmp("kTwo", name)) {
    *result = Foo::kTwo;
    return true;
  }
  if (!strcmp("kBig", name)) {
    *result = Foo::kBig;
    return true;
  }
  if (!strcmp("kBigBackwards", name)) {
    *result = Foo::kBigBackwards;
    return true;
  }
  if (!strcmp("kReallyBig", name)) {
    *result = Foo::kReallyBig;
    return true;
  }
  if (!strcmp("kReallyBigBackwards", name)) {
    *result = Foo::kReallyBigBackwards;
    return true;
  }
  if (!strcmp("k2to24MinusOne", name)) {
    *result = Foo::k2to24MinusOne;
    return true;
  }
  if (!strcmp("k2to24", name)) {
    *result = Foo::k2to24;
    return true;
  }
  if (!strcmp("kMax", name)) {
    *result = Foo::kMax;
    return true;
  }
  return false;
}

static inline const char *TryToGetNameFromEnum(Foo value) {
  switch (value) {
    case Foo::kMin:
      return "kMin";
    case Foo::kOne:
      return "kOne";
    case Foo::kTwo:
      return "kTwo";
    case Foo::kBig:
      return "kBig";
    case Foo::kBigBackwards:
      return "kBigBackwards";
    case Foo::kReallyBig:
      return "kReallyBig";
    case Foo::kReallyBigBackwards:
      return "kReallyBigBackwards";
    case Foo::k2to24MinusOne:
      return "k2to24MinusOne";
    case Foo::k2to24:
      return "k2to24";
    case Foo::kMax:
      return "kMax";
    default:
      return nullptr;
  }
}

template </**/ ::std::size_t kBits>
using FooViewN = EnumView<Foo, FixedSizeViewParameters<kBits, AllValuesAreOk>,
                          LittleEndianBitBlockN<kBits>>;

template <int kMaxBits>
void CheckEnumViewSizeInBits() {
  const int size_in_bits =
      EnumView<Foo, FixedSizeViewParameters<kMaxBits, AllValuesAreOk>,
               OffsetBitBlock<LittleEndianBitBlockN<64>>>::SizeInBits();
  EXPECT_EQ(size_in_bits, kMaxBits);
  return CheckEnumViewSizeInBits<kMaxBits - 1>();
}

template <>
void CheckEnumViewSizeInBits<0>() {
  return;
}

TEST(EnumView, SizeInBits) { CheckEnumViewSizeInBits<64>(); }

TEST(EnumView, ValueType) {
  using BitBlockType = OffsetBitBlock<LittleEndianBitBlockN<64>>;
  EXPECT_TRUE(
      (::std::is_same<Foo,
                      EnumView<Foo, FixedSizeViewParameters<8, AllValuesAreOk>,
                               BitBlockType>::ValueType>::value));
  EXPECT_TRUE(
      (::std::is_same<Foo,
                      EnumView<Foo, FixedSizeViewParameters<6, AllValuesAreOk>,
                               BitBlockType>::ValueType>::value));
  EXPECT_TRUE(
      (::std::is_same<Foo,
                      EnumView<Foo, FixedSizeViewParameters<33, AllValuesAreOk>,
                               BitBlockType>::ValueType>::value));
  EXPECT_TRUE(
      (::std::is_same<Foo,
                      EnumView<Foo, FixedSizeViewParameters<64, AllValuesAreOk>,
                               BitBlockType>::ValueType>::value));
}

TEST(EnumView, CouldWriteValue) {
  EXPECT_TRUE(FooViewN<64>::CouldWriteValue(Foo::kMax));
  EXPECT_TRUE(FooViewN<64>::CouldWriteValue(Foo::kMax));
  EXPECT_TRUE(FooViewN<24>::CouldWriteValue(Foo::k2to24MinusOne));
  EXPECT_FALSE(FooViewN<24>::CouldWriteValue(Foo::k2to24));
}

TEST(EnumView, ReadAndWriteWithSufficientBuffer) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}};
  auto enum64_view = FooViewN<64>{ReadWriteContiguousBuffer{bytes.data(), 8}};
  EXPECT_EQ(Foo::kReallyBig, enum64_view.Read());
  EXPECT_EQ(Foo::kReallyBig, enum64_view.UncheckedRead());
  enum64_view.Write(Foo::kReallyBigBackwards);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x09, 0x0a, 0x0b, 0x0c, 0x0d,
                                                0x0e, 0x0f, 0x10, 0x08}),
            bytes);
  enum64_view.UncheckedWrite(Foo::kReallyBig);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x10, 0x0f, 0x0e, 0x0d, 0x0c,
                                                0x0b, 0x0a, 0x09, 0x08}),
            bytes);
  EXPECT_TRUE(enum64_view.TryToWrite(Foo::kReallyBigBackwards));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x09, 0x0a, 0x0b, 0x0c, 0x0d,
                                                0x0e, 0x0f, 0x10, 0x08}),
            bytes);
  EXPECT_TRUE(enum64_view.Ok());
  EXPECT_TRUE(enum64_view.IsComplete());
}

TEST(EnumView, ReadAndWriteWithInsufficientBuffer) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}};
  auto enum64_view = FooViewN<64>{ReadWriteContiguousBuffer{bytes.data(), 4}};
  EXPECT_EQ(Foo::kReallyBig, enum64_view.UncheckedRead());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(enum64_view.Read(), "");
  EXPECT_DEATH(enum64_view.Write(Foo::kReallyBigBackwards), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_FALSE(enum64_view.TryToWrite(Foo::kReallyBigBackwards));
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x10, 0x0f, 0x0e, 0x0d, 0x0c,
                                                0x0b, 0x0a, 0x09, 0x08}),
            bytes);
  enum64_view.UncheckedWrite(Foo::kReallyBigBackwards);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x09, 0x0a, 0x0b, 0x0c, 0x0d,
                                                0x0e, 0x0f, 0x10, 0x08}),
            bytes);
  EXPECT_FALSE(enum64_view.Ok());
  EXPECT_FALSE(enum64_view.IsComplete());
}

TEST(EnumView, NonPowerOfTwoSize) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x10, 0x0f, 0x0e, 0x0d}};
  auto enum24_view = FooViewN<24>{ReadWriteContiguousBuffer{bytes.data(), 3}};
  EXPECT_EQ(Foo::kBig, enum24_view.Read());
  EXPECT_EQ(Foo::kBig, enum24_view.UncheckedRead());
  enum24_view.Write(Foo::kBigBackwards);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x0e, 0x0f, 0x10, 0x0d}),
            bytes);
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(enum24_view.Write(Foo::k2to24), "");
#endif  // EMBOSS_CHECK_ABORTS
  enum24_view.UncheckedWrite(Foo::k2to24);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x00, 0x00, 0x00, 0x0d}),
            bytes);
  EXPECT_TRUE(enum24_view.Ok());
  EXPECT_TRUE(enum24_view.IsComplete());
}

TEST(EnumView, NonPowerOfTwoSizeInsufficientBuffer) {
  ::std::vector</**/ ::std::uint8_t> bytes = {{0x10, 0x0f, 0x0e, 0x0d}};
  auto enum24_view = FooViewN<24>{ReadWriteContiguousBuffer{bytes.data(), 2}};
  EXPECT_EQ(Foo::kBig, enum24_view.UncheckedRead());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(enum24_view.Read(), "");
  EXPECT_DEATH(enum24_view.Write(Foo::kBigBackwards), "");
#endif  // EMBOSS_CHECK_ABORTS
  enum24_view.UncheckedWrite(Foo::kBigBackwards);
  EXPECT_EQ((::std::vector</**/ ::std::uint8_t>{0x0e, 0x0f, 0x10, 0x0d}),
            bytes);
  EXPECT_FALSE(enum24_view.Ok());
  EXPECT_FALSE(enum24_view.IsComplete());
}

TEST(EnumView, UpdateFromText) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}};
  const auto enum64_view =
      FooViewN<64>{ReadWriteContiguousBuffer{bytes.data(), 8}};
  EXPECT_TRUE(UpdateFromText(enum64_view, "kBig"));
  EXPECT_EQ(Foo::kBig, enum64_view.Read());
  EXPECT_TRUE(UpdateFromText(enum64_view, "k2to24"));
  EXPECT_EQ(Foo::k2to24, enum64_view.Read());
  EXPECT_FALSE(UpdateFromText(enum64_view, "k2to24M"));
  EXPECT_EQ(Foo::k2to24, enum64_view.Read());
  EXPECT_TRUE(UpdateFromText(enum64_view, "k2to24MinusOne"));
  EXPECT_EQ(Foo::k2to24MinusOne, enum64_view.Read());
  EXPECT_TRUE(UpdateFromText(enum64_view, "0x0e0f10"));
  EXPECT_EQ(Foo::kBig, enum64_view.Read());
  EXPECT_TRUE(UpdateFromText(enum64_view, "0x7654321"));
  EXPECT_EQ(static_cast<Foo>(0x7654321), enum64_view.Read());
  EXPECT_FALSE(UpdateFromText(enum64_view, "0y0"));
  EXPECT_EQ(static_cast<Foo>(0x7654321), enum64_view.Read());
  EXPECT_FALSE(UpdateFromText(enum64_view, "-x"));
  EXPECT_EQ(static_cast<Foo>(0x7654321), enum64_view.Read());
  EXPECT_TRUE(UpdateFromText(enum64_view, "-0x8000_0000_0000_0000"));
  EXPECT_EQ(Foo::kMin, enum64_view.Read());
}

TEST(EnumView, WriteToText) {
  ::std::vector</**/ ::std::uint8_t> bytes = {
      {0x10, 0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08}};
  const auto enum64_view =
      FooViewN<64>{ReadWriteContiguousBuffer{bytes.data(), 8}};
  EXPECT_EQ("kReallyBig", WriteToString(enum64_view));
  EXPECT_EQ("kReallyBig  # 651345242494996240",
            WriteToString(enum64_view, TextOutputOptions().WithComments(true)));
  EXPECT_EQ("kReallyBig  # 0x90a0b0c0d0e0f10",
            WriteToString(
                enum64_view,
                TextOutputOptions().WithComments(true).WithNumericBase(16)));
  enum64_view.Write(static_cast<Foo>(123));
  EXPECT_EQ("123", WriteToString(enum64_view));
  EXPECT_EQ("123",
            WriteToString(enum64_view, TextOutputOptions().WithComments(true)));
  EXPECT_EQ("0x7b",
            WriteToString(
                enum64_view,
                TextOutputOptions().WithComments(true).WithNumericBase(16)));
}

}  // namespace test
}  // namespace support
}  // namespace emboss
