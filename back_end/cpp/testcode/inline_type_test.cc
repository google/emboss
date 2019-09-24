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

// Tests for types defined inline.
#include <stdint.h>

#include <vector>

#include "gtest/gtest.h"
#include "testdata/inline_type.emb.h"

namespace emboss {
namespace test {
namespace {

static const ::std::uint8_t kFoo[2] = {0, 12};

static const ::std::uint8_t kFooOnFire[2] = {12, 0};

// Tests that inline-defined enums have correct, independent values.
TEST(FooView, EnumValuesAreAsExpected) {
  EXPECT_EQ(0, static_cast<int>(Foo::Status::OK));
  EXPECT_EQ(12, static_cast<int>(Foo::Status::FAILURE));
  EXPECT_EQ(12, static_cast<int>(Foo::SecondaryStatus::OK));
  EXPECT_EQ(0, static_cast<int>(Foo::SecondaryStatus::FAILURE));
}

// Tests that a structure containing inline-defined enums can be read correctly.
TEST(FooView, ReadsCorrectly) {
  auto ok_view = FooView(kFoo, sizeof kFoo);
  EXPECT_EQ(Foo::Status::OK, ok_view.status().Read());
  EXPECT_EQ(Foo::SecondaryStatus::OK, ok_view.secondary_status().Read());
  auto on_fire_view = FooView(kFooOnFire, sizeof kFooOnFire);
  EXPECT_EQ(Foo::Status::FAILURE, on_fire_view.status().Read());
  EXPECT_EQ(Foo::SecondaryStatus::FAILURE,
            on_fire_view.secondary_status().Read());
}

}  // namespace
}  // namespace test
}  // namespace emboss
