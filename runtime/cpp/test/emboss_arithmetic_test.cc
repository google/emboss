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

TEST(FlooringQuotient, FlooringQuotient) {
  // Sign table from the division_and_modulus design doc.
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(2),
            (FlooringQuotient</**/ ::std::int32_t, ::std::int32_t,
                              ::std::int32_t, ::std::int32_t>(
                Maybe</**/ ::std::int32_t>(8), Maybe</**/ ::std::int32_t>(3))));
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(-3),
            (FlooringQuotient</**/ ::std::int32_t, ::std::int32_t,
                              ::std::int32_t, ::std::int32_t>(
                Maybe</**/ ::std::int32_t>(8), Maybe</**/ ::std::int32_t>(-3))));
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(-3),
            (FlooringQuotient</**/ ::std::int32_t, ::std::int32_t,
                              ::std::int32_t, ::std::int32_t>(
                Maybe</**/ ::std::int32_t>(-8), Maybe</**/ ::std::int32_t>(3))));
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(2),
      (FlooringQuotient</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                        ::std::int32_t>(Maybe</**/ ::std::int32_t>(-8),
                                        Maybe</**/ ::std::int32_t>(-3))));
  // Exact division needs no flooring adjustment.
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(-2),
      (FlooringQuotient</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                        ::std::int32_t>(Maybe</**/ ::std::int32_t>(-6),
                                        Maybe</**/ ::std::int32_t>(3))));
  // Unsigned: identical to C++'s built-in division.
  EXPECT_EQ(Maybe</**/ ::std::uint32_t>(2),
            (FlooringQuotient</**/ ::std::uint32_t, ::std::uint32_t,
                              ::std::uint32_t, ::std::uint32_t>(
                Maybe</**/ ::std::uint32_t>(8),
                Maybe</**/ ::std::uint32_t>(3))));
  // Unknown propagates.
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(),
      (FlooringQuotient</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                        ::std::int32_t>(Maybe</**/ ::std::int32_t>(),
                                        Maybe</**/ ::std::int32_t>(3))));
  // A zero divisor yields Unknown even when both operands are Known -- this is
  // the "undefined" result of `// 0`, avoiding C++ undefined behavior.
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(),
      (FlooringQuotient</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                        ::std::int32_t>(Maybe</**/ ::std::int32_t>(8),
                                        Maybe</**/ ::std::int32_t>(0))));
  EXPECT_EQ(Maybe</**/ ::std::uint32_t>(),
            (FlooringQuotient</**/ ::std::uint32_t, ::std::uint32_t,
                              ::std::uint32_t, ::std::uint32_t>(
                Maybe</**/ ::std::uint32_t>(8),
                Maybe</**/ ::std::uint32_t>(0))));
}

TEST(FlooringRemainder, FlooringRemainder) {
  // Sign table from the design doc; the result takes the sign of the divisor.
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(2),
            (FlooringRemainder</**/ ::std::int32_t, ::std::int32_t,
                               ::std::int32_t, ::std::int32_t>(
                Maybe</**/ ::std::int32_t>(8), Maybe</**/ ::std::int32_t>(3))));
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(-1),
            (FlooringRemainder</**/ ::std::int32_t, ::std::int32_t,
                               ::std::int32_t, ::std::int32_t>(
                Maybe</**/ ::std::int32_t>(8), Maybe</**/ ::std::int32_t>(-3))));
  EXPECT_EQ(Maybe</**/ ::std::int32_t>(1),
            (FlooringRemainder</**/ ::std::int32_t, ::std::int32_t,
                               ::std::int32_t, ::std::int32_t>(
                Maybe</**/ ::std::int32_t>(-8), Maybe</**/ ::std::int32_t>(3))));
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(-2),
      (FlooringRemainder</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                         ::std::int32_t>(Maybe</**/ ::std::int32_t>(-8),
                                         Maybe</**/ ::std::int32_t>(-3))));
  // Exact division: remainder is zero regardless of sign.
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(0),
      (FlooringRemainder</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                         ::std::int32_t>(Maybe</**/ ::std::int32_t>(-6),
                                         Maybe</**/ ::std::int32_t>(3))));
  // Unsigned.
  EXPECT_EQ(Maybe</**/ ::std::uint32_t>(2),
            (FlooringRemainder</**/ ::std::uint32_t, ::std::uint32_t,
                               ::std::uint32_t, ::std::uint32_t>(
                Maybe</**/ ::std::uint32_t>(8),
                Maybe</**/ ::std::uint32_t>(3))));
  // Unknown propagates.
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(),
      (FlooringRemainder</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                         ::std::int32_t>(Maybe</**/ ::std::int32_t>(8),
                                         Maybe</**/ ::std::int32_t>())));
  // A zero divisor yields Unknown even when both operands are Known.
  EXPECT_EQ(
      Maybe</**/ ::std::int32_t>(),
      (FlooringRemainder</**/ ::std::int32_t, ::std::int32_t, ::std::int32_t,
                         ::std::int32_t>(Maybe</**/ ::std::int32_t>(8),
                                         Maybe</**/ ::std::int32_t>(0))));
  EXPECT_EQ(Maybe</**/ ::std::uint32_t>(),
            (FlooringRemainder</**/ ::std::uint32_t, ::std::uint32_t,
                               ::std::uint32_t, ::std::uint32_t>(
                Maybe</**/ ::std::uint32_t>(8),
                Maybe</**/ ::std::uint32_t>(0))));
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

