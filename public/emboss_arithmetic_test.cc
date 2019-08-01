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

#include "public/emboss_arithmetic.h"

#include <gtest/gtest.h>

namespace emboss {
namespace support {

// EXPECT_EQ uses operator==.  For un-Known() Maybes, this follows the semantics
// for operator==(std::optional<T>, std::optional<T>), which returns true if
// neither argument has_value().  (It also matches Rust's Option and Haskell's
// Maybe.)
//
// Given the name "Known", it arguably should follow NaN != NaN semantics
// instead, but this is more useful for tests.
template <typename T>
constexpr inline bool operator==(const Maybe<T> &l, const Maybe<T> &r) {
  return l.Known() == r.Known() && l.ValueOrDefault() == r.ValueOrDefault();
}

namespace test {

using ::std::int32_t;
using ::std::int64_t;
using ::std::uint32_t;
using ::std::uint64_t;

TEST(Sum, Sum) {
  EXPECT_EQ(Maybe<int32_t>(0), (Sum<int32_t, int32_t, int32_t, int32_t>(
                                   Maybe<int32_t>(0), Maybe<int32_t>(0))));
  EXPECT_EQ(Maybe<int32_t>(2147483647),
            (Sum<int32_t, int32_t, int32_t, int32_t>(Maybe<int32_t>(2147483646),
                                                     Maybe<int32_t>(1))));
  EXPECT_EQ(Maybe<int32_t>(-2147483647 - 1),
            (Sum<int32_t, int32_t, int32_t, int32_t>(
                Maybe<int32_t>(-2147483647), Maybe<int32_t>(-1))));
  EXPECT_EQ(Maybe<uint32_t>(2147483648U),
            (Sum<uint32_t, uint32_t, int32_t, int32_t>(
                Maybe<int32_t>(2147483647), Maybe<int32_t>(1))));
  EXPECT_EQ(Maybe<int32_t>(2147483647),
            (Sum<int64_t, int32_t, uint32_t, int32_t>(
                Maybe<uint32_t>(2147483648U), Maybe<int32_t>(-1))));
  EXPECT_EQ(Maybe<int32_t>(), (Sum<int64_t, int32_t, uint32_t, int32_t>(
                                  Maybe<uint32_t>(), Maybe<int32_t>(-1))));
}

TEST(Difference, Difference) {
  EXPECT_EQ(Maybe<int32_t>(0), (Difference<int32_t, int32_t, int32_t, int32_t>(
                                   Maybe<int32_t>(0), Maybe<int32_t>(0))));
  EXPECT_EQ(Maybe<int32_t>(2147483647),
            (Difference<int32_t, int32_t, int32_t, int32_t>(
                Maybe<int32_t>(2147483646), Maybe<int32_t>(-1))));
  EXPECT_EQ(Maybe<int32_t>(-2147483647 - 1),
            (Difference<int32_t, int32_t, int32_t, int32_t>(
                Maybe<int32_t>(-2147483647), Maybe<int32_t>(1))));
  EXPECT_EQ(Maybe<uint32_t>(2147483648U),
            (Difference<uint32_t, uint32_t, int32_t, int32_t>(
                Maybe<int32_t>(2147483647), Maybe<int32_t>(-1))));
  EXPECT_EQ(Maybe<int32_t>(2147483647),
            (Difference<uint32_t, int32_t, uint32_t, int32_t>(
                Maybe<uint32_t>(2147483648U), Maybe<int32_t>(1))));
  EXPECT_EQ(Maybe<int32_t>(-2147483647 - 1),
            (Difference<int64_t, int32_t, int32_t, uint32_t>(
                Maybe<int32_t>(1), Maybe<uint32_t>(2147483649U))));
  EXPECT_EQ(Maybe<int32_t>(), (Difference<int64_t, int32_t, int32_t, uint32_t>(
                                  Maybe<int32_t>(1), Maybe<uint32_t>())));
}

TEST(Product, Product) {
  EXPECT_EQ(Maybe<int32_t>(0), (Product<int32_t, int32_t, int32_t, int32_t>(
                                   Maybe<int32_t>(0), Maybe<int32_t>(0))));
  EXPECT_EQ(Maybe<int32_t>(-2147483646),
            (Product<int32_t, int32_t, int32_t, int32_t>(
                Maybe<int32_t>(2147483646), Maybe<int32_t>(-1))));
  EXPECT_EQ(Maybe<int32_t>(-2147483647 - 1),
            (Product<int32_t, int32_t, int32_t, int32_t>(
                Maybe<int32_t>(-2147483647 - 1), Maybe<int32_t>(1))));
  EXPECT_EQ(Maybe<uint32_t>(2147483648U),
            (Product<uint32_t, uint32_t, int32_t, int32_t>(
                Maybe<int32_t>(1073741824), Maybe<int32_t>(2))));
  EXPECT_EQ(Maybe<uint32_t>(), (Product<uint32_t, uint32_t, int32_t, int32_t>(
                                   Maybe<int32_t>(), Maybe<int32_t>(2))));
}

TEST(Equal, Equal) {
  EXPECT_EQ(Maybe<bool>(true), (Equal<int32_t, bool, int32_t, int32_t>(
                                   Maybe<int32_t>(0), Maybe<int32_t>(0))));
  EXPECT_EQ(Maybe<bool>(false),
            (Equal<int32_t, bool, int32_t, int32_t>(Maybe<int32_t>(2147483646),
                                                    Maybe<int32_t>(-1))));
  EXPECT_EQ(Maybe<bool>(true),
            (Equal<int32_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(2147483647), Maybe<uint32_t>(2147483647))));
  EXPECT_EQ(Maybe<bool>(false),
            (Equal<int64_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(-2147483648LL), Maybe<uint32_t>(2147483648U))));
  EXPECT_EQ(Maybe<bool>(),
            (Equal<int64_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(), Maybe<uint32_t>(2147483648U))));
}

