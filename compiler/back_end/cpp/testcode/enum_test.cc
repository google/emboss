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

// Tests for the generated View class for Container and Box from
// nested_structure.emb.
//
// These tests check that nested structures work.
#include <array>
#include <cstdint>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>

#include "gtest/gtest.h"
#include "testdata/enum.emb.h"

namespace emboss {
namespace test {
namespace {

static_assert(
    ::std::is_same</**/ ::std::uint64_t,
                   ::std::underlying_type<OnlyShortValues>::type>::value,
    "Emboss enums should default to 64-bit.");
static_assert(
    ::std::is_same</**/ ::std::int64_t,
                   ::std::underlying_type<OnlyShortSignedValues>::type>::value,
    "Emboss enums should default to 64-bit.");
static_assert(
    ::std::is_same</**/ ::std::int64_t,
                   ::std::underlying_type<ExplicitlySigned>::type>::value,
    "Emboss enum with explicit is_signed = true should be signed.");
static_assert(
    ::std::is_same</**/ ::std::int64_t,
                   ::std::underlying_type<ExplicitlySigned>::type>::value,
    "Emboss enum with explicit is_signed = true should be signed.");
static_assert(
    ::std::is_same</**/ ::std::uint64_t,
                   ::std::underlying_type<ExplicitlySized64>::type>::value,
    "Emboss enum with maximum_bits = 64 should be uint64_t.");
static_assert(
    ::std::is_same</**/ ::std::uint32_t,
                   ::std::underlying_type<ExplicitlySized32>::type>::value,
    "Emboss enum with maximum_bits = 32 should be uint32_t.");
static_assert(
    ::std::is_same</**/ ::std::uint16_t,
                   ::std::underlying_type<ExplicitlySized16>::type>::value,
    "Emboss enum with maximum_bits = 16 should be uint16_t.");
static_assert(
    ::std::is_same</**/ ::std::uint8_t,
                   ::std::underlying_type<ExplicitlySized8>::type>::value,
    "Emboss enum with maximum_bits = 8 should be uint8_t.");
static_assert(
    ::std::is_same<
        /**/ ::std::int32_t,
        ::std::underlying_type<ExplicitlySizedAndSigned>::type>::value,
    "Emboss enum with maximum_bits = 32 and is_signed = true should be "
    "int32_t.");
static_assert(
    ::std::is_same</**/ ::std::uint16_t,
                   ::std::underlying_type<ExplicitlySized12>::type>::value,
    "Emboss enum with maximum_bits = 12 should be uint16_t.");

alignas(8) static const ::std::uint8_t kManifestEntry[14] = {
    0x01,                          // 0:1  Kind  kind == SPROCKET
    0x04, 0x00, 0x00, 0x00,        // 1:5  UInt  count == 4
    0x02, 0x00, 0x00, 0x00,        // 5:9  Kind  wide_kind == GEEGAW
    0x20, 0x00, 0x00, 0x00, 0x00,  // 9:14 Kind  wide_kind_in_bits == GEEGAW
};

TEST(ManifestEntryView, CanReadKind) {
  auto view = MakeAlignedManifestEntryView<const ::std::uint8_t, 8>(
      kManifestEntry, sizeof kManifestEntry);
  EXPECT_EQ(Kind::SPROCKET, view.kind().Read());
  EXPECT_EQ(Kind::GEEGAW, view.wide_kind().Read());
  EXPECT_EQ(Kind::GEEGAW, view.wide_kind_in_bits().Read());
}

TEST(ManifestEntryView, Equals) {
  ::std::array</**/ ::std::uint8_t, sizeof kManifestEntry> buf_x;
  ::std::array</**/ ::std::uint8_t, sizeof kManifestEntry> buf_y;

  ::std::copy(kManifestEntry, kManifestEntry + sizeof kManifestEntry,
              buf_x.begin());
  ::std::copy(kManifestEntry, kManifestEntry + sizeof kManifestEntry,
              buf_y.begin());

  EXPECT_EQ(buf_x, buf_y);
  auto x = MakeManifestEntryView(&buf_x);
  auto x_const = MakeManifestEntryView(
      static_cast</**/ ::std::array</**/ ::std::uint8_t, sizeof kManifestEntry>
                      *>(&buf_x));
  auto y = MakeManifestEntryView(&buf_y);

  EXPECT_TRUE(x.Equals(x));
  EXPECT_TRUE(x.UncheckedEquals(x));
  EXPECT_TRUE(y.Equals(y));
  EXPECT_TRUE(y.UncheckedEquals(y));

  EXPECT_TRUE(x.Equals(y));
  EXPECT_TRUE(x.UncheckedEquals(y));
  EXPECT_TRUE(y.Equals(x));
  EXPECT_TRUE(y.UncheckedEquals(x));

  EXPECT_TRUE(x_const.Equals(y));
  EXPECT_TRUE(x_const.UncheckedEquals(y));
  EXPECT_TRUE(y.Equals(x_const));
  EXPECT_TRUE(y.UncheckedEquals(x_const));

  ++buf_y[1];
  EXPECT_FALSE(x.Equals(y));
  EXPECT_FALSE(x.UncheckedEquals(y));
  EXPECT_FALSE(y.Equals(x));
  EXPECT_FALSE(y.UncheckedEquals(x));

  EXPECT_FALSE(x_const.Equals(y));
  EXPECT_FALSE(x_const.UncheckedEquals(y));
  EXPECT_FALSE(y.Equals(x_const));
  EXPECT_FALSE(y.UncheckedEquals(x_const));
}

static const ::std::uint8_t kManifestEntryEdgeCases[14] = {
    0xff,                          // 0:1  Kind  kind == 0x0f
    0x04, 0x00, 0x00, 0x00,        // 1:5  UInt  count == 4
    0xff, 0xff, 0xff, 0xff,        // 5:9  Kind  wide_kind == MAX32BIT
    0xf0, 0xff, 0xff, 0xff, 0x0f,  // 9:14 Kind  wide_kind_in_bits == GEEGAW
};

TEST(ManifestEntryView, EdgeCases) {
  auto view = ManifestEntryView(kManifestEntryEdgeCases,
                                sizeof kManifestEntryEdgeCases);
  EXPECT_EQ(static_cast<Kind>(255), view.kind().Read());
  EXPECT_EQ(255U, static_cast</**/ ::std::uint64_t>(view.kind().Read()));
  EXPECT_EQ(Kind::MAX32BIT, view.wide_kind().Read());
  EXPECT_EQ(Kind::MAX32BIT, view.wide_kind_in_bits().Read());
}

TEST(Kind, Values) {
  EXPECT_EQ(static_cast<Kind>(0), Kind::WIDGET);
  EXPECT_EQ(static_cast<Kind>(1), Kind::SPROCKET);
  EXPECT_EQ(static_cast<Kind>(2), Kind::GEEGAW);
  EXPECT_EQ(
      static_cast<Kind>(static_cast</**/ ::std::uint64_t>(Kind::GEEGAW) +
                        static_cast</**/ ::std::uint64_t>(Kind::SPROCKET)),
      Kind::COMPUTED);
  EXPECT_EQ(static_cast<Kind>(4294967295), Kind::MAX32BIT);
}

TEST(ManifestEntryWriter, CanWriteKind) {
  ::std::uint8_t buffer[sizeof kManifestEntry] = {0};
  auto writer = ManifestEntryWriter(buffer, sizeof buffer);
  writer.kind().Write(Kind::SPROCKET);
  writer.count().Write(4);
  writer.wide_kind().Write(Kind::GEEGAW);
  writer.wide_kind_in_bits().Write(Kind::GEEGAW);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(
                kManifestEntry, kManifestEntry + sizeof kManifestEntry),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));

#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(writer.kind().Write(Kind::LARGE_VALUE), "");
#endif  // EMBOSS_CHECK_ABORTS
  writer.kind().Write(static_cast<Kind>(0xff));
  EXPECT_EQ(static_cast<Kind>(0xff), writer.kind().Read());
  EXPECT_EQ(0xff, buffer[0]);
  // The writes to kind() should not have overwritten the next field.
  EXPECT_EQ(0x04, buffer[1]);
  writer.wide_kind().Write(Kind::MAX32BIT);
  writer.wide_kind_in_bits().Write(Kind::MAX32BIT);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(
                kManifestEntryEdgeCases,
                kManifestEntryEdgeCases + sizeof kManifestEntryEdgeCases),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(Kind, EnumToName) {
  EXPECT_EQ("WIDGET", TryToGetNameFromEnum(Kind::WIDGET));
  EXPECT_EQ("SPROCKET", TryToGetNameFromEnum(Kind::SPROCKET));
  EXPECT_EQ("MAX32BIT", TryToGetNameFromEnum(Kind::MAX32BIT));
  // In the case of duplicate values, the first one listed in the .emb is
  // chosen.
  // TODO(bolms): Decide if this policy is good enough, or if the choice should
  // be explicit.
  EXPECT_EQ("LARGE_VALUE", TryToGetNameFromEnum(Kind::LARGE_VALUE));
  EXPECT_EQ("LARGE_VALUE", TryToGetNameFromEnum(Kind::DUPLICATE_LARGE_VALUE));
  EXPECT_EQ(nullptr, TryToGetNameFromEnum(static_cast<Kind>(100)));
}

TEST(Kind, EnumToOstream) {
  {
    ::std::ostringstream s;
    s << Kind::WIDGET;
    EXPECT_EQ("WIDGET", s.str());
  }
  {
    ::std::ostringstream s;
    s << Kind::MAX32BIT;
    EXPECT_EQ("MAX32BIT", s.str());
  }
  {
    ::std::ostringstream s;
    s << static_cast<Kind>(10005);
    EXPECT_EQ("10005", s.str());
  }
  {
    ::std::ostringstream s;
    s << Kind::WIDGET << ":" << Kind::SPROCKET;
    EXPECT_EQ("WIDGET:SPROCKET", s.str());
  }
}

TEST(ManifestEntryView, CopyFrom) {
  ::std::array</**/ ::std::uint8_t, 14> buf_x = {0x00};
  ::std::array</**/ ::std::uint8_t, 14> buf_y = {0xff};

  auto x = MakeManifestEntryView(&buf_x);
  auto y = MakeManifestEntryView(&buf_y);

  EXPECT_NE(x.kind().Read(), y.kind().Read());
  x.kind().CopyFrom(y.kind());
  EXPECT_EQ(x.kind().Read(), y.kind().Read());
}

TEST(ManifestEntryView, TryToCopyFrom) {
  ::std::array</**/ ::std::uint8_t, 14> buf_x = {0x00};
  ::std::array</**/ ::std::uint8_t, 14> buf_y = {0xff};

  auto x = MakeManifestEntryView(&buf_x);
  auto y = MakeManifestEntryView(&buf_y);

  EXPECT_NE(x.kind().Read(), y.kind().Read());
  EXPECT_TRUE(x.kind().TryToCopyFrom(y.kind()));
  EXPECT_EQ(x.kind().Read(), y.kind().Read());
}

TEST(Kind, NameToEnum) {
  Kind result;
  EXPECT_TRUE(TryToGetEnumFromName("WIDGET", &result));
  EXPECT_EQ(Kind::WIDGET, result);
  EXPECT_TRUE(TryToGetEnumFromName("SPROCKET", &result));
  EXPECT_EQ(Kind::SPROCKET, result);
  EXPECT_TRUE(TryToGetEnumFromName("MAX32BIT", &result));
  EXPECT_EQ(Kind::MAX32BIT, result);
  EXPECT_TRUE(TryToGetEnumFromName("LARGE_VALUE", &result));
  EXPECT_EQ(Kind::LARGE_VALUE, result);
  EXPECT_EQ(Kind::DUPLICATE_LARGE_VALUE, result);
  EXPECT_TRUE(TryToGetEnumFromName("DUPLICATE_LARGE_VALUE", &result));
  EXPECT_EQ(Kind::LARGE_VALUE, result);
  EXPECT_EQ(Kind::DUPLICATE_LARGE_VALUE, result);

  result = Kind::WIDGET;
  EXPECT_FALSE(TryToGetEnumFromName("MAX32BIT ", &result));
  EXPECT_EQ(Kind::WIDGET, result);
  EXPECT_FALSE(TryToGetEnumFromName("", &result));
  EXPECT_EQ(Kind::WIDGET, result);
  EXPECT_FALSE(TryToGetEnumFromName(nullptr, &result));
  EXPECT_EQ(Kind::WIDGET, result);
  EXPECT_FALSE(TryToGetEnumFromName(" MAX32BIT", &result));
  EXPECT_EQ(Kind::WIDGET, result);
  EXPECT_FALSE(TryToGetEnumFromName("MAX32BI", &result));
  EXPECT_EQ(Kind::WIDGET, result);
  EXPECT_FALSE(TryToGetEnumFromName("max32bit", &result));
  EXPECT_EQ(Kind::WIDGET, result);
}

TEST(Kind, Type) {
  EXPECT_TRUE((::std::is_same</**/ ::std::uint64_t,
                              ::std::underlying_type<Kind>::type>::value));
}

TEST(Signed, Type) {
  EXPECT_TRUE((::std::is_same</**/ ::std::int64_t,
                              ::std::underlying_type<Signed>::type>::value));
}

TEST(Foo, EnumsExposedFromView) {
  EXPECT_EQ(StructContainingEnum::Status::OK,
            StructContainingEnumView::Status::OK);
  EXPECT_EQ(StructContainingEnum::Status::FAILURE,
            StructContainingEnumView::Status::FAILURE);
}

TEST(Kind, EnumIsKnown) {
  EXPECT_TRUE(EnumIsKnown(Kind::WIDGET));
  EXPECT_TRUE(EnumIsKnown(Kind::SPROCKET));
  EXPECT_TRUE(EnumIsKnown(Kind::GEEGAW));
  EXPECT_TRUE(EnumIsKnown(Kind::COMPUTED));
  EXPECT_TRUE(EnumIsKnown(Kind::LARGE_VALUE));
  EXPECT_TRUE(EnumIsKnown(Kind::DUPLICATE_LARGE_VALUE));
  EXPECT_TRUE(EnumIsKnown(Kind::MAX32BIT));
  EXPECT_TRUE(EnumIsKnown(Kind::MAX64BIT));
  EXPECT_FALSE(EnumIsKnown(static_cast<Kind>(12345)));
}

}  // namespace
}  // namespace test
}  // namespace emboss
