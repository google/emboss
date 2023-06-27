// Copyright 2023 Google LLC
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

// Tests the `enum_case` attribute generating the correct case. Note that since
// these tests are regarding the name of enum members, it is likely that if this
// test would fail, it may fail to compile.

#include "gtest/gtest.h"
#include "testdata/enum_case.emb.h"

namespace emboss {
namespace test {
namespace {

TEST(EnumShouty, AccessValuesByNameInSource) {
  EXPECT_EQ(static_cast<int>(EnumShouty::FIRST), 0);
  EXPECT_EQ(static_cast<int>(EnumShouty::SECOND), 1);
  EXPECT_EQ(static_cast<int>(EnumShouty::TWO_WORD), 2);
  EXPECT_EQ(static_cast<int>(EnumShouty::THREE_WORD_ENUM), 4);
  EXPECT_EQ(static_cast<int>(EnumShouty::LONG_ENUM_VALUE_NAME), 8);
}

TEST(EnumShouty, EnumIsKnown) {
  EXPECT_TRUE(EnumIsKnown(EnumShouty::FIRST));
  EXPECT_TRUE(EnumIsKnown(EnumShouty::SECOND));
  EXPECT_TRUE(EnumIsKnown(EnumShouty::TWO_WORD));
  EXPECT_TRUE(EnumIsKnown(EnumShouty::THREE_WORD_ENUM));
  EXPECT_TRUE(EnumIsKnown(EnumShouty::LONG_ENUM_VALUE_NAME));
  EXPECT_FALSE(EnumIsKnown(static_cast<EnumShouty>(999)));
}

TEST(EnumShouty, NameToEnum) {
  EnumShouty result;

  EXPECT_TRUE(TryToGetEnumFromName("FIRST", &result));
  EXPECT_EQ(EnumShouty::FIRST, result);
  EXPECT_TRUE(TryToGetEnumFromName("SECOND", &result));
  EXPECT_EQ(EnumShouty::SECOND, result);
  EXPECT_TRUE(TryToGetEnumFromName("TWO_WORD", &result));
  EXPECT_EQ(EnumShouty::TWO_WORD, result);
  EXPECT_TRUE(TryToGetEnumFromName("THREE_WORD_ENUM", &result));
  EXPECT_EQ(EnumShouty::THREE_WORD_ENUM, result);
  EXPECT_TRUE(TryToGetEnumFromName("LONG_ENUM_VALUE_NAME", &result));
  EXPECT_EQ(EnumShouty::LONG_ENUM_VALUE_NAME, result);
}

TEST(EnumShouty, NameToEnumFailsWithKCamel) {
  EnumShouty result = EnumShouty::FIRST;

  EXPECT_FALSE(TryToGetEnumFromName("kSecond", &result));
  EXPECT_EQ(EnumShouty::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("kTwoWord", &result));
  EXPECT_EQ(EnumShouty::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("kThreeWordEnum", &result));
  EXPECT_EQ(EnumShouty::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("kLongEnumValueName", &result));
  EXPECT_EQ(EnumShouty::FIRST, result);
}

TEST(EnumShouty, EnumToName) {
  EXPECT_EQ("FIRST", TryToGetNameFromEnum(EnumShouty::FIRST));
  EXPECT_EQ("SECOND", TryToGetNameFromEnum(EnumShouty::SECOND));
  EXPECT_EQ("TWO_WORD", TryToGetNameFromEnum(EnumShouty::TWO_WORD));
  EXPECT_EQ("THREE_WORD_ENUM",
    TryToGetNameFromEnum(EnumShouty::THREE_WORD_ENUM));
  EXPECT_EQ("LONG_ENUM_VALUE_NAME",
    TryToGetNameFromEnum(EnumShouty::LONG_ENUM_VALUE_NAME));
}

TEST(EnumDefault, AccessValuesByNameInSource) {
  EXPECT_EQ(static_cast<int>(EnumDefault::kFirst), 0);
  EXPECT_EQ(static_cast<int>(EnumDefault::kSecond), 1);
  EXPECT_EQ(static_cast<int>(EnumDefault::kTwoWord), 2);
  EXPECT_EQ(static_cast<int>(EnumDefault::kThreeWordEnum), 4);
  EXPECT_EQ(static_cast<int>(EnumDefault::kLongEnumValueName), 8);
}

TEST(EnumDefault, EnumIsKnown) {
  EXPECT_TRUE(EnumIsKnown(EnumDefault::kFirst));
  EXPECT_TRUE(EnumIsKnown(EnumDefault::kSecond));
  EXPECT_TRUE(EnumIsKnown(EnumDefault::kTwoWord));
  EXPECT_TRUE(EnumIsKnown(EnumDefault::kThreeWordEnum));
  EXPECT_TRUE(EnumIsKnown(EnumDefault::kLongEnumValueName));
  EXPECT_FALSE(EnumIsKnown(static_cast<EnumDefault>(999)));
}

TEST(EnumDefault, NameToEnum) {
  EnumDefault result;

  EXPECT_TRUE(TryToGetEnumFromName("FIRST", &result));
  EXPECT_EQ(EnumDefault::kFirst, result);
  EXPECT_TRUE(TryToGetEnumFromName("SECOND", &result));
  EXPECT_EQ(EnumDefault::kSecond, result);
  EXPECT_TRUE(TryToGetEnumFromName("TWO_WORD", &result));
  EXPECT_EQ(EnumDefault::kTwoWord, result);
  EXPECT_TRUE(TryToGetEnumFromName("THREE_WORD_ENUM", &result));
  EXPECT_EQ(EnumDefault::kThreeWordEnum, result);
  EXPECT_TRUE(TryToGetEnumFromName("LONG_ENUM_VALUE_NAME", &result));
  EXPECT_EQ(EnumDefault::kLongEnumValueName, result);
}

TEST(EnumDefault, NameToEnumFailsWithKCamel) {
  EnumDefault result = EnumDefault::kFirst;

  EXPECT_FALSE(TryToGetEnumFromName("kFirst", &result));
  EXPECT_EQ(EnumDefault::kFirst, result);
  EXPECT_FALSE(TryToGetEnumFromName("kSecond", &result));
  EXPECT_EQ(EnumDefault::kFirst, result);
  EXPECT_FALSE(TryToGetEnumFromName("kTwoWord", &result));
  EXPECT_EQ(EnumDefault::kFirst, result);
  EXPECT_FALSE(TryToGetEnumFromName("kThreeWordEnum", &result));
  EXPECT_EQ(EnumDefault::kFirst, result);
  EXPECT_FALSE(TryToGetEnumFromName("kLongEnumValueName", &result));
  EXPECT_EQ(EnumDefault::kFirst, result);
}

TEST(EnumDefault, EnumToName) {
  EXPECT_EQ("FIRST", TryToGetNameFromEnum(EnumDefault::kFirst));
  EXPECT_EQ("SECOND", TryToGetNameFromEnum(EnumDefault::kSecond));
  EXPECT_EQ("TWO_WORD", TryToGetNameFromEnum(EnumDefault::kTwoWord));
  EXPECT_EQ("THREE_WORD_ENUM",
    TryToGetNameFromEnum(EnumDefault::kThreeWordEnum));
  EXPECT_EQ("LONG_ENUM_VALUE_NAME",
    TryToGetNameFromEnum(EnumDefault::kLongEnumValueName));
}

TEST(EnumShoutyAndKCamel, AccessValuesByNameInSource) {
  EXPECT_EQ(static_cast<int>(EnumShoutyAndKCamel::FIRST), 0);
  EXPECT_EQ(static_cast<int>(EnumShoutyAndKCamel::kFirst), 0);
  EXPECT_EQ(static_cast<int>(EnumShoutyAndKCamel::SECOND), 1);
  EXPECT_EQ(static_cast<int>(EnumShoutyAndKCamel::kSecond), 1);
  EXPECT_EQ(static_cast<int>(EnumShoutyAndKCamel::TWO_WORD), 2);
  EXPECT_EQ(static_cast<int>(EnumShoutyAndKCamel::kTwoWord), 2);
  EXPECT_EQ(static_cast<int>(EnumShoutyAndKCamel::THREE_WORD_ENUM), 4);
  EXPECT_EQ(static_cast<int>(EnumShoutyAndKCamel::kThreeWordEnum), 4);
  EXPECT_EQ(static_cast<int>(EnumShoutyAndKCamel::LONG_ENUM_VALUE_NAME), 8);
  EXPECT_EQ(static_cast<int>(EnumShoutyAndKCamel::kLongEnumValueName), 8);
}

TEST(EnumShoutyAndKCamel, EnumIsKnown) {
  EXPECT_TRUE(EnumIsKnown(EnumShoutyAndKCamel::FIRST));
  EXPECT_TRUE(EnumIsKnown(EnumShoutyAndKCamel::SECOND));
  EXPECT_TRUE(EnumIsKnown(EnumShoutyAndKCamel::TWO_WORD));
  EXPECT_TRUE(EnumIsKnown(EnumShoutyAndKCamel::THREE_WORD_ENUM));
  EXPECT_TRUE(EnumIsKnown(EnumShoutyAndKCamel::LONG_ENUM_VALUE_NAME));
  EXPECT_TRUE(EnumIsKnown(EnumShoutyAndKCamel::kFirst));
  EXPECT_TRUE(EnumIsKnown(EnumShoutyAndKCamel::kSecond));
  EXPECT_TRUE(EnumIsKnown(EnumShoutyAndKCamel::kTwoWord));
  EXPECT_TRUE(EnumIsKnown(EnumShoutyAndKCamel::kThreeWordEnum));
  EXPECT_TRUE(EnumIsKnown(EnumShoutyAndKCamel::kLongEnumValueName));
  EXPECT_FALSE(EnumIsKnown(static_cast<EnumShoutyAndKCamel>(999)));
}

TEST(EnumShoutyAndKCamel, NameToEnum) {
  EnumShoutyAndKCamel result;

  EXPECT_TRUE(TryToGetEnumFromName("FIRST", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::FIRST, result);
  EXPECT_TRUE(TryToGetEnumFromName("SECOND", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::SECOND, result);
  EXPECT_TRUE(TryToGetEnumFromName("TWO_WORD", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::TWO_WORD, result);
  EXPECT_TRUE(TryToGetEnumFromName("THREE_WORD_ENUM", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::THREE_WORD_ENUM, result);
  EXPECT_TRUE(TryToGetEnumFromName("LONG_ENUM_VALUE_NAME", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::LONG_ENUM_VALUE_NAME, result);
}

TEST(EnumShoutyAndKCamel, NameToEnumFailsWithKCamel) {
  EnumShoutyAndKCamel result = EnumShoutyAndKCamel::FIRST;

  EXPECT_FALSE(TryToGetEnumFromName("kFirst", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("kSecond", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("kTwoWord", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("kThreeWordEnum", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("kLongEnumValueName", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::FIRST, result);
}

TEST(EnumShoutyAndKCamel, EnumToName) {
  EXPECT_EQ("FIRST", TryToGetNameFromEnum(EnumShoutyAndKCamel::FIRST));
  EXPECT_EQ("SECOND", TryToGetNameFromEnum(EnumShoutyAndKCamel::SECOND));
  EXPECT_EQ("TWO_WORD", TryToGetNameFromEnum(EnumShoutyAndKCamel::TWO_WORD));
  EXPECT_EQ("THREE_WORD_ENUM",
    TryToGetNameFromEnum(EnumShoutyAndKCamel::THREE_WORD_ENUM));
  EXPECT_EQ("LONG_ENUM_VALUE_NAME",
    TryToGetNameFromEnum(EnumShoutyAndKCamel::LONG_ENUM_VALUE_NAME));

  EXPECT_EQ("FIRST", TryToGetNameFromEnum(EnumShoutyAndKCamel::kFirst));
  EXPECT_EQ("SECOND", TryToGetNameFromEnum(EnumShoutyAndKCamel::kSecond));
  EXPECT_EQ("TWO_WORD", TryToGetNameFromEnum(EnumShoutyAndKCamel::kTwoWord));
  EXPECT_EQ("THREE_WORD_ENUM",
    TryToGetNameFromEnum(EnumShoutyAndKCamel::kThreeWordEnum));
  EXPECT_EQ("LONG_ENUM_VALUE_NAME",
    TryToGetNameFromEnum(EnumShoutyAndKCamel::kLongEnumValueName));
}

TEST(EnumMixed, AccessValuesByNameInSource) {
  EXPECT_EQ(static_cast<int>(EnumMixed::FIRST), 0);
  EXPECT_EQ(static_cast<int>(EnumMixed::kFirst), 0);
  EXPECT_EQ(static_cast<int>(EnumMixed::SECOND), 1);
  EXPECT_EQ(static_cast<int>(EnumMixed::kTwoWord), 2);
  EXPECT_EQ(static_cast<int>(EnumMixed::THREE_WORD_ENUM), 4);
  EXPECT_EQ(static_cast<int>(EnumMixed::kThreeWordEnum), 4);
  EXPECT_EQ(static_cast<int>(EnumMixed::kLongEnumValueName), 8);
}

TEST(EnumMixed, EnumIsKnown) {
  EXPECT_TRUE(EnumIsKnown(EnumMixed::FIRST));
  EXPECT_TRUE(EnumIsKnown(EnumMixed::SECOND));
  EXPECT_TRUE(EnumIsKnown(EnumMixed::THREE_WORD_ENUM));
  EXPECT_TRUE(EnumIsKnown(EnumMixed::kFirst));
  EXPECT_TRUE(EnumIsKnown(EnumMixed::kTwoWord));
  EXPECT_TRUE(EnumIsKnown(EnumMixed::kThreeWordEnum));
  EXPECT_TRUE(EnumIsKnown(EnumMixed::kLongEnumValueName));
  EXPECT_FALSE(EnumIsKnown(static_cast<EnumMixed>(999)));
}

TEST(EnumMixed, NameToEnum) {
  EnumMixed result;

  EXPECT_TRUE(TryToGetEnumFromName("FIRST", &result));
  EXPECT_EQ(EnumMixed::FIRST, result);
  EXPECT_TRUE(TryToGetEnumFromName("SECOND", &result));
  EXPECT_EQ(EnumMixed::SECOND, result);
  EXPECT_TRUE(TryToGetEnumFromName("TWO_WORD", &result));
  EXPECT_EQ(EnumMixed::kTwoWord, result);
  EXPECT_TRUE(TryToGetEnumFromName("THREE_WORD_ENUM", &result));
  EXPECT_EQ(EnumMixed::THREE_WORD_ENUM, result);
  EXPECT_TRUE(TryToGetEnumFromName("LONG_ENUM_VALUE_NAME", &result));
  EXPECT_EQ(EnumMixed::kLongEnumValueName, result);
}

TEST(EnumMixed, NameToEnumFailsWithKCamel) {
  EnumShoutyAndKCamel result = EnumShoutyAndKCamel::FIRST;

  EXPECT_FALSE(TryToGetEnumFromName("kFirst", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("kSecond", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("kTwoWord", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("kThreeWordEnum", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("kLongEnumValueName", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::FIRST, result);
}

TEST(EnumMixed, EnumToName) {
  EXPECT_EQ("FIRST", TryToGetNameFromEnum(EnumMixed::FIRST));
  EXPECT_EQ("FIRST", TryToGetNameFromEnum(EnumMixed::kFirst));
  EXPECT_EQ("SECOND", TryToGetNameFromEnum(EnumMixed::SECOND));
  EXPECT_EQ("TWO_WORD", TryToGetNameFromEnum(EnumMixed::kTwoWord));
  EXPECT_EQ("THREE_WORD_ENUM",
    TryToGetNameFromEnum(EnumMixed::THREE_WORD_ENUM));
  EXPECT_EQ("THREE_WORD_ENUM",
    TryToGetNameFromEnum(EnumMixed::kThreeWordEnum));
  EXPECT_EQ("LONG_ENUM_VALUE_NAME",
    TryToGetNameFromEnum(EnumMixed::kLongEnumValueName));
}

TEST(UseKCamelEnumCase, IsValidToUse) {
  std::array<uint8_t, UseKCamelEnumCase::IntrinsicSizeInBytes()> buffer;
  auto view = MakeUseKCamelEnumCaseView(&buffer);

  EXPECT_EQ(UseKCamelEnumCase::first(), EnumDefault::kFirst);
  EXPECT_EQ(view.first().Read(), EnumDefault::kFirst);

  EXPECT_TRUE(view.v().TryToWrite(EnumDefault::kSecond));
  EXPECT_FALSE(view.v_is_first().Read());

  EXPECT_TRUE(view.v().TryToWrite(EnumDefault::kFirst));
  EXPECT_TRUE(view.v_is_first().Read());
}

TEST(UseKCamelEnumCase, TextStream) {
  std::array<uint8_t, UseKCamelEnumCase::IntrinsicSizeInBytes()> buffer;
  auto view = MakeUseKCamelEnumCaseView(&buffer);

  EXPECT_TRUE(view.v().TryToWrite(EnumDefault::kSecond));
  EXPECT_EQ(WriteToString(view), "{ v: SECOND }");
  EXPECT_TRUE(UpdateFromText(view, "{ v: TWO_WORD }"));
  EXPECT_EQ(view.v().Read(), EnumDefault::kTwoWord);
}

}  // namespace
}  // namespace test
}  // namespace emboss
