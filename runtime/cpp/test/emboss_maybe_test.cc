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

#include "runtime/cpp/emboss_maybe.h"

#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace emboss {
namespace support {
namespace test {

enum class Foo : ::std::int64_t {
  BAR = 1,
  BAZ = 2,
};

TEST(Maybe, Known) {
  EXPECT_TRUE(Maybe<int>(10).Known());
  EXPECT_EQ(10, Maybe<int>(10).ValueOr(3));
  EXPECT_EQ(10, Maybe<int>(10).ValueOrDefault());
  EXPECT_EQ(10, Maybe<int>(10).Value());
  EXPECT_TRUE(Maybe<bool>(true).Value());
  EXPECT_EQ(Foo::BAZ, Maybe<Foo>(Foo::BAZ).ValueOrDefault());

  Maybe<int> x = Maybe<int>(1000);
  Maybe<int> y = Maybe<int>();
  y = x;
  EXPECT_TRUE(y.Known());
  EXPECT_EQ(1000, y.Value());
}

TEST(Maybe, Unknown) {
  EXPECT_FALSE(Maybe<int>().Known());
  EXPECT_EQ(3, Maybe<int>().ValueOr(3));
  EXPECT_EQ(0, Maybe<int>().ValueOrDefault());
  EXPECT_FALSE(Maybe<bool>().ValueOrDefault());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(Maybe<int>().Value(), "Known()");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_FALSE(Maybe<bool>().ValueOrDefault());
  EXPECT_EQ(static_cast<Foo>(0), Maybe<Foo>().ValueOrDefault());

  Maybe<int> x = Maybe<int>();
  Maybe<int> y = Maybe<int>(1000);
  y = x;
  EXPECT_FALSE(y.Known());
}

}  // namespace test
}  // namespace support
}  // namespace emboss