// The tests below exercise the "why not" reason (Unknowability) that a
// non-Known Maybe carries, and -- crucially -- how it MERGES across operators.
// The precedence is operation-dependent (see emboss_arithmetic.h): arithmetic
// lets kUndefined dominate, while short-circuiting And/Or let kUnreadable
// dominate.
//
// The test-local operator==(Maybe, Maybe) above ignores the reason, so these
// tests assert on Reason()/IsUndefined() directly.

// Reason shorthands.  A Known() value, an unreadable Unknown, and an undefined
// Unknown, for both int and bool.
constexpr Maybe<int> kKnownInt = Maybe<int>(5);
constexpr Maybe<int> kUnreadableInt = Maybe<int>();
constexpr Maybe<int> kUndefinedInt = Maybe<int>(Unknowability::kUndefined);
constexpr Maybe<bool> kTrue = Maybe<bool>(true);
constexpr Maybe<bool> kFalse = Maybe<bool>(false);
constexpr Maybe<bool> kUnreadableBool = Maybe<bool>();
constexpr Maybe<bool> kUndefinedBool = Maybe<bool>(Unknowability::kUndefined);

// Operator function templates cannot be aliased, so these helper wrappers give
// the merge-matrix tests below a concise, fixed-type spelling of each operator.
inline Maybe<int> SumII(Maybe<int> l, Maybe<int> r) {
  return Sum<int, int, int, int>(l, r);
}
inline Maybe<int> MaxI5(Maybe<int> a, Maybe<int> b, Maybe<int> c, Maybe<int> d,
                        Maybe<int> e) {
  return Maximum<int, int, int, int, int, int>(a, b, c, d, e);
}
inline Maybe<bool> AndBB(Maybe<bool> l, Maybe<bool> r) {
  return And<bool, bool, bool, bool>(l, r);
}
inline Maybe<bool> OrBB(Maybe<bool> l, Maybe<bool> r) {
  return Or<bool, bool, bool, bool>(l, r);
}
inline Maybe<int> ChoiceI(Maybe<bool> c, Maybe<int> t, Maybe<int> f) {
  return Choice<int, int, bool, int, int>(c, t, f);
}
inline Maybe<int> QuotII(Maybe<int> l, Maybe<int> r) {
  return FlooringQuotient<int, int, int, int>(l, r);
}
inline Maybe<int> RemII(Maybe<int> l, Maybe<int> r) {
  return FlooringRemainder<int, int, int, int>(l, r);
}

