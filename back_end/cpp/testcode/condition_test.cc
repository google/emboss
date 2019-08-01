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

// Tests to ensure that conditional fields work.
#include <stdint.h>

#include <vector>

#include "testdata/condition.emb.h"
#include <gtest/gtest.h>

namespace emboss {
namespace test {
namespace {

TEST(Conditional, WithConditionTrueFieldsAreOk) {
  uint8_t buffer[2] = {0, 0};
  auto writer = BasicConditionalWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  EXPECT_TRUE(writer.x().Ok());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(Conditional, WithConditionTrueAllFieldsAreReadable) {
  uint8_t buffer[2] = {0, 2};
  auto writer = BasicConditionalWriter(buffer, sizeof buffer);
  EXPECT_EQ(0, writer.x().Read());
  EXPECT_EQ(2, writer.xc().Read());
}

TEST(Conditional, WithConditionTrueConditionalFieldIsWritable) {
  uint8_t buffer1[2] = {0, 2};
  auto writer1 = BasicConditionalWriter(buffer1, sizeof buffer1);
  EXPECT_TRUE(writer1.xc().TryToWrite(3));
  EXPECT_EQ(3, buffer1[1]);

  uint8_t buffer2[2] = {0, 0};
  auto writer2 = BasicConditionalWriter(buffer2, sizeof buffer2);
  EXPECT_FALSE(writer2.xc().Equals(writer1.xc()));
  EXPECT_TRUE(writer2.xc().TryToCopyFrom(writer1.xc()));
  EXPECT_TRUE(writer2.xc().Equals(writer1.xc()));
  EXPECT_EQ(3, buffer2[1]);
}

TEST(Conditional, WithConditionFalseStructIsOkButConditionalFieldIsNot) {
  uint8_t buffer[2] = {1, 2};
  auto writer = BasicConditionalWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  EXPECT_TRUE(writer.x().Ok());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(Conditional, BasicConditionFalseReadCrashes) {
  uint8_t buffer[2] = {1, 2};
  auto writer = BasicConditionalWriter(buffer, sizeof buffer);
  EXPECT_DEATH(writer.xc().Read(), "");
}

TEST(Conditional, BasicConditionFalseWriteCrashes) {
  uint8_t buffer[2] = {1, 2};
  auto writer = BasicConditionalWriter(buffer, sizeof buffer);
  EXPECT_DEATH(writer.xc().Write(3), "");
}

TEST(Conditional, BasicConditionTrueSizeIncludesConditionalField) {
  uint8_t buffer[2] = {0, 2};
  auto writer = BasicConditionalWriter(buffer, sizeof buffer);
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_EQ(2, BasicConditional::MaxSizeInBytes());
  EXPECT_EQ(1, BasicConditional::MinSizeInBytes());
  EXPECT_EQ(2, writer.MaxSizeInBytes().Read());
  EXPECT_EQ(1, writer.MinSizeInBytes().Read());
}

TEST(Conditional, BasicConditionFalseSizeDoesNotIncludeConditionalField) {
  uint8_t buffer[2] = {1, 2};
  auto writer = BasicConditionalWriter(buffer, sizeof buffer);
  EXPECT_EQ(1, writer.SizeInBytes());
  EXPECT_EQ(2, writer.MaxSizeInBytes().Read());
  EXPECT_EQ(1, writer.MinSizeInBytes().Read());
}

TEST(Conditional, WithConditionFalseStructIsOkWhenBufferIsSmall) {
  uint8_t buffer[1] = {1};
  auto writer = BasicConditionalWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  EXPECT_TRUE(writer.x().Ok());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(Conditional, WithConditionTrueStructIsNotOkWhenBufferIsSmall) {
  uint8_t buffer[1] = {0};
  auto writer = BasicConditionalWriter(buffer, sizeof buffer);
  EXPECT_FALSE(writer.Ok());
  EXPECT_TRUE(writer.x().Ok());
  EXPECT_TRUE(writer.has_xc().Known());
  EXPECT_TRUE(writer.has_xc().Value());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(Conditional, WithNegativeConditionTrueFieldsAreOk) {
  uint8_t buffer[2] = {1, 0};
  auto writer = NegativeConditionalWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  EXPECT_TRUE(writer.x().Ok());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(Conditional, WithNegativeConditionTrueAllFieldsAreReadable) {
  uint8_t buffer[2] = {1, 2};
  auto writer = NegativeConditionalWriter(buffer, sizeof buffer);
  EXPECT_EQ(1, writer.x().Read());
  EXPECT_EQ(2, writer.xc().Read());
}

TEST(Conditional, WithNegativeConditionTrueConditionalFieldIsWritable) {
  uint8_t buffer1[2] = {1, 2};
  auto writer1 = NegativeConditionalWriter(buffer1, sizeof buffer1);
  EXPECT_TRUE(writer1.xc().TryToWrite(3));
  EXPECT_EQ(3, buffer1[1]);

  uint8_t buffer2[2] = {1, 0};
  auto writer2 = NegativeConditionalWriter(buffer2, sizeof buffer2);
  EXPECT_FALSE(writer2.xc().Equals(writer1.xc()));
  EXPECT_TRUE(writer2.xc().TryToCopyFrom(writer1.xc()));
  EXPECT_TRUE(writer2.xc().Equals(writer1.xc()));
  EXPECT_EQ(3, buffer2[1]);
}

TEST(Conditional,
     WithNegativeConditionFalseStructIsOkButConditionalFieldIsNot) {
  uint8_t buffer[2] = {0, 2};
  auto writer = NegativeConditionalWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  EXPECT_TRUE(writer.x().Ok());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(Conditional, NegativeConditionFalseReadCrashes) {
  uint8_t buffer1[2] = {0, 2};
  auto writer1 = NegativeConditionalWriter(buffer1, sizeof buffer1);
  EXPECT_DEATH(writer1.xc().Read(), "");

  uint8_t buffer2[2] = {0, 0};
  auto writer2 = BasicConditionalWriter(buffer2, sizeof buffer2);
  EXPECT_TRUE(writer2.xc().CouldWriteValue(2));
  EXPECT_EQ(writer2.xc().Read(), 0);
  EXPECT_FALSE(writer2.xc().TryToCopyFrom(writer1.xc()));
  EXPECT_EQ(writer2.xc().Read(), 0);
}

TEST(Conditional, NegativeConditionFalseWriteCrashes) {
  uint8_t buffer1[2] = {0, 2};
  auto writer1 = NegativeConditionalWriter(buffer1, sizeof buffer1);
  EXPECT_DEATH(writer1.xc().Write(3), "");

  uint8_t buffer2[2] = {0, 2};
  auto writer2 = NegativeConditionalWriter(buffer2, sizeof buffer2);
  EXPECT_FALSE(writer2.xc().TryToCopyFrom(writer1.xc()));
}

TEST(Conditional, NegativeConditionTrueSizeIncludesConditionalField) {
  uint8_t buffer[2] = {1, 2};
  auto writer = NegativeConditionalWriter(buffer, sizeof buffer);
  EXPECT_EQ(2, writer.SizeInBytes());
}

TEST(Conditional, NegativeConditionFalseSizeDoesNotIncludeConditionalField) {
  uint8_t buffer[2] = {0, 2};
  auto writer = NegativeConditionalWriter(buffer, sizeof buffer);
  EXPECT_EQ(1, writer.SizeInBytes());
}

TEST(Conditional, WithNegativeConditionFalseStructIsOkWhenBufferIsSmall) {
  uint8_t buffer[1] = {0};
  auto writer = NegativeConditionalWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  EXPECT_TRUE(writer.x().Ok());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(Conditional, WithNegativeConditionTrueStructIsNotOkWhenBufferIsSmall) {
  uint8_t buffer[1] = {1};
  auto writer = NegativeConditionalWriter(buffer, sizeof buffer);
  EXPECT_FALSE(writer.Ok());
  EXPECT_TRUE(writer.x().Ok());
  EXPECT_TRUE(writer.has_xc().Known());
  EXPECT_TRUE(writer.has_xc().Value());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(Conditional,
     SizeIncludesUnconditionalFieldsThatOverlapWithConditionalFields) {
  uint8_t buffer[2] = {1, 2};
  auto writer = ConditionalAndUnconditionalOverlappingFinalFieldWriter(
      buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  EXPECT_EQ(2, writer.SizeInBytes());
}

TEST(Conditional,
     SizeIsConstantWhenUnconditionalFieldsOverlapWithConditionalFields) {
  EXPECT_EQ(
      2, ConditionalAndUnconditionalOverlappingFinalFieldWriter::SizeInBytes());
}

TEST(Conditional, WhenConditionalFieldIsFirstSizeIsConstant) {
  EXPECT_EQ(2, ConditionalBasicConditionalFieldFirstWriter::SizeInBytes());
}

TEST(Conditional, WhenConditionIsFalseDynamicallyPlacedFieldDoesNotAffectSize) {
  uint8_t buffer[3] = {1, 0, 10};
  auto writer = ConditionalAndDynamicLocationWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  EXPECT_EQ(3, writer.SizeInBytes());
}

TEST(Conditional, WhenConditionIsTrueDynamicallyPlacedFieldDoesAffectSize) {
  uint8_t buffer[4] = {0, 0, 3, 0};
  auto writer = ConditionalAndDynamicLocationWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  EXPECT_EQ(4, writer.SizeInBytes());
}

TEST(Conditional, WhenConditionIsTrueDynamicallyPlacedFieldOutOfRangeIsError) {
  uint8_t buffer[3] = {0, 0, 3};
  auto writer = ConditionalAndDynamicLocationWriter(buffer, sizeof buffer);
  EXPECT_FALSE(writer.Ok());
  EXPECT_EQ(4, writer.SizeInBytes());
}

TEST(Conditional, ConditionUsesMinInt) {
  uint8_t buffer[2] = {0, 0};
  auto view = MakeConditionUsesMinIntView(buffer, sizeof buffer);
  EXPECT_TRUE(view.Ok());
  EXPECT_FALSE(view.has_xc().ValueOr(true));
  EXPECT_EQ(1, view.SizeInBytes());
  buffer[0] = 0x80;
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(-0x80, view.x().Read());
  EXPECT_TRUE(view.has_xc().ValueOr(false));
  EXPECT_EQ(2, view.SizeInBytes());
}

TEST(Conditional,
     StructWithNestedConditionIsNotOkWhenOuterConditionDoesNotExist) {
  uint8_t buffer[3] = {1, 0, 3};
  auto writer = NestedConditionalWriter(buffer, sizeof buffer);
  ASSERT_FALSE(writer.IntrinsicSizeInBytes().Ok());
  ASSERT_FALSE((writer.xc().Ok()));
  ASSERT_FALSE(writer.SizeIsKnown());
  ASSERT_FALSE(writer.IsComplete());
  ASSERT_FALSE(writer.Ok());
  ASSERT_TRUE(writer.has_xc().Known());
  ASSERT_FALSE(writer.has_xc().Value());
  ASSERT_FALSE(writer.has_xcc().Known());
}

TEST(Conditional,
     StructWithCorrectNestedConditionIsOkWhenOuterConditionDoesNotExist) {
  uint8_t buffer[3] = {1, 0, 3};
  auto writer = CorrectNestedConditionalWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.IsComplete());
  EXPECT_TRUE(writer.Ok());
  EXPECT_TRUE(writer.has_xc().Known());
  EXPECT_FALSE(writer.has_xc().Value());
  EXPECT_TRUE(writer.has_xcc().Known());
  EXPECT_FALSE(writer.has_xcc().Value());
  EXPECT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(1, writer.SizeInBytes());
}

TEST(Conditional, StructWithNestedConditionIsOkWhenOuterConditionExists) {
  uint8_t buffer[3] = {0, 1, 3};
  auto writer = NestedConditionalWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_TRUE(writer.has_xc().Known());
  EXPECT_TRUE(writer.has_xc().Value());
  EXPECT_TRUE(writer.has_xcc().Known());
  EXPECT_FALSE(writer.has_xcc().Value());
  EXPECT_EQ(2, writer.SizeInBytes());
}

TEST(Conditional, AlwaysMissingFieldDoesNotContributeToStaticSize) {
  EXPECT_EQ(0, OnlyAlwaysFalseConditionWriter::SizeInBytes());
  EXPECT_EQ(1, AlwaysFalseConditionWriter::SizeInBytes());
}

TEST(Conditional, AlwaysMissingFieldDoesNotContributeToSize) {
  uint8_t buffer[1] = {0};
  auto view = MakeAlwaysFalseConditionDynamicSizeView(buffer, sizeof buffer);
  ASSERT_TRUE(view.SizeIsKnown());
  EXPECT_EQ(1, view.SizeInBytes());
}

TEST(Conditional, StructIsOkWithAlwaysMissingField) {
  uint8_t buffer[1] = {0};
  auto writer = AlwaysFalseConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(1, writer.SizeInBytes());
  EXPECT_EQ(1, AlwaysFalseConditionView::SizeInBytes());
}

TEST(Conditional, StructIsOkWithOnlyAlwaysMissingField) {
  uint8_t buffer[1] = {0};
  auto writer = OnlyAlwaysFalseConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(0, writer.SizeInBytes());
  EXPECT_EQ(0, OnlyAlwaysFalseConditionView::SizeInBytes());
}

TEST(Conditional, ConditionDoesNotBlockStaticSize) {
  EXPECT_EQ(3, ConditionDoesNotContributeToSizeView::SizeInBytes());
}

TEST(Conditional, EqualsHaveAllFields) {
  std::array<uint8_t, 2> buf_a = {0, 1};
  std::array<uint8_t, 2> buf_b = {0, 1};
  EXPECT_EQ(buf_a, buf_b);

  auto a = BasicConditionalWriter(&buf_a);
  auto a_const = BasicConditionalWriter(
      static_cast</**/ ::std::array<uint8_t, 2> *>(&buf_a));
  auto b = BasicConditionalWriter(&buf_b);

  EXPECT_TRUE(a.has_xc().Known());
  EXPECT_TRUE(a.has_xc().Value());
  EXPECT_TRUE(b.has_xc().Known());
  EXPECT_TRUE(b.has_xc().Value());

  EXPECT_TRUE(a.Equals(a));
  EXPECT_TRUE(a.UncheckedEquals(a));
  EXPECT_TRUE(b.Equals(b));
  EXPECT_TRUE(b.UncheckedEquals(b));

  EXPECT_TRUE(a.Equals(b));
  EXPECT_TRUE(a.UncheckedEquals(b));
  EXPECT_TRUE(b.Equals(a));
  EXPECT_TRUE(b.UncheckedEquals(a));

  EXPECT_TRUE(a_const.Equals(b));
  EXPECT_TRUE(a_const.UncheckedEquals(b));
  EXPECT_TRUE(b.Equals(a_const));
  EXPECT_TRUE(b.UncheckedEquals(a_const));

  b.xc().Write(b.xc().Read() + 1);
  EXPECT_FALSE(a.Equals(b));
  EXPECT_FALSE(a.UncheckedEquals(b));
  EXPECT_FALSE(b.Equals(a));
  EXPECT_FALSE(b.UncheckedEquals(a));

  EXPECT_FALSE(a_const.Equals(b));
  EXPECT_FALSE(a_const.UncheckedEquals(b));
  EXPECT_FALSE(b.Equals(a_const));
  EXPECT_FALSE(b.UncheckedEquals(a_const));
}

TEST(Conditional, EqualsOneViewMissingField) {
  std::array<uint8_t, 2> buf_a = {0, 1};
  std::array<uint8_t, 2> buf_b = {1, 1};
  EXPECT_NE(buf_a, buf_b);

  auto a = BasicConditionalWriter(&buf_a);
  auto b = BasicConditionalWriter(&buf_b);

  EXPECT_TRUE(a.has_xc().Known());
  EXPECT_TRUE(a.has_xc().Value());
  EXPECT_TRUE(b.has_xc().Known());
  EXPECT_FALSE(b.has_xc().Value());

  EXPECT_FALSE(a.Equals(b));
  EXPECT_FALSE(a.UncheckedEquals(b));
  EXPECT_FALSE(b.Equals(a));
  EXPECT_FALSE(b.UncheckedEquals(a));
}

TEST(Conditional, EqualsBothFieldsMissing) {
  std::array<uint8_t, 2> buf_a = {1, 1};
  std::array<uint8_t, 2> buf_b = {1, 1};
  EXPECT_EQ(buf_a, buf_b);

  auto a = BasicConditionalWriter(&buf_a);
  auto a_const = BasicConditionalWriter(
      static_cast</**/ ::std::array<uint8_t, 2> *>(&buf_a));
  auto b = BasicConditionalWriter(&buf_b);

  EXPECT_TRUE(a.has_xc().Known());
  EXPECT_FALSE(a.has_xc().Value());
  EXPECT_TRUE(b.has_xc().Known());
  EXPECT_FALSE(b.has_xc().Value());

  EXPECT_TRUE(a.Equals(b));
  EXPECT_TRUE(a.UncheckedEquals(b));
  EXPECT_TRUE(b.Equals(a));
  EXPECT_TRUE(b.UncheckedEquals(a));

  EXPECT_TRUE(a_const.Equals(b));
  EXPECT_TRUE(a_const.UncheckedEquals(b));
  EXPECT_TRUE(b.Equals(a_const));
  EXPECT_TRUE(b.UncheckedEquals(a_const));

  ++buf_b[1];
  EXPECT_NE(buf_a, buf_b);
  EXPECT_TRUE(a.Equals(b));
  EXPECT_TRUE(a.UncheckedEquals(b));
  EXPECT_TRUE(b.Equals(a));
  EXPECT_TRUE(b.UncheckedEquals(a));

  EXPECT_TRUE(a_const.Equals(b));
  EXPECT_TRUE(a_const.UncheckedEquals(b));
  EXPECT_TRUE(b.Equals(a_const));
  EXPECT_TRUE(b.UncheckedEquals(a_const));
}

TEST(Conditional, TrueEnumBasedCondition) {
  uint8_t buffer[2] = {1};
  auto writer = EnumConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_EQ(0, writer.xc().Read());
}

TEST(Conditional, FalseEnumBasedCondition) {
  uint8_t buffer[2] = {0};
  auto writer = EnumConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(1, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(Conditional, TrueEnumBasedNegativeCondition) {
  uint8_t buffer[2] = {0};
  auto writer = NegativeEnumConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_EQ(0, writer.xc().Read());
}

TEST(Conditional, FalseEnumBasedNegativeCondition) {
  uint8_t buffer[2] = {1};
  auto writer = NegativeEnumConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(1, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(LessThanConditional, LessThan) {
  uint8_t buffer[2] = {4};
  auto writer = LessThanConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(LessThanConditional, Equal) {
  uint8_t buffer[2] = {5};
  auto writer = LessThanConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(1, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(LessThanConditional, GreaterThan) {
  uint8_t buffer[2] = {6};
  auto writer = LessThanConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(1, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(LessThanOrEqualConditional, LessThan) {
  uint8_t buffer[2] = {4};
  auto writer = LessThanOrEqualConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(LessThanOrEqualConditional, Equal) {
  uint8_t buffer[2] = {5};
  auto writer = LessThanOrEqualConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(LessThanOrEqualConditional, GreaterThan) {
  uint8_t buffer[2] = {6};
  auto writer = LessThanOrEqualConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(1, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(GreaterThanConditional, LessThan) {
  uint8_t buffer[2] = {4};
  auto writer = GreaterThanConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(1, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(GreaterThanConditional, Equal) {
  uint8_t buffer[2] = {5};
  auto writer = GreaterThanConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(1, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(GreaterThanConditional, GreaterThan) {
  uint8_t buffer[2] = {6};
  auto writer = GreaterThanConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(GreaterThanOrEqualConditional, LessThan) {
  uint8_t buffer[2] = {4};
  auto writer = GreaterThanOrEqualConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(1, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(GreaterThanOrEqualConditional, Equal) {
  uint8_t buffer[2] = {5};
  auto writer = GreaterThanOrEqualConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(GreaterThanOrEqualConditional, GreaterThan) {
  uint8_t buffer[2] = {6};
  auto writer = GreaterThanOrEqualConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(RangeConditional, ValueTooSmall) {
  uint8_t buffer[3] = {1, 9};
  auto writer = RangeConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(RangeConditional, ValueTooLarge) {
  uint8_t buffer[3] = {11, 12};
  auto writer = RangeConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(RangeConditional, ValuesSwapped) {
  uint8_t buffer[3] = {8, 7};
  auto writer = RangeConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(RangeConditional, True) {
  uint8_t buffer[3] = {7, 8};
  auto writer = RangeConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(3, writer.SizeInBytes());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(ReverseRangeConditional, ValueTooSmall) {
  uint8_t buffer[3] = {1, 9};
  auto writer = ReverseRangeConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(ReverseRangeConditional, ValueTooLarge) {
  uint8_t buffer[3] = {11, 12};
  auto writer = ReverseRangeConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(ReverseRangeConditional, ValuesSwapped) {
  uint8_t buffer[3] = {8, 7};
  auto writer = ReverseRangeConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(ReverseRangeConditional, True) {
  uint8_t buffer[3] = {7, 8};
  auto writer = ReverseRangeConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(3, writer.SizeInBytes());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(AndConditional, BothFalse) {
  uint8_t buffer[3] = {1, 1};
  auto writer = AndConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(AndConditional, FirstFalse) {
  uint8_t buffer[3] = {1, 5};
  auto writer = AndConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(AndConditional, SecondFalse) {
  uint8_t buffer[3] = {5, 1};
  auto writer = AndConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(AndConditional, BothTrue) {
  uint8_t buffer[3] = {5, 5};
  auto writer = AndConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(3, writer.SizeInBytes());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(OrConditional, BothFalse) {
  uint8_t buffer[3] = {1, 1};
  auto writer = OrConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(2, writer.SizeInBytes());
  EXPECT_FALSE(writer.xc().Ok());
}

TEST(OrConditional, FirstFalse) {
  uint8_t buffer[3] = {1, 5};
  auto writer = OrConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(3, writer.SizeInBytes());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(OrConditional, SecondFalse) {
  uint8_t buffer[3] = {5, 1};
  auto writer = OrConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(3, writer.SizeInBytes());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(OrConditional, BothTrue) {
  uint8_t buffer[3] = {5, 5};
  auto writer = OrConditionWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  ASSERT_TRUE(writer.SizeIsKnown());
  EXPECT_EQ(3, writer.SizeInBytes());
  EXPECT_TRUE(writer.xc().Ok());
}

TEST(ChoiceConditional, UseX) {
  ::std::array<uint8_t, 4> buffer = {1, 5, 0, 10};
  auto view = MakeChoiceConditionView(&buffer);
  EXPECT_TRUE(view.Ok());
  EXPECT_TRUE(view.SizeIsKnown());
  EXPECT_EQ(4, view.SizeInBytes());
  EXPECT_TRUE(view.has_xyc().ValueOr(false));
  EXPECT_EQ(10, view.xyc().Read());
}

TEST(ChoiceConditional, UseY) {
  ::std::array<uint8_t, 4> buffer = {2, 5, 0, 10};
  auto view = MakeChoiceConditionView(&buffer);
  EXPECT_TRUE(view.Ok());
  EXPECT_TRUE(view.SizeIsKnown());
  EXPECT_EQ(3, view.SizeInBytes());
  EXPECT_FALSE(view.has_xyc().ValueOr(true));
}

TEST(FlagConditional, True) {
  uint8_t buffer[2] = {0x80, 0xff};
  auto writer = ContainsContainsBitsWriter(buffer, sizeof buffer);
  EXPECT_TRUE(writer.Ok());
  EXPECT_TRUE(writer.SizeIsKnown());
  EXPECT_TRUE(writer.top().Ok());
}

TEST(WriteToString, MissingFieldsAreNotWritten) {
  uint8_t buffer[2] = {0x01, 0x00};
  auto reader = BasicConditionalWriter(buffer, 1U);
  EXPECT_EQ(
      "{\n"
      "  x: 1  # 0x1\n"
      "}",
      ::emboss::WriteToString(reader, ::emboss::MultilineText()));
  EXPECT_EQ("{ x: 1 }", ::emboss::WriteToString(reader));
}

TEST(WriteToString, PresentFieldsNotWritten) {
  uint8_t buffer[2] = {0x00, 0x01};
  auto reader = BasicConditionalWriter(buffer, 2U);
  EXPECT_EQ(
      "{\n"
      "  x: 0  # 0x0\n"
      "  xc: 1  # 0x1\n"
      "}",
      ::emboss::WriteToString(reader, ::emboss::MultilineText()));
  EXPECT_EQ("{ x: 0, xc: 1 }", ::emboss::WriteToString(reader));
}

TEST(WriteToString, AlwaysFalseCondition) {
  uint8_t buffer[2] = {0x00};
  auto reader = MakeAlwaysFalseConditionView(buffer, 1U);
  EXPECT_EQ(
      "{\n"
      "  x: 0  # 0x0\n"
      "}",
      ::emboss::WriteToString(reader, ::emboss::MultilineText()));
  EXPECT_EQ("{ x: 0 }", ::emboss::WriteToString(reader));
}

TEST(WriteToString, OnlyAlwaysFalseCondition) {
  uint8_t buffer[2] = {0x00};
  auto reader = MakeOnlyAlwaysFalseConditionView(buffer, 0U);
  EXPECT_EQ(
      "{\n"
      "}",
      ::emboss::WriteToString(reader, ::emboss::MultilineText()));
  EXPECT_EQ("{ }", ::emboss::WriteToString(reader));
}

TEST(WriteToString, EmptyStruct) {
  uint8_t buffer[2] = {0x00};
  auto reader = MakeEmptyStructView(buffer, 0U);
  EXPECT_EQ(
      "{\n"
      "}",
      ::emboss::WriteToString(reader, ::emboss::MultilineText()));
  EXPECT_EQ("{ }", ::emboss::WriteToString(reader));
}

TEST(ConditionalInline, ConditionalInline) {
  uint8_t buffer[4] = {0x00, 0x01, 0x02, 0x03};
  auto reader = ConditionalInlineWriter(buffer, 4U);
  EXPECT_EQ(1, reader.type_0().a().Read());
  EXPECT_TRUE(reader.has_type_1().Known());
  EXPECT_FALSE(reader.has_type_1().Value());
}

TEST(ConditionalAnonymous, ConditionalAnonymous) {
  ::std::array<uint8_t, 2> buffer = {0x00, 0x98};
  auto view = MakeConditionalAnonymousView(&buffer);
  EXPECT_TRUE(view.Ok());
  EXPECT_FALSE(view.has_low().Value());
  EXPECT_FALSE(view.has_mid().Value());
  EXPECT_FALSE(view.has_high().Value());
  view.x().Write(100);
  EXPECT_TRUE(view.has_low().Value());
  EXPECT_FALSE(view.has_mid().Value());
  EXPECT_TRUE(view.has_high().Value());
  EXPECT_EQ(0, view.low().Read());
  EXPECT_EQ(1, view.high().Read());
  view.low().Write(1);
  EXPECT_TRUE(view.has_low().Value());
  EXPECT_TRUE(view.has_mid().Value());
  EXPECT_TRUE(view.has_high().Value());
  EXPECT_EQ(1, view.low().Read());
  EXPECT_EQ(3, view.mid().Read());
  EXPECT_EQ(1, view.high().Read());
}

TEST(ConditionalOnFlag, ConditionalOnFlag) {
  ::std::array<uint8_t, 2> buffer = {0x00, 0x98};
  auto view = MakeConditionalOnFlagView(&buffer);
  EXPECT_TRUE(view.Ok());
  EXPECT_FALSE(view.enabled().Read());
  EXPECT_FALSE(view.has_value().Value());
  buffer[0] = 1;
  EXPECT_TRUE(view.enabled().Read());
  EXPECT_TRUE(view.has_value().Value());
  EXPECT_EQ(0x98, view.value().Read());
}

}  // namespace
}  // namespace test
}  // namespace emboss
