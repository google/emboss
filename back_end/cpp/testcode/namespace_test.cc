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

// Tests that generated code ends up in the correct C++ namespaces.
#include <stdint.h>

#include <vector>

#include "gtest/gtest.h"
#include "testdata/absolute_cpp_namespace.emb.h"
#include "testdata/cpp_namespace.emb.h"
#include "testdata/no_cpp_namespace.emb.h"

namespace emboss {
namespace test {
namespace {

TEST(Namespace, FooValueHasCorrectValueInDifferentNamespaces) {
  EXPECT_EQ(static_cast</**/ ::emboss_generated_code::Foo>(10),
            ::emboss_generated_code::Foo::VALUE);
  EXPECT_EQ(static_cast</**/ ::emboss::test::no_leading_double_colon::Foo>(11),
            ::emboss::test::no_leading_double_colon::Foo::VALUE);
  EXPECT_EQ(static_cast</**/ ::emboss::test::leading_double_colon::Foo>(12),
            ::emboss::test::leading_double_colon::Foo::VALUE);
}

}  // namespace
}  // namespace test
}  // namespace emboss