TEST(Unknowability, ArithmeticUndefinedDominates) {
  // Any undefined operand makes an (un-Known) arithmetic result undefined;
  // otherwise an un-Known result is merely unreadable.  A fully-Known result
  // has no un-Known reason at all.
  EXPECT_EQ(Unknowability::kKnown, SumII(kKnownInt, kKnownInt).Reason());
  EXPECT_EQ(Unknowability::kUnreadable,
            SumII(kKnownInt, kUnreadableInt).Reason());
  EXPECT_EQ(Unknowability::kUndefined,
            SumII(kKnownInt, kUndefinedInt).Reason());
  EXPECT_EQ(Unknowability::kUndefined,
            SumII(kUndefinedInt, kUnreadableInt).Reason());
  EXPECT_EQ(Unknowability::kUnreadable,
            SumII(kUnreadableInt, kUnreadableInt).Reason());
  EXPECT_TRUE(SumII(kKnownInt, kUndefinedInt).IsUndefined());
  EXPECT_FALSE(SumII(kKnownInt, kUnreadableInt).IsUndefined());

  // Product and the comparisons route through the same MaybeDo path.
  EXPECT_EQ(Unknowability::kUndefined,
            (Product<int, int, int, int>(kUndefinedInt, kKnownInt)).Reason());
  EXPECT_EQ(
      Unknowability::kUndefined,
      (Equal<bool, bool, int, int>(kUndefinedInt, kKnownInt)).Reason());
  EXPECT_EQ(
      Unknowability::kUnreadable,
      (LessThan<bool, bool, int, int>(kUnreadableInt, kKnownInt)).Reason());
}

TEST(Unknowability, MaximumUndefinedDominatesAcrossManyArgs) {
  // Maximum folds through MaybeDo variadically: a single undefined arg among
  // many poisons the whole max as undefined.
  EXPECT_EQ(
      Unknowability::kUndefined,
      MaxI5(kKnownInt, kKnownInt, kUndefinedInt, kKnownInt, kUnreadableInt)
          .Reason());
  EXPECT_EQ(
      Unknowability::kUnreadable,
      MaxI5(kKnownInt, kUnreadableInt, kKnownInt, kKnownInt, kKnownInt)
          .Reason());
  EXPECT_EQ(
      Unknowability::kKnown,
      MaxI5(kKnownInt, kKnownInt, kKnownInt, kKnownInt, kKnownInt).Reason());
}

TEST(Unknowability, AndUnreadableDominates) {
  // In a short-circuiting And, an unreadable operand could still become a Known
  // false with more bytes -- resolving the whole And -- so kUnreadable
  // dominates kUndefined.  A Known false still short-circuits to Known false.
  //
  // unreadable + undefined -> unreadable (unreadable side might yet settle).
  EXPECT_EQ(Unknowability::kUnreadable,
            AndBB(kUndefinedBool, kUnreadableBool).Reason());
  EXPECT_EQ(Unknowability::kUnreadable,
            AndBB(kUnreadableBool, kUndefinedBool).Reason());
  // Both undefined -> nothing can settle it -> undefined.
  EXPECT_EQ(Unknowability::kUndefined,
            AndBB(kUndefinedBool, kUndefinedBool).Reason());
  // A settled (Known true) side plus an undefined side -> undefined.
  EXPECT_EQ(Unknowability::kUndefined, AndBB(kTrue, kUndefinedBool).Reason());
  EXPECT_EQ(Unknowability::kUnreadable, AndBB(kTrue, kUnreadableBool).Reason());
  // A Known false short-circuits regardless of the other side's reason.
  EXPECT_EQ(Unknowability::kKnown, AndBB(kFalse, kUndefinedBool).Reason());
  EXPECT_TRUE(AndBB(kFalse, kUndefinedBool).Known());
  EXPECT_FALSE(AndBB(kFalse, kUndefinedBool).ValueOrDefault());
}

TEST(Unknowability, OrUnreadableDominates) {
  // Symmetric to And: an unreadable operand could still become a Known true,
  // resolving the Or, so kUnreadable dominates.  A Known true short-circuits.
  EXPECT_EQ(Unknowability::kUnreadable,
            OrBB(kUndefinedBool, kUnreadableBool).Reason());
  EXPECT_EQ(Unknowability::kUndefined,
            OrBB(kUndefinedBool, kUndefinedBool).Reason());
  // A settled (Known false) side plus an undefined side -> undefined.
  EXPECT_EQ(Unknowability::kUndefined, OrBB(kFalse, kUndefinedBool).Reason());
  EXPECT_EQ(Unknowability::kUnreadable, OrBB(kFalse, kUnreadableBool).Reason());
  // A Known true short-circuits regardless of the other side's reason.
  EXPECT_EQ(Unknowability::kKnown, OrBB(kTrue, kUndefinedBool).Reason());
  EXPECT_TRUE(OrBB(kTrue, kUndefinedBool).ValueOrDefault());
}