TEST(NotEqual, NotEqual) {
  EXPECT_EQ(Maybe<bool>(false), (NotEqual<int32_t, bool, int32_t, int32_t>(
                                    Maybe<int32_t>(0), Maybe<int32_t>(0))));
  EXPECT_EQ(Maybe<bool>(true),
            (NotEqual<int32_t, bool, int32_t, int32_t>(
                Maybe<int32_t>(2147483646), Maybe<int32_t>(-1))));
  EXPECT_EQ(Maybe<bool>(false),
            (NotEqual<int32_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(2147483647), Maybe<uint32_t>(2147483647))));
  EXPECT_EQ(Maybe<bool>(true),
            (NotEqual<int64_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(-2147483648LL), Maybe<uint32_t>(2147483648U))));
  EXPECT_EQ(Maybe<bool>(),
            (NotEqual<int64_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(-2147483648LL), Maybe<uint32_t>())));
}

TEST(LessThan, LessThan) {
  EXPECT_EQ(Maybe<bool>(false), (LessThan<int32_t, bool, int32_t, int32_t>(
                                    Maybe<int32_t>(0), Maybe<int32_t>(0))));
  EXPECT_EQ(Maybe<bool>(false),
            (LessThan<int32_t, bool, int32_t, int32_t>(
                Maybe<int32_t>(2147483646), Maybe<int32_t>(-1))));
  EXPECT_EQ(Maybe<bool>(false),
            (LessThan<int32_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(2147483647), Maybe<uint32_t>(2147483647))));
  EXPECT_EQ(Maybe<bool>(true),
            (LessThan<int64_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(-2147483648LL), Maybe<uint32_t>(2147483648U))));
  EXPECT_EQ(Maybe<bool>(),
            (LessThan<int64_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(), Maybe<uint32_t>(2147483648U))));
}

TEST(LessThanOrEqual, LessThanOrEqual) {
  EXPECT_EQ(Maybe<bool>(true),
            (LessThanOrEqual<int32_t, bool, int32_t, int32_t>(
                Maybe<int32_t>(0), Maybe<int32_t>(0))));
  EXPECT_EQ(Maybe<bool>(false),
            (LessThanOrEqual<int32_t, bool, int32_t, int32_t>(
                Maybe<int32_t>(2147483646), Maybe<int32_t>(-1))));
  EXPECT_EQ(Maybe<bool>(true),
            (LessThanOrEqual<int32_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(2147483647), Maybe<uint32_t>(2147483647))));
  EXPECT_EQ(Maybe<bool>(true),
            (LessThanOrEqual<int64_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(-2147483648LL), Maybe<uint32_t>(2147483648U))));
  EXPECT_EQ(Maybe<bool>(),
            (LessThanOrEqual<int64_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(), Maybe<uint32_t>(2147483648U))));
}

