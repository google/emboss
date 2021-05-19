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

// Tests of generated code for text format.
#include <stdint.h>

#include <type_traits>
#include <utility>
#include <vector>

#include "gtest/gtest.h"
#include "testdata/text_format.emb.h"

namespace emboss {
namespace test {
namespace {

TEST(TextFormat, VanillaOutput) {
  ::std::array<char, 2> values = {1, 2};
  const auto view = MakeVanillaView(&values);
  EXPECT_EQ("{ a: 1, b: 2 }", ::emboss::WriteToString(view));
  EXPECT_EQ(
      "{\n"
      "  a: 1  # 0x1\n"
      "  b: 2  # 0x2\n"
      "}",
      ::emboss::WriteToString(view, ::emboss::MultilineText()));
}

TEST(TextFormat, SkippedFieldOutput) {
  ::std::array<char, 3> values = {1, 2, 3};
  const auto view = MakeStructWithSkippedFieldsView(&values);
  EXPECT_EQ("{ a: 1, c: 3 }", ::emboss::WriteToString(view));
  EXPECT_EQ(
      "{\n"
      "  a: 1  # 0x1\n"
      "  c: 3  # 0x3\n"
      "}",
      ::emboss::WriteToString(view, ::emboss::MultilineText()));
}

TEST(TextFormat, SkippedStructureFieldOutput) {
  ::std::array<char, 6> values = {1, 2, 3, 4, 5, 6};
  const auto view = MakeStructWithSkippedStructureFieldsView(&values);
  EXPECT_EQ("{ a: { a: 1, b: 2 }, c: { a: 5, b: 6 } }",
            ::emboss::WriteToString(view));
  EXPECT_EQ(
      "{\n"
      "  a: {\n"
      "    a: 1  # 0x1\n"
      "    b: 2  # 0x2\n"
      "  }\n"
      "  c: {\n"
      "    a: 5  # 0x5\n"
      "    b: 6  # 0x6\n"
      "  }\n"
      "}",
      ::emboss::WriteToString(view, ::emboss::MultilineText()));
  EXPECT_EQ("{ a: 3, b: 4 }", ::emboss::WriteToString(view.b()));
  EXPECT_EQ(
      "{\n"
      "  a: 3  # 0x3\n"
      "  b: 4  # 0x4\n"
      "}",
      ::emboss::WriteToString(view.b(), ::emboss::MultilineText()));
}

TEST(TextFormat, UpdateFromText) {
  ::std::array<char, 2> values{};
  const auto view = MakeVanillaView(&values);

  ::emboss::UpdateFromText(view, "{ a: 1, b: 2 }");
  EXPECT_EQ(view.a().Read(), 1);
  EXPECT_EQ(view.b().Read(), 2);

  ::emboss::UpdateFromText(view, "{ a: 3 }");
  EXPECT_EQ(view.a().Read(), 3);
  EXPECT_EQ(view.b().Read(), 2);

  ::emboss::UpdateFromText(view, "{ b: 4 }");
  EXPECT_EQ(view.a().Read(), 3);
  EXPECT_EQ(view.b().Read(), 4);
}

}  // namespace
}  // namespace test
}  // namespace emboss
