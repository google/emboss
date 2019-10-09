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

// Tests of generated code for virtual fields.
#include <stdint.h>

#include <type_traits>
#include <utility>
#include <vector>

#include "gtest/gtest.h"
#include "testdata/virtual_field.emb.h"

namespace emboss {
namespace test {
namespace {

// Check that the constant methods are generated as constexpr free functions in
// the type's aliased namespace, and have the appropriate values.
static_assert(StructureWithConstants::ten() == 10,
              "StructureWithConstants::ten() == 10");
static_assert(StructureWithConstants::twenty() == 20,
              "StructureWithConstants::twenty() == 20");
static_assert(StructureWithConstants::four_billion() == 4000000000U,
              "StructureWithConstants::four_billion() == 4000000000U");
static_assert(StructureWithConstants::ten_billion() == 10000000000L,
              "StructureWithConstants::ten_billion() == 10000000000L");
static_assert(StructureWithConstants::minus_ten_billion() == -10000000000L,
              "StructureWithConstants::minus_ten_billion() == -10000000000L");

// Check the return types of the static Read methods.
static_assert(::std::is_same</**/ ::std::int32_t,
                             decltype(StructureWithConstants::ten())>::value,
              "StructureWithConstants::ten() returns ::std::int8_t");
static_assert(::std::is_same</**/ ::std::int32_t,
                             decltype(StructureWithConstants::twenty())>::value,
              "StructureWithConstants::twenty() returns ::std::int8_t");
static_assert(
    ::std::is_same</**/ ::std::uint32_t,
                   decltype(StructureWithConstants::four_billion())>::value,
    "StructureWithConstants::four_billion() returns ::std::uint32_t");
static_assert(
    ::std::is_same</**/ ::std::int64_t,
                   decltype(StructureWithConstants::ten_billion())>::value,
    "StructureWithConstants::ten_billion() returns ::std::int64_t");

TEST(Constants, ValuesOnView) {
  ::std::array<char, 4> values = {0, 0, 0, 0};
  const auto view = MakeStructureWithConstantsView(&values);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(10, view.ten().Read());
  EXPECT_EQ(10, view.alias_of_ten().Read());
  EXPECT_EQ(10, view.alias_of_alias_of_ten().Read());
  EXPECT_EQ(20, view.twenty().Read());
  EXPECT_EQ(4000000000U, view.four_billion().Read());
  EXPECT_EQ(10000000000L, view.ten_billion().Read());
  EXPECT_EQ(0U, view.value().Read());
  EXPECT_EQ(0U, view.alias_of_value().Read());
  EXPECT_EQ(0U, view.alias_of_alias_of_value().Read());
  view.alias_of_alias_of_value().Write(10);
  EXPECT_EQ(10U, view.value().Read());
  EXPECT_EQ(10U, view.alias_of_value().Read());
  EXPECT_EQ(10U, view.alias_of_alias_of_value().Read());
}

TEST(Computed, Values) {
  ::std::array<char, 8> values = {5, 0, 0, 0, 50, 0, 0, 0};
  const auto view = MakeStructureWithComputedValuesView(&values);
  EXPECT_EQ(5U, view.value().Read());
  EXPECT_EQ(10U, view.doubled().Read());
  EXPECT_EQ(15U, view.plus_ten().Read());
  EXPECT_EQ(50, view.value2().Read());
  EXPECT_EQ(100, view.signed_doubled().Read());
  EXPECT_EQ(60, view.signed_plus_ten().Read());
  EXPECT_EQ(250, view.product().Read());
  view.value2().Write(-50);
  EXPECT_EQ(-100, view.signed_doubled().Read());
  EXPECT_EQ(-40, view.signed_plus_ten().Read());
  EXPECT_EQ(-250, view.product().Read());
}

#if EMBOSS_CHECK_ABORTS
TEST(Computed, ReadFailsWhenUnderlyingFieldIsNotOk) {
  ::std::array<char, 0> values = {};
  const auto view = MakeStructureWithComputedValuesView(&values);
  EXPECT_DEATH(view.value().Read(), "");
  EXPECT_DEATH(view.doubled().Read(), "");
}
#endif  // EMBOSS_CHECK_ABORTS

// Check the return types of nonstatic Read methods.
static_assert(
    ::std::is_same</**/ ::std::int64_t,
                   decltype(MakeStructureWithComputedValuesView("x", 1)
                                .doubled()
                                .Read())>::value,
    "StructureWithComputedValuesView::doubled().Read() should return "
    "::std::int64_t.");
// Check the return types of nonstatic Read methods.
static_assert(
    ::std::is_same</**/ ::std::int64_t,
                   decltype(MakeStructureWithComputedValuesView("x", 1)
                                .product()
                                .Read())>::value,
    "StructureWithComputedValuesView::product().Read() should return "
    "::std::int64_t.");

TEST(Constants, TextFormatWrite) {
  ::std::array<char, 4> values = {5, 0, 0, 0};
  const auto view = MakeStructureWithConstantsView(&values);
  // TODO(bolms): Provide a way of marking fields as "not for text format," so
  // that end users can choose whether to use an alias or an original field or
  // both in the text format.
  EXPECT_EQ("{ value: 5, alias_of_value: 5, alias_of_alias_of_value: 5 }",
            ::emboss::WriteToString(view));
  EXPECT_EQ(
      "{\n"
      "  # ten: 10  # 0xa\n"
      "  # twenty: 20  # 0x14\n"
      "  # four_billion: 4_000_000_000  # 0xee6b_2800\n"
      "  # ten_billion: 10_000_000_000  # 0x2_540b_e400\n"
      "  # minus_ten_billion: -10_000_000_000  # -0x2_540b_e400\n"
      "  value: 5  # 0x5\n"
      "  alias_of_value: 5  # 0x5\n"
      "  alias_of_alias_of_value: 5  # 0x5\n"
      "  # alias_of_ten: 10  # 0xa\n"
      "  # alias_of_alias_of_ten: 10  # 0xa\n"
      "}",
      ::emboss::WriteToString(view, ::emboss::MultilineText()));
}

TEST(Computed, TextFormatWrite) {
  ::std::array<char, 8> values = {5, 0, 0, 0, 50, 0, 0, 0};
  const auto view = MakeStructureWithComputedValuesView(&values);
  EXPECT_EQ("{ value: 5, plus_ten: 15, value2: 50, signed_plus_ten: 60 }",
            ::emboss::WriteToString(view));
  EXPECT_EQ(
      "{\n"
      "  value: 5  # 0x5\n"
      "  # doubled: 10  # 0xa\n"
      "  plus_ten: 15  # 0xf\n"
      "  value2: 50  # 0x32\n"
      "  # signed_doubled: 100  # 0x64\n"
      "  signed_plus_ten: 60  # 0x3c\n"
      "  # product: 250  # 0xfa\n"
      "}",
      ::emboss::WriteToString(view, ::emboss::MultilineText()));
}

TEST(Constants, TextFormatRead) {
  ::std::array<char, 4> values = {5, 0, 0, 0};
  const auto view = MakeStructureWithConstantsView(&values);
  EXPECT_TRUE(::emboss::UpdateFromText(view, "{ value: 50 }"));
  EXPECT_EQ(50, values[0]);
  EXPECT_FALSE(::emboss::UpdateFromText(view, "{ ten: 50 }"));
  // TODO(bolms): Should this be allowed?
  EXPECT_FALSE(::emboss::UpdateFromText(view, "{ ten: 10 }"));
}

TEST(Computed, TextFormatRead) {
  ::std::array<char, 8> values = {5, 0, 0, 0, 50, 0, 0, 0};
  const auto view = MakeStructureWithComputedValuesView(&values);
  EXPECT_TRUE(::emboss::UpdateFromText(view, "{ value: 50, value2: 5 }"));
  EXPECT_EQ(50, values[0]);
  EXPECT_EQ(5, values[4]);
  EXPECT_FALSE(::emboss::UpdateFromText(view, "{ product: 10 }"));
  // TODO(bolms): Make Emboss automatically infer write_transform for
  // easily-reversible cases like `field * 2`.
  EXPECT_FALSE(::emboss::UpdateFromText(view, "{ doubled: 10 }"));
}

TEST(ConditionalVirtual, ConditionChecks) {
  ::std::array<char, 4> values = {5, 0, 0, 0};
  const auto view = MakeStructureWithConditionalValueView(&values);
  EXPECT_TRUE(view.has_two_x().Value());
  EXPECT_TRUE(view.has_x_plus_one().Value());
  EXPECT_EQ(10, view.two_x().Read());
  EXPECT_EQ(6, view.x_plus_one().Read());
  EXPECT_EQ(10, view.two_x().UncheckedRead());
  EXPECT_EQ(6, view.x_plus_one().UncheckedRead());
  view.x().Write(0x80000000U);
  EXPECT_FALSE(view.has_two_x().Value());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(view.two_x().Read(), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_TRUE(view.has_x_plus_one().Value());
  EXPECT_EQ(0x80000001U, view.x_plus_one().Read());
}

TEST(ConditionalVirtual, UncheckedRead) {
  ::std::array<char, 4> values = {5, 0, 0, 0};
  const auto view = MakeStructureWithConditionalValueView(&values[0], 1);
  EXPECT_FALSE(view.Ok());
  EXPECT_FALSE(view.x().Ok());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(view.two_x().Read(), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_EQ(0, view.two_x().UncheckedRead());
}

TEST(ConditionalVirtual, TextFormatWrite) {
  ::std::array<unsigned char, 4> values = {0, 0, 0, 0x80};
  const auto view = MakeStructureWithConditionalValueView(&values);
  EXPECT_EQ("{ x: 2147483648, x_plus_one: 2147483649 }",
            ::emboss::WriteToString(view));
  EXPECT_EQ(
      "{\n"
      "  x: 2_147_483_648  # 0x8000_0000\n"
      "  x_plus_one: 2_147_483_649  # 0x8000_0001\n"
      "}",
      ::emboss::WriteToString(view, ::emboss::MultilineText()));
  view.x().Write(5);
  EXPECT_EQ("{ x: 5, x_plus_one: 6 }", ::emboss::WriteToString(view));
  EXPECT_EQ(
      "{\n"
      "  x: 5  # 0x5\n"
      "  # two_x: 10  # 0xa\n"
      "  x_plus_one: 6  # 0x6\n"
      "}",
      ::emboss::WriteToString(view, ::emboss::MultilineText()));
}

TEST(VirtualInCondition, ConditionCheck) {
  ::std::array<char, 8> values = {5, 0, 0, 0, 50, 0, 0, 0};
  const auto view = MakeStructureWithValueInConditionView(&values);
  EXPECT_TRUE(view.has_if_two_x_lt_100().Value());
  view.x().Write(75);
  EXPECT_FALSE(view.has_if_two_x_lt_100().Value());
}

TEST(VirtualInLocation, Offset) {
  ::std::array<char, 8> values = {5, 0, 0, 0, 50, 0, 0, 0};
  const auto view = MakeStructureWithValuesInLocationView(&values);
  EXPECT_FALSE(view.Ok());
  view.x().Write(2);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(50U, view.offset_two_x().Read());
  EXPECT_EQ(50U, view.size_two_x().Read());
  view.x().Write(1);
  EXPECT_FALSE(view.Ok());
  EXPECT_EQ(50 * 0x10000U, view.offset_two_x().Read());
  view.x().Write(0);
  EXPECT_EQ(0U, view.offset_two_x().Read());
}

TEST(BooleanVirtual, TrueAndFalse) {
  ::std::array<char, 4> values = {5, 0, 0, 0};
  const auto view = MakeStructureWithBoolValueView(&values);
  EXPECT_TRUE(view.Ok());
  EXPECT_FALSE(view.x_is_ten().Read());
  view.x().Write(10);
  EXPECT_TRUE(view.x_is_ten().Read());
}

TEST(EnumVirtual, SmallAndLarge) {
  ::std::array<char, 4> values = {5, 0, 0, 0};
  const auto view = MakeStructureWithEnumValueView(&values);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(StructureWithEnumValue::Category::SMALL, view.x_size().Read());
  view.x().Write(100);
  EXPECT_EQ(StructureWithEnumValue::Category::LARGE, view.x_size().Read());
}

TEST(BitsVirtual, Sum) {
  ::std::array<char, 4> values = {5, 0, 10, 0};
  const auto view = MakeStructureWithBitsWithValueView(&values);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(5, view.b().a().Read());
  EXPECT_EQ(5, view.alias_of_b_a().Read());
  EXPECT_EQ(10, view.b().b().Read());
  EXPECT_EQ(15, view.b().sum().Read());
  EXPECT_EQ(15, view.alias_of_b_sum().Read());
  view.alias_of_b_a().Write(20);
  EXPECT_EQ(20, view.b().a().Read());
  EXPECT_EQ(20, view.alias_of_b_a().Read());
  EXPECT_EQ(20, values[0]);
}

TEST(ForeignConstants, ForeignConstants) {
  static_assert(StructureUsingForeignConstants::one_hundred() == 100,
                "StructureUsingForeignConstants::one_hundred() == 100");
  ::std::array<char, 14> values = {5, 0, 0, 0, 10, 0, 0, 0, 15, 0, 20, 0, 0, 0};
  const auto view = MakeStructureUsingForeignConstantsView(&values);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(20U, view.x().Read());
  EXPECT_EQ(100, view.one_hundred().Read());
}

TEST(HasField, HasField) {
  ::std::array<char, 3> values = {0, 0, 0};
  const auto view = MakeHasFieldView(&values);
  EXPECT_FALSE(view.Ok());  // There is not enough information to determine if
                            // view.has_y(), so the view is not Ok().
  view.z().Write(11);
  EXPECT_TRUE(view.Ok());
  EXPECT_FALSE(view.has_y().Value());
  EXPECT_TRUE(view.has_x().Value());
  EXPECT_FALSE(view.x().has_y().Value());
  EXPECT_FALSE(view.x_has_y().Read());
  EXPECT_FALSE(view.x_has_y().UncheckedRead());
  view.x().v().Write(11);
  EXPECT_TRUE(view.Ok());
  EXPECT_TRUE(view.has_y().Value());
  EXPECT_TRUE(view.has_x().Value());
  EXPECT_TRUE(view.x().has_y().Value());
  EXPECT_TRUE(view.x_has_y().Read());
  EXPECT_TRUE(view.x_has_y().UncheckedRead());
}

TEST(RestrictedAlias, RestrictedAlias) {
  ::std::array<char, 5> values = {1, 2, 3, 4, 5};
  const auto view = MakeRestrictedAliasView(&values);
  EXPECT_TRUE(view.Ok());
  EXPECT_TRUE(view.has_a_b().Value());
  EXPECT_TRUE(view.a_b().Ok());
  EXPECT_FALSE(view.has_a_b_alias().Value());
  EXPECT_FALSE(view.a_b_alias().Ok());
  EXPECT_FALSE(view.a_b_alias().a().Ok());
  EXPECT_FALSE(view.a_b_alias().b().Ok());
  view.alias_switch().Write(11);
  EXPECT_TRUE(view.has_a_b().Value());
  EXPECT_TRUE(view.a_b().Ok());
  EXPECT_TRUE(view.has_a_b_alias().Value());
  EXPECT_TRUE(view.a_b_alias().Ok());
}

TEST(VirtualWithConditionalComponent, ReadWhenAllPresent) {
  ::std::array<char, 2> values = {0, 0};
  const auto view = MakeVirtualUnconditionallyUsesConditionalView(&values);
  EXPECT_TRUE(view.x_nor_xc().Read());
  EXPECT_TRUE(view.x_nor_xc().UncheckedRead());
}

TEST(VirtualWithConditionalComponent, ReadWhenNotAllPresent) {
  ::std::array<char, 2> values = {1, 0};
  const auto view = MakeVirtualUnconditionallyUsesConditionalView(&values);
  EXPECT_FALSE(view.x_nor_xc().Read());
  EXPECT_FALSE(view.x_nor_xc().UncheckedRead());
}

TEST(IntrinsicSize, SizeInBytes) {
  ::std::array<char, 1> values = {10};
  const auto view = MakeUsesSizeView(&values);
  EXPECT_TRUE(view.Ok());
  EXPECT_TRUE(view.IntrinsicSizeInBytes().Ok());
  EXPECT_EQ(1, view.IntrinsicSizeInBytes().Read());
  EXPECT_EQ(1, UsesSizeView::IntrinsicSizeInBytes().Read());
  EXPECT_EQ(1, UsesSize::IntrinsicSizeInBytes());
  EXPECT_TRUE(view.r().IntrinsicSizeInBits().Ok());
  EXPECT_EQ(8, view.r().IntrinsicSizeInBits().Read());
  EXPECT_EQ(8, UsesSize::R::IntrinsicSizeInBits());
  EXPECT_EQ(values[0], view.r().q().Read());
  EXPECT_EQ(values[0] + 1, view.r_q_plus_byte_size().Read());
  EXPECT_EQ(values[0] + 8, view.r().q_plus_bit_size().Read());
}

TEST(VirtualFields, SizeInBytes) {
  const ::std::array</**/ ::std::uint8_t, 8> values = {0x11, 0x11, 0x11, 0x11,
                                                       0x22, 0x22, 0x22, 0x22};
  const auto view = MakeUsesExternalSizeView(&values);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(8U, view.SizeInBytes());
  EXPECT_EQ(view.x().SizeInBytes(), 4U);
  EXPECT_EQ(view.y().SizeInBytes(), 4U);
  EXPECT_EQ(view.x().value().Read(), 0x11111111U);
  EXPECT_EQ(view.y().value().Read(), 0x22222222U);
  EXPECT_TRUE(view.IntrinsicSizeInBytes().Ok());
  EXPECT_EQ(8, UsesExternalSizeView::IntrinsicSizeInBytes().Read());
  EXPECT_EQ(8, UsesExternalSize::MaxSizeInBytes());
}

TEST(WriteTransform, Write) {
  ::std::array<char, 1> values = {0};
  const auto view = MakeImplicitWriteBackView(&values);

  view.x_plus_ten().Write(11);
  EXPECT_EQ(1, view.x().Read());
  EXPECT_EQ(11, view.x_plus_ten().Read());

  view.ten_plus_x().Write(12);
  EXPECT_EQ(2, view.x().Read());
  EXPECT_EQ(12, view.ten_plus_x().Read());

  EXPECT_TRUE((::std::is_same<decltype(view.x_minus_ten())::ValueType,
                              ::std::int32_t>::value));

  view.x_minus_ten().Write(-7);
  EXPECT_EQ(3, view.x().Read());
  EXPECT_EQ(-7, view.x_minus_ten().Read());

  view.ten_minus_x().Write(6);
  EXPECT_EQ(4, view.x().Read());
  EXPECT_EQ(6, view.ten_minus_x().Read());

  view.ten_minus_x_plus_ten().Write(4);
  EXPECT_EQ(16, view.x().Read());
  EXPECT_EQ(4, view.ten_minus_x_plus_ten().Read());
}

TEST(WriteTransform, CouldWriteValue) {
  ::std::array<char, 1> values = {0};
  const auto view = MakeImplicitWriteBackView(&values);
  EXPECT_EQ(0, view.x().Read());
  // x is UInt:8, so has range [0, 255].

  EXPECT_FALSE(view.x_plus_ten().CouldWriteValue(9));
  EXPECT_TRUE(view.x_plus_ten().CouldWriteValue(10));
  EXPECT_TRUE(view.x_plus_ten().CouldWriteValue(265));
  EXPECT_FALSE(view.x_plus_ten().CouldWriteValue(266));

  EXPECT_FALSE(view.ten_plus_x().CouldWriteValue(9));
  EXPECT_TRUE(view.ten_plus_x().CouldWriteValue(10));
  EXPECT_TRUE(view.ten_plus_x().CouldWriteValue(265));
  EXPECT_FALSE(view.ten_plus_x().CouldWriteValue(266));

  EXPECT_FALSE(view.x_minus_ten().CouldWriteValue(-11));
  EXPECT_TRUE(view.x_minus_ten().CouldWriteValue(-10));
  EXPECT_TRUE(view.x_minus_ten().CouldWriteValue(245));
  EXPECT_FALSE(view.x_minus_ten().CouldWriteValue(246));

  EXPECT_FALSE(view.ten_minus_x().CouldWriteValue(-246));
  EXPECT_TRUE(view.ten_minus_x().CouldWriteValue(-245));
  EXPECT_TRUE(view.ten_minus_x().CouldWriteValue(10));
  EXPECT_FALSE(view.ten_minus_x().CouldWriteValue(11));

  EXPECT_FALSE(view.ten_minus_x_plus_ten().CouldWriteValue(-236));
  EXPECT_TRUE(view.ten_minus_x_plus_ten().CouldWriteValue(-235));
  EXPECT_TRUE(view.ten_minus_x_plus_ten().CouldWriteValue(20));
  EXPECT_FALSE(view.ten_minus_x_plus_ten().CouldWriteValue(21));
}

}  // namespace
}  // namespace test
}  // namespace emboss
