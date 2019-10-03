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

#include "runtime/cpp/emboss_arithmetic.h"

#include "gtest/gtest.h"

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
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(0),
      (Sum</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t, ::std::int32_t>(
          Maybe</**/ ::std::int32_t>(0), Maybe</**/ ::std::int32_t>(0))));
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(2147483647),
      (Sum</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t, ::std::int32_t>(
          Maybe</**/ ::std::int32_t>(2147483646),
          Maybe</**/ ::std::int32_t>(1))));
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(-2147483647 - 1),
      (Sum</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t, ::std::int32_t>(
          Maybe</**/ ::std::int32_t>(-2147483647),
          Maybe</**/ ::std::int32_t>(-1))));
  EXPECT_EQ(Maybe</**/ ::std::uint32_t>(2147483648U),
            (Sum</**/ ::std::uint32_t, ::std::uint32_t, ::std::int32_t,
                 ::std::int32_t>(Maybe</**/ ::std::int32_t>(2147483647),
                                 Maybe</**/ ::std::int32_t>(1))));
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(2147483647),
            (Sum</**/ ::std::int64_t, ::std::int32_t, ::std::uint32_t,
                 ::std::int32_t>(Maybe</**/ ::std::uint32_t>(2147483648U),
                                 Maybe</**/ ::std::int32_t>(-1))));
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(),
            (Sum</**/ ::std::int64_t, ::std::int32_t, ::std::uint32_t,
                 ::std::int32_t>(Maybe</**/ ::std::uint32_t>(),
                                 Maybe</**/ ::std::int32_t>(-1))));
}

TEST(Difference, Difference) {
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(0),
            (Difference</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                        ::std::int32_t>(Maybe</**/ ::std::int32_t>(0),
                                        Maybe</**/ ::std::int32_t>(0))));
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(2147483647),
            (Difference</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                        ::std::int32_t>(Maybe</**/ ::std::int32_t>(2147483646),
                                        Maybe</**/ ::std::int32_t>(-1))));
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(-2147483647 - 1),
            (Difference</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                        ::std::int32_t>(Maybe</**/ ::std::int32_t>(-2147483647),
                                        Maybe</**/ ::std::int32_t>(1))));
  EXPECT_EQ(Maybe</**/ ::std::uint32_t>(2147483648U),
            (Difference</**/ ::std::uint32_t, ::std::uint32_t, ::std::int32_t,
                        ::std::int32_t>(Maybe</**/ ::std::int32_t>(2147483647),
                                        Maybe</**/ ::std::int32_t>(-1))));
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(2147483647),
      (Difference</**/ ::std::uint32_t, ::std::int32_t, ::std::uint32_t,
                  ::std::int32_t>(Maybe</**/ ::std::uint32_t>(2147483648U),
                                  Maybe</**/ ::std::int32_t>(1))));
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(-2147483647 - 1),
      (Difference</**/ ::std::int64_t, ::std::int32_t, ::std::int32_t,
                  ::std::uint32_t>(Maybe</**/ ::std::int32_t>(1),
                                   Maybe</**/ ::std::uint32_t>(2147483649U))));
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(),
            (Difference</**/ ::std::int64_t, ::std::int32_t, ::std::int32_t,
                        ::std::uint32_t>(Maybe</**/ ::std::int32_t>(1),
                                         Maybe</**/ ::std::uint32_t>())));
}

TEST(Product, Product) {
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(0),
            (Product</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                     ::std::int32_t>(Maybe</**/ ::std::int32_t>(0),
                                     Maybe</**/ ::std::int32_t>(0))));
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(-2147483646),
            (Product</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                     ::std::int32_t>(Maybe</**/ ::std::int32_t>(2147483646),
                                     Maybe</**/ ::std::int32_t>(-1))));
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(-2147483647 - 1),
      (Product</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
               ::std::int32_t>(Maybe</**/ ::std::int32_t>(-2147483647 - 1),
                               Maybe</**/ ::std::int32_t>(1))));
  EXPECT_EQ(Maybe</**/ ::std::uint32_t>(2147483648U),
            (Product</**/ ::std::uint32_t, ::std::uint32_t, ::std::int32_t,
                     ::std::int32_t>(Maybe</**/ ::std::int32_t>(1073741824),
                                     Maybe</**/ ::std::int32_t>(2))));
  EXPECT_EQ(Maybe</**/ ::std::uint32_t>(),
            (Product</**/ ::std::uint32_t, ::std::uint32_t, ::std::int32_t,
                     ::std::int32_t>(Maybe</**/ ::std::int32_t>(),
                                     Maybe</**/ ::std::int32_t>(2))));
}