TEST(GreaterThan, GreaterThan) {
  EXPECT_EQ(Maybe<bool>(false), (GreaterThan<int32_t, bool, int32_t, int32_t>(
                                    Maybe<int32_t>(0), Maybe<int32_t>(0))));
  EXPECT_EQ(Maybe<bool>(true),
            (GreaterThan<int32_t, bool, int32_t, int32_t>(
                Maybe<int32_t>(2147483646), Maybe<int32_t>(-1))));
  EXPECT_EQ(Maybe<bool>(false),
            (GreaterThan<int32_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(2147483647), Maybe<uint32_t>(2147483647))));
  EXPECT_EQ(Maybe<bool>(false),
            (GreaterThan<int64_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(-2147483648LL), Maybe<uint32_t>(2147483648U))));
  EXPECT_EQ(Maybe<bool>(),
            (GreaterThan<int64_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(), Maybe<uint32_t>(2147483648U))));
}

TEST(GreaterThanOrEqual, GreaterThanOrEqual) {
  EXPECT_EQ(Maybe<bool>(true),
            (GreaterThanOrEqual<int32_t, bool, int32_t, int32_t>(
                Maybe<int32_t>(0), Maybe<int32_t>(0))));
  EXPECT_EQ(Maybe<bool>(true),
            (GreaterThanOrEqual<int32_t, bool, int32_t, int32_t>(
                Maybe<int32_t>(2147483646), Maybe<int32_t>(-1))));
  EXPECT_EQ(Maybe<bool>(true),
            (GreaterThanOrEqual<int32_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(2147483647), Maybe<uint32_t>(2147483647))));
  EXPECT_EQ(Maybe<bool>(false),
            (GreaterThanOrEqual<int64_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(-2147483648LL), Maybe<uint32_t>(2147483648U))));
  EXPECT_EQ(Maybe<bool>(),
            (GreaterThanOrEqual<int64_t, bool, int32_t, uint32_t>(
                Maybe<int32_t>(), Maybe<uint32_t>(2147483648U))));
}

TEST(And, And) {
  EXPECT_EQ(Maybe<bool>(true), (And<bool, bool, bool, bool>(
                                   Maybe<bool>(true), Maybe<bool>(true))));
  EXPECT_EQ(Maybe<bool>(),
            (And<bool, bool, bool, bool>(Maybe<bool>(), Maybe<bool>(true))));
  EXPECT_EQ(Maybe<bool>(),
            (And<bool, bool, bool, bool>(Maybe<bool>(), Maybe<bool>())));
  EXPECT_EQ(Maybe<bool>(),
            (And<bool, bool, bool, bool>(Maybe<bool>(true), Maybe<bool>())));
  EXPECT_EQ(Maybe<bool>(false), (And<bool, bool, bool, bool>(
                                    Maybe<bool>(false), Maybe<bool>(true))));
  EXPECT_EQ(Maybe<bool>(false),
            (And<bool, bool, bool, bool>(Maybe<bool>(false), Maybe<bool>())));
  EXPECT_EQ(Maybe<bool>(false), (And<bool, bool, bool, bool>(
                                    Maybe<bool>(false), Maybe<bool>(false))));
  EXPECT_EQ(Maybe<bool>(false), (And<bool, bool, bool, bool>(
                                    Maybe<bool>(true), Maybe<bool>(false))));
  EXPECT_EQ(Maybe<bool>(false),
            (And<bool, bool, bool, bool>(Maybe<bool>(), Maybe<bool>(false))));
}

