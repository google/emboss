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

#include <array>
#include <numeric>

#include "testing/base/public/gunit.h"
#include "third_party/emboss/runtime/cpp/emboss_text_util.h"
#include "third_party/emboss/testdata/text_format.emb.h"

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

TEST(TextFormat, JsonOutput) {
  ::std::array<char, 57> values = {};
  ::std::iota(values.begin(), values.end(), 0);

  const auto view = MakeJsonTestStructView(&values);
  EXPECT_EQ(
      "{\"one_byte_enum\": \"ZERO\", \"seven_bit_uint\": 1, \"one_bit_flag\": "
      "false, \"one_byte_uint\": 2, \"two_byte_uint\": 1027, "
      "\"four_byte_uint\": 134678021, \"eight_byte_uint\": "
      "1157159078456920585, \"uint8_array\": [17, 18, 19, 20, 21, 22, 23, 24, "
      "25, 26], \"uint16_array\": [7195, 7709, 8223, 8737, 9251, 9765, 10279, "
      "10793, 11307, 11821], \"struct_array\": [{\"element_one\": 47, "
      "\"element_two\": 48, \"element_three\": 49, \"element_four\": 50}, "
      "{\"element_one\": 51, \"element_two\": 52, \"element_three\": 53, "
      "\"element_four\": 54}]}",
      ::emboss::WriteToString(view, TextOutputOptions().Json(true)));
}

TEST(TextFormat, JsonOutputRobustness) {
  ::std::array<char, 57> values = {};
  ::std::iota(values.begin(), values.end(), 0);

  const auto view = MakeJsonTestStructView(&values);
  auto options = ::emboss::TextOutputOptions()
                     .Json(true)
                     .WithComments(true)
                     .WithDigitGrouping(true)
                     .WithNumericBase(16);
  EXPECT_EQ(
      "{\"one_byte_enum\": \"ZERO\", \"seven_bit_uint\": 1, \"one_bit_flag\": "
      "false, \"one_byte_uint\": 2, \"two_byte_uint\": 1027, "
      "\"four_byte_uint\": 134678021, \"eight_byte_uint\": "
      "1157159078456920585, \"uint8_array\": [17, 18, 19, 20, 21, 22, 23, 24, "
      "25, 26], \"uint16_array\": [7195, 7709, 8223, 8737, 9251, 9765, 10279, "
      "10793, 11307, 11821], \"struct_array\": [{\"element_one\": 47, "
      "\"element_two\": 48, \"element_three\": 49, \"element_four\": 50}, "
      "{\"element_one\": 51, \"element_two\": 52, \"element_three\": 53, "
      "\"element_four\": 54}]}",
      ::emboss::WriteToString(view, options));
}

TEST(TextFormat, DigitGroupingAndNumericBase) {
  ::std::array<char, 57> values = {};
  ::std::iota(values.begin(), values.end(), 0);

  const auto view = MakeJsonTestStructView(&values);
  auto options =
      ::emboss::TextOutputOptions().WithDigitGrouping(true).WithNumericBase(16);
  EXPECT_EQ(
      "{ one_byte_enum: ZERO, seven_bit_uint: 0x1, one_bit_flag: false, "
      "one_byte_uint: 0x2, two_byte_uint: 0x403, four_byte_uint: 0x807_0605, "
      "eight_byte_uint: 0x100f_0e0d_0c0b_0a09, uint8_array: { [0x0]: 0x11, "
      "0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, [0x8]: 0x19, 0x1a }, "
      "uint16_array: { [0x0]: 0x1c1b, 0x1e1d, 0x201f, 0x2221, 0x2423, 0x2625, "
      "0x2827, 0x2a29, [0x8]: 0x2c2b, 0x2e2d }, struct_array: { [0x0]: { "
      "element_one: 0x2f, element_two: 0x30, element_three: 0x31, "
      "element_four: 0x32 }, { element_one: 0x33, element_two: 0x34, "
      "element_three: 0x35, element_four: 0x36 } } }",
      ::emboss::WriteToString(view, options));
}

TEST(TextFormat, MultilineAndPartial) {
  ::std::array<char, 1> values = {10};
  // MakeVanillaView expects a pointer to an array of size 2, so we have to
  // construct the view manually.
  auto view = VanillaWriter(values.data(), values.size());
  auto options =
      ::emboss::TextOutputOptions().Multiline(true).WithAllowPartialOutput(
          true);
  EXPECT_EQ(
      "{\n"
      "a: 10\n"
      "}",
      ::emboss::WriteToString(view, options));
}

TEST(TextFormat, JsonSkippedFieldOutput) {
  ::std::array<char, 3> values = {1, 2, 3};
  const auto view = MakeStructWithSkippedFieldsView(&values);
  EXPECT_EQ("{\"a\": 1, \"c\": 3}",
            ::emboss::WriteToString(view, TextOutputOptions().Json(true)));
}

}  // namespace
}  // namespace test
}  // namespace emboss