TEST(Equal, Equal) {
  EXPECT_EQ(Maybe<bool>(true),
            (Equal</**/ ::std::int32_t, bool, ::std::int32_t, ::std::int32_t>(
                Maybe</**/ ::std::int32_t>(0), Maybe</**/ ::std::int32_t>(0))));
  EXPECT_EQ(Maybe<bool>(false),
            (Equal</**/ ::std::int32_t, bool, ::std::int32_t, ::std::int32_t>(
                Maybe</**/ ::std::int32_t>(2147483646),
                Maybe</**/ ::std::int32_t>(-1))));
  EXPECT_EQ(Maybe<bool>(true),
            (Equal</**/ ::std::int32_t, bool, ::std::int32_t, ::std::uint32_t>(
                Maybe</**/ ::std::int32_t>(2147483647),
                Maybe</**/ ::std::uint32_t>(2147483647))));
  EXPECT_EQ(Maybe<bool>(false),
            (Equal</**/ ::std::int64_t, bool, ::std::int32_t, ::std::uint32_t>(
                Maybe</**/ ::std::int32_t>(-2147483648LL),
                Maybe</**/ ::std::uint32_t>(2147483648U))));
  EXPECT_EQ(Maybe<bool>(),
            (Equal</**/ ::std::int64_t, bool, ::std::int32_t, ::std::uint32_t>(
                Maybe</**/ ::std::int32_t>(),
                Maybe</**/ ::std::uint32_t>(2147483648U))));
}

TEST(NotEqual, NotEqual) {
  EXPECT_EQ(
      Maybe<bool>(false),
      (NotEqual</**/ ::std::int32_t, bool, ::std::int32_t, ::std::int32_t>(
          Maybe</**/ ::std::int32_t>(0), Maybe</**/ ::std::int32_t>(0))));
  EXPECT_EQ(
      Maybe<bool>(true),
      (NotEqual</**/ ::std::int32_t, bool, ::std::int32_t, ::std::int32_t>(
          Maybe</**/ ::std::int32_t>(2147483646),
          Maybe</**/ ::std::int32_t>(-1))));
  EXPECT_EQ(
      Maybe<bool>(false),
      (NotEqual</**/ ::std::int32_t, bool, ::std::int32_t, ::std::uint32_t>(
          Maybe</**/ ::std::int32_t>(2147483647),
          Maybe</**/ ::std::uint32_t>(2147483647))));
  EXPECT_EQ(
      Maybe<bool>(true),
      (NotEqual</**/ ::std::int64_t, bool, ::std::int32_t, ::std::uint32_t>(
          Maybe</**/ ::std::int32_t>(-2147483648LL),
          Maybe</**/ ::std::uint32_t>(2147483648U))));
  EXPECT_EQ(
      Maybe<bool>(),
      (NotEqual</**/ ::std::int64_t, bool, ::std::int32_t, ::std::uint32_t>(
          Maybe</**/ ::std::int32_t>(-2147483648LL),
          Maybe</**/ ::std::uint32_t>())));
}

TEST(LessThan, LessThan) {
  EXPECT_EQ(
      Maybe<bool>(false),
      (LessThan</**/ ::std::int32_t, bool, ::std::int32_t, ::std::int32_t>(
          Maybe</**/ ::std::int32_t>(0), Maybe</**/ ::std::int32_t>(0))));
  EXPECT_EQ(
      Maybe<bool>(false),
      (LessThan</**/ ::std::int32_t, bool, ::std::int32_t, ::std::int32_t>(
          Maybe</**/ ::std::int32_t>(2147483646),
          Maybe</**/ ::std::int32_t>(-1))));
  EXPECT_EQ(
      Maybe<bool>(false),
      (LessThan</**/ ::std::int32_t, bool, ::std::int32_t, ::std::uint32_t>(
          Maybe</**/ ::std::int32_t>(2147483647),
          Maybe</**/ ::std::uint32_t>(2147483647))));
  EXPECT_EQ(
      Maybe<bool>(true),
      (LessThan</**/ ::std::int64_t, bool, ::std::int32_t, ::std::uint32_t>(
          Maybe</**/ ::std::int32_t>(-2147483648LL),
          Maybe</**/ ::std::uint32_t>(2147483648U))));
  EXPECT_EQ(
      Maybe<bool>(),
      (LessThan</**/ ::std::int64_t, bool, ::std::int32_t, ::std::uint32_t>(
          Maybe</**/ ::std::int32_t>(),
          Maybe</**/ ::std::uint32_t>(2147483648U))));
}

TEST(LessThanOrEqual, LessThanOrEqual) {
  EXPECT_EQ(Maybe<bool>(true),
            (LessThanOrEqual</**/ ::std::int32_t, bool, ::std::int32_t,
                             ::std::int32_t>(Maybe</**/ ::std::int32_t>(0),
                                             Maybe</**/ ::std::int32_t>(0))));
  EXPECT_EQ(
      Maybe<bool>(false),
      (LessThanOrEqual</**/ ::std::int32_t, bool, ::std::int32_t,
                       ::std::int32_t>(Maybe</**/ ::std::int32_t>(2147483646),
                                       Maybe</**/ ::std::int32_t>(-1))));
  EXPECT_EQ(Maybe<bool>(true),
            (LessThanOrEqual</**/ ::std::int32_t, bool, ::std::int32_t,
                             ::std::uint32_t>(
                Maybe</**/ ::std::int32_t>(2147483647),
                Maybe</**/ ::std::uint32_t>(2147483647))));
  EXPECT_EQ(Maybe<bool>(true),
            (LessThanOrEqual</**/ ::std::int64_t, bool, ::std::int32_t,
                             ::std::uint32_t>(
                Maybe</**/ ::std::int32_t>(-2147483648LL),
                Maybe</**/ ::std::uint32_t>(2147483648U))));
  EXPECT_EQ(Maybe<bool>(), (LessThanOrEqual</**/ ::std::int64_t, bool,
                                            ::std::int32_t, ::std::uint32_t>(
                               Maybe</**/ ::std::int32_t>(),
                               Maybe</**/ ::std::uint32_t>(2147483648U))));
}