TEST(Or, Or) {
  EXPECT_EQ(Maybe<bool>(false), (Or<bool, bool, bool, bool>(
                                    Maybe<bool>(false), Maybe<bool>(false))));
  EXPECT_EQ(Maybe<bool>(),
            (Or<bool, bool, bool, bool>(Maybe<bool>(), Maybe<bool>(false))));
  EXPECT_EQ(Maybe<bool>(),
            (Or<bool, bool, bool, bool>(Maybe<bool>(), Maybe<bool>())));
  EXPECT_EQ(Maybe<bool>(),
            (Or<bool, bool, bool, bool>(Maybe<bool>(false), Maybe<bool>())));
  EXPECT_EQ(Maybe<bool>(true), (Or<bool, bool, bool, bool>(Maybe<bool>(false),
                                                           Maybe<bool>(true))));
  EXPECT_EQ(Maybe<bool>(true),
            (Or<bool, bool, bool, bool>(Maybe<bool>(true), Maybe<bool>())));
  EXPECT_EQ(Maybe<bool>(true),
            (Or<bool, bool, bool, bool>(Maybe<bool>(true), Maybe<bool>(true))));
  EXPECT_EQ(Maybe<bool>(true), (Or<bool, bool, bool, bool>(
                                   Maybe<bool>(true), Maybe<bool>(false))));
  EXPECT_EQ(Maybe<bool>(true),
            (Or<bool, bool, bool, bool>(Maybe<bool>(), Maybe<bool>(true))));
}

TEST(Choice, Choice) {
  EXPECT_EQ(Maybe<int>(), (Choice<int, int, bool, int, int>(
                              Maybe<bool>(), Maybe<int>(1), Maybe<int>(2))));
  EXPECT_EQ(Maybe<int>(1),
            (Choice<int, int, bool, int, int>(Maybe<bool>(true), Maybe<int>(1),
                                              Maybe<int>(2))));
  EXPECT_EQ(Maybe<int>(2),
            (Choice<int, int, bool, int, int>(Maybe<bool>(false), Maybe<int>(1),
                                              Maybe<int>(2))));
  EXPECT_EQ(Maybe<int>(), (Choice<int, int, bool, int, int>(
                              Maybe<bool>(true), Maybe<int>(), Maybe<int>(2))));
  EXPECT_EQ(Maybe<int>(),
            (Choice<int, int, bool, int, int>(Maybe<bool>(false), Maybe<int>(1),
                                              Maybe<int>())));
  EXPECT_EQ(Maybe<int64_t>(2),
            (Choice<int64_t, int64_t, bool, int32_t, int32_t>(
                Maybe<bool>(false), Maybe<int32_t>(1), Maybe<int32_t>(2))));
  EXPECT_EQ(Maybe<int64_t>(2),
            (Choice<int64_t, int64_t, bool, int32_t, uint32_t>(
                Maybe<bool>(false), Maybe<int32_t>(-1), Maybe<uint32_t>(2))));
  EXPECT_EQ(Maybe<int64_t>(-1),
            (Choice<int64_t, int64_t, bool, int32_t, uint32_t>(
                Maybe<bool>(true), Maybe<int32_t>(-1), Maybe<uint32_t>(2))));
  EXPECT_EQ(Maybe<bool>(true),
            (Choice<bool, bool, bool, bool, bool>(
                Maybe<bool>(false), Maybe<bool>(false), Maybe<bool>(true))));
}

TEST(Maximum, Maximum) {
  EXPECT_EQ(Maybe<int>(100), (Maximum<int, int, int>(Maybe<int>(100))));
  EXPECT_EQ(Maybe<int>(99),
            (Maximum<int, int, int, int>(Maybe<int>(99), Maybe<int>(50))));
  EXPECT_EQ(Maybe<int>(98),
            (Maximum<int, int, int, int>(Maybe<int>(50), Maybe<int>(98))));
  EXPECT_EQ(Maybe<int>(97),
            (Maximum<int, int, int, int, int>(Maybe<int>(50), Maybe<int>(70),
                                              Maybe<int>(97))));
  EXPECT_EQ(Maybe<int>(), (Maximum<int, int, int, int, int>(
                              Maybe<int>(50), Maybe<int>(), Maybe<int>(97))));
  EXPECT_EQ(Maybe<int>(-100),
            (Maximum<int, int, int, int, int>(
                Maybe<int>(-120), Maybe<int>(-150), Maybe<int>(-100))));
  EXPECT_EQ(Maybe<int>(), (Maximum<int, int, int>(Maybe<int>())));
}

}  // namespace test
}  // namespace support
}  // namespace emboss