TEST(Unknowability, ChoicePropagatesConditionThenTakenBranch) {
  // Unknown condition -> propagate the condition's reason.
  EXPECT_EQ(Unknowability::kUndefined,
            ChoiceI(kUndefinedBool, kKnownInt, kKnownInt).Reason());
  EXPECT_EQ(Unknowability::kUnreadable,
            ChoiceI(kUnreadableBool, kKnownInt, kKnownInt).Reason());
  // Known condition -> propagate ONLY the taken branch's reason; the untaken
  // branch's undefined-ness is irrelevant.
  EXPECT_EQ(Unknowability::kUndefined,
            ChoiceI(kTrue, kUndefinedInt, kKnownInt).Reason());
  EXPECT_EQ(Unknowability::kKnown,
            ChoiceI(kTrue, kKnownInt, kUndefinedInt).Reason());
  EXPECT_EQ(Unknowability::kKnown,
            ChoiceI(kFalse, kUndefinedInt, kKnownInt).Reason());
  EXPECT_EQ(Unknowability::kUndefined,
            ChoiceI(kFalse, kKnownInt, kUndefinedInt).Reason());
  EXPECT_EQ(Unknowability::kUnreadable,
            ChoiceI(kTrue, kUnreadableInt, kKnownInt).Reason());
}

TEST(Unknowability, MaybeStaticCastPropagates) {
  EXPECT_EQ(
      Unknowability::kUndefined,
      (MaybeStaticCast</**/ ::std::int64_t, int>(kUndefinedInt)).Reason());
  EXPECT_EQ(
      Unknowability::kUnreadable,
      (MaybeStaticCast</**/ ::std::int64_t, int>(kUnreadableInt)).Reason());
  EXPECT_EQ(Unknowability::kKnown,
            (MaybeStaticCast</**/ ::std::int64_t, int>(kKnownInt)).Reason());
}

TEST(Unknowability, DivideOrModuloZeroDivisorIsUndefined) {
  // A Known zero divisor is undefined -- even if the dividend is unreadable,
  // the r==0 case dominates.
  EXPECT_EQ(Unknowability::kUndefined,
            QuotII(Maybe<int>(8), Maybe<int>(0)).Reason());
  EXPECT_EQ(Unknowability::kUndefined,
            RemII(Maybe<int>(8), Maybe<int>(0)).Reason());
  EXPECT_EQ(Unknowability::kUndefined,
            QuotII(kUnreadableInt, Maybe<int>(0)).Reason());
  EXPECT_TRUE(QuotII(Maybe<int>(8), Maybe<int>(0)).IsUndefined());

  // An unreadable operand with a nonzero (or unreadable) divisor is unreadable.
  EXPECT_EQ(Unknowability::kUnreadable,
            QuotII(Maybe<int>(8), kUnreadableInt).Reason());
  EXPECT_EQ(Unknowability::kUnreadable,
            QuotII(kUnreadableInt, Maybe<int>(2)).Reason());

  // An already-undefined operand propagates as undefined.
  EXPECT_EQ(Unknowability::kUndefined,
            QuotII(kUndefinedInt, Maybe<int>(2)).Reason());
  EXPECT_EQ(Unknowability::kUndefined,
            QuotII(Maybe<int>(8), kUndefinedInt).Reason());
  EXPECT_EQ(Unknowability::kUndefined,
            QuotII(kUndefinedInt, kUnreadableInt).Reason());

  // A defined division has a Known result and no reason.
  EXPECT_EQ(Unknowability::kKnown,
            QuotII(Maybe<int>(8), Maybe<int>(2)).Reason());
}

}  // namespace test
}  // namespace support
}  // namespace emboss