TEST(GreaterThan, GreaterThan) {
  EXPECT_EQ(
      Maybe<bool>(false),
      (GreaterThan</**/ ::std::int32_t, bool, ::std::int32_t, ::std::int32_t>(
          Maybe</**/ ::std::int32_t>(0), Maybe</**/ ::std::int32_t>(0))));
  EXPECT_EQ(
      Maybe<bool>(true),
      (GreaterThan</**/ ::std::int32_t, bool, ::std::int32_t, ::std::int32_t>(
          Maybe</**/ ::std::int32_t>(2147483646),
          Maybe</**/ ::std::int32_t>(-1))));
  EXPECT_EQ(
      Maybe<bool>(false),
      (GreaterThan</**/ ::std::int32_t, bool, ::std::int32_t, ::std::uint32_t>(
          Maybe</**/ ::std::int32_t>(2147483647),
          Maybe</**/ ::std::uint32_t>(2147483647))));
  EXPECT_EQ(
      Maybe<bool>(false),
      (GreaterThan</**/ ::std::int64_t, bool, ::std::int32_t, ::std::uint32_t>(
          Maybe</**/ ::std::int32_t>(-2147483648LL),
          Maybe</**/ ::std::uint32_t>(2147483648U))));
  EXPECT_EQ(
      Maybe<bool>(),
      (GreaterThan</**/ ::std::int64_t, bool, ::std::int32_t, ::std::uint32_t>(
          Maybe</**/ ::std::int32_t>(),
          Maybe</**/ ::std::uint32_t>(2147483648U))));
}

TEST(GreaterThanOrEqual, GreaterThanOrEqual) {
  EXPECT_EQ(Maybe<bool>(true),
            (GreaterThanOrEqual</**/ ::std::int32_t, bool, ::std::int32_t,
                                ::std::int32_t>(
                Maybe</**/ ::std::int32_t>(0), Maybe</**/ ::std::int32_t>(0))));
  EXPECT_EQ(Maybe<bool>(true),
            (GreaterThanOrEqual</**/ ::std::int32_t, bool, ::std::int32_t,
                                ::std::int32_t>(
                Maybe</**/ ::std::int32_t>(2147483646),
                Maybe</**/ ::std::int32_t>(-1))));
  EXPECT_EQ(Maybe<bool>(true),
            (GreaterThanOrEqual</**/ ::std::int32_t, bool, ::std::int32_t,
                                ::std::uint32_t>(
                Maybe</**/ ::std::int32_t>(2147483647),
                Maybe</**/ ::std::uint32_t>(2147483647))));
  EXPECT_EQ(Maybe<bool>(false),
            (GreaterThanOrEqual</**/ ::std::int64_t, bool, ::std::int32_t,
                                ::std::uint32_t>(
                Maybe</**/ ::std::int32_t>(-2147483648LL),
                Maybe</**/ ::std::uint32_t>(2147483648U))));
  EXPECT_EQ(Maybe<bool>(), (GreaterThanOrEqual</**/ ::std::int64_t, bool,
                                               ::std::int32_t, ::std::uint32_t>(
                               Maybe</**/ ::std::int32_t>(),
                               Maybe</**/ ::std::uint32_t>(2147483648U))));
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
  EXPECT_EQ(
      Maybe</**/ ::std::int64_t>(2),
      (Choice</**/ ::std::int64_t, ::std::int64_t, bool, ::std::int32_t,
              ::std::int32_t>(Maybe<bool>(false), Maybe</**/ ::std::int32_t>(1),
                              Maybe</**/ ::std::int32_t>(2))));
  EXPECT_EQ(Maybe</**/ ::std::int64_t>(2),
            (Choice</**/ ::std::int64_t, ::std::int64_t, bool, ::std::int32_t,
                    ::std::uint32_t>(Maybe<bool>(false),
                                     Maybe</**/ ::std::int32_t>(-1),
                                     Maybe</**/ ::std::uint32_t>(2))));
  EXPECT_EQ(Maybe</**/ ::std::int64_t>(-1),
            (Choice</**/ ::std::int64_t, ::std::int64_t, bool, ::std::int32_t,
                    ::std::uint32_t>(Maybe<bool>(true),
                                     Maybe</**/ ::std::int32_t>(-1),
                                     Maybe</**/ ::std::uint32_t>(2))));
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
