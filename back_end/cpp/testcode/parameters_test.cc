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
#include <gtest/gtest.h>
#include <stdint.h>

#include <type_traits>
#include <utility>
#include <vector>

#include "testdata/parameters.emb.h"

namespace emboss_test {
namespace {

TEST(Axes, Construction) {
  ::std::array<char, 12> values = {1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0};
  auto view = MakeAxesView(2, &values);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(2U, view.values().ElementCount());
  EXPECT_EQ(1U, view.values()[0].value().Read());
  EXPECT_EQ(1U, view.x().x().Read());
  EXPECT_EQ(2U, view.values()[1].value().Read());
  EXPECT_EQ(2U, view.y().y().Read());
  EXPECT_FALSE(view.has_z().Value());

  view = MakeAxesView(3, &values);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(3U, view.values().ElementCount());
  EXPECT_EQ(1U, view.values()[0].value().Read());
  EXPECT_EQ(2U, view.values()[1].value().Read());
  EXPECT_EQ(3U, view.values()[2].value().Read());
  EXPECT_EQ(3U, view.z().z().Read());

  view = MakeAxesView(4, &values);
  EXPECT_FALSE(view.Ok());
}

TEST(Axes, VirtualUsingParameter) {
  ::std::array<char, 12> values = {1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0};
  auto view = MakeAxesView(2, &values);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(3, view.axis_count_plus_one().Read());
}

TEST(AxesEnvelope, FieldPassedAsParameter) {
  ::std::array<char, 9> values = {2, 0, 0, 0, 0x80, 0, 100, 0, 0};
  auto view = MakeAxesEnvelopeView(&values);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(0x80000000U, view.axes().x().value().Read());
  EXPECT_EQ(9U, view.SizeInBytes());
}

TEST(AxesEnvelope, ParameterValueIsOutOfRange) {
  ::std::array<char, 9> values = {16, 0, 0, 0, 0x80, 0, 100, 0, 0};
  auto view = MakeAxesEnvelopeView(&values);
  EXPECT_FALSE(view.Ok());
  EXPECT_FALSE(view.axes().Ok());
}

TEST(Multiversion, ParameterPassedDown) {
  ::std::array<char, 13> values = {0, 1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0};
  auto view = MakeMultiversionView(Product::VERSION_1, &values);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(2U, view.axes().y().y().Read());
  EXPECT_FALSE(view.axes().has_z().Value());
  view = MakeMultiversionView(Product::VERSION_X, &values);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(2U, view.axes().y().y().Read());
  EXPECT_TRUE(view.axes().has_z().Value());
}

TEST(Multiversion, ParameterUsedToSwitchField) {
  ::std::array<char, 9> values = {1, 0, 0, 0, 0x80, 0, 100, 0, 0};
  auto view = MakeMultiversionView(Product::VERSION_1, &values);
  EXPECT_TRUE(view.Ok());
  EXPECT_TRUE(view.config().power().Read());
  EXPECT_FALSE(view.has_config_vx().Value());
  EXPECT_EQ(5U, view.SizeInBytes());
  view = MakeMultiversionView(Product::VERSION_X, &values);
  EXPECT_TRUE(view.Ok());
  EXPECT_TRUE(view.config().power().Read());
  EXPECT_TRUE(view.has_config_vx().Value());
  EXPECT_EQ(25600U, view.config_vx().gain().Read());
  EXPECT_EQ(9U, view.SizeInBytes());
}

TEST(StructContainingStructWithUnusedParameter, NoParameterIsNotOk) {
  ::std::array<char, 1> bytes = {1};
  auto view = MakeStructContainingStructWithUnusedParameterView(&bytes);
  EXPECT_FALSE(view.Ok());
  EXPECT_FALSE(view.swup().Ok());
  // In theory, view.swup().y().Ok() could be true, but as of time of writing,
  // missing/invalid parameters cause the parent structure to withhold backing
  // storage, making the entire child struct not Ok().
}

TEST(SizedArrayOfBiasedValues, ArrayElementsAreAccessible) {
  ::std::array<char, 3> bytes = {1, 10, 100};
  auto view = MakeSizedArrayOfBiasedValuesView(&bytes);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(110, view.values()[0].value().Read());
}

}  // namespace
}  // namespace emboss_test
