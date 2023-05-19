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

TEST(EnumDefault, NameToEnum) {
  EnumDefault result;

  EXPECT_TRUE(TryToGetEnumFromName("kFirst", &result));
  EXPECT_EQ(EnumDefault::kFirst, result);
  EXPECT_TRUE(TryToGetEnumFromName("kSecond", &result));
  EXPECT_EQ(EnumDefault::kSecond, result);
  EXPECT_TRUE(TryToGetEnumFromName("kTwoWord", &result));
  EXPECT_EQ(EnumDefault::kTwoWord, result);
  EXPECT_TRUE(TryToGetEnumFromName("kThreeWordEnum", &result));
  EXPECT_EQ(EnumDefault::kThreeWordEnum, result);
  EXPECT_TRUE(TryToGetEnumFromName("kLongEnumValueName", &result));
  EXPECT_EQ(EnumDefault::kLongEnumValueName, result);
}

TEST(EnumDefault, NameToEnumFailsWithShouty) {
  EnumDefault result = EnumDefault::kFirst;

  EXPECT_FALSE(TryToGetEnumFromName("SECOND", &result));
  EXPECT_EQ(EnumDefault::kFirst, result);
  EXPECT_FALSE(TryToGetEnumFromName("TWO_WORD", &result));
  EXPECT_EQ(EnumDefault::kFirst, result);
  EXPECT_FALSE(TryToGetEnumFromName("THREE_WORD_ENUM", &result));
  EXPECT_EQ(EnumDefault::kFirst, result);
  EXPECT_FALSE(TryToGetEnumFromName("LONG_ENUM_VALUE_NAME", &result));
  EXPECT_EQ(EnumDefault::kFirst, result);
}

TEST(EnumDefault, EnumToName) {
  EXPECT_EQ("kFirst", TryToGetNameFromEnum(EnumDefault::kFirst));
  EXPECT_EQ("kSecond", TryToGetNameFromEnum(EnumDefault::kSecond));
  EXPECT_EQ("kTwoWord", TryToGetNameFromEnum(EnumDefault::kTwoWord));
  EXPECT_EQ("kThreeWordEnum",
    TryToGetNameFromEnum(EnumDefault::kThreeWordEnum));
  EXPECT_EQ("kLongEnumValueName",
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

TEST(EnumShoutyAndKCamel, NameToEnum) {
  EnumShoutyAndKCamel result;

  EXPECT_TRUE(TryToGetEnumFromName("kFirst", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::kFirst, result);
  EXPECT_TRUE(TryToGetEnumFromName("kSecond", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::kSecond, result);
  EXPECT_TRUE(TryToGetEnumFromName("kTwoWord", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::kTwoWord, result);
  EXPECT_TRUE(TryToGetEnumFromName("kThreeWordEnum", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::kThreeWordEnum, result);
  EXPECT_TRUE(TryToGetEnumFromName("kLongEnumValueName", &result));
  EXPECT_EQ(EnumShoutyAndKCamel::kLongEnumValueName, result);

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

TEST(EnumMixed, NameToEnum) {
  EnumMixed result;

  EXPECT_TRUE(TryToGetEnumFromName("FIRST", &result));
  EXPECT_EQ(EnumMixed::FIRST, result);
  EXPECT_TRUE(TryToGetEnumFromName("kFirst", &result));
  EXPECT_EQ(EnumMixed::kFirst, result);
  EXPECT_TRUE(TryToGetEnumFromName("SECOND", &result));
  EXPECT_EQ(EnumMixed::SECOND, result);
  EXPECT_TRUE(TryToGetEnumFromName("kTwoWord", &result));
  EXPECT_EQ(EnumMixed::kTwoWord, result);
  EXPECT_TRUE(TryToGetEnumFromName("THREE_WORD_ENUM", &result));
  EXPECT_EQ(EnumMixed::THREE_WORD_ENUM, result);
  EXPECT_TRUE(TryToGetEnumFromName("kThreeWordEnum", &result));
  EXPECT_EQ(EnumMixed::kThreeWordEnum, result);
  EXPECT_TRUE(TryToGetEnumFromName("kLongEnumValueName", &result));
  EXPECT_EQ(EnumMixed::kLongEnumValueName, result);
 }

TEST(EnumMixed, NameToEnumFailsWithWrongCases) {
  EnumMixed result = EnumMixed::FIRST;
  EXPECT_FALSE(TryToGetEnumFromName("kSecond", &result));
  EXPECT_EQ(EnumMixed::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("TWO_WORD", &result));
  EXPECT_EQ(EnumMixed::FIRST, result);
  EXPECT_FALSE(TryToGetEnumFromName("LONG_ENUM_VALUE_NAME", &result));
  EXPECT_EQ(EnumMixed::FIRST, result);
}

TEST(EnumMixed, EnumToName) {
  EXPECT_EQ("FIRST", TryToGetNameFromEnum(EnumMixed::FIRST));
  EXPECT_EQ("FIRST", TryToGetNameFromEnum(EnumMixed::kFirst));
  EXPECT_EQ("SECOND", TryToGetNameFromEnum(EnumMixed::SECOND));
  EXPECT_EQ("kTwoWord", TryToGetNameFromEnum(EnumMixed::kTwoWord));
  EXPECT_EQ("kThreeWordEnum",
    TryToGetNameFromEnum(EnumMixed::THREE_WORD_ENUM));
  EXPECT_EQ("kThreeWordEnum",
    TryToGetNameFromEnum(EnumMixed::kThreeWordEnum));
  EXPECT_EQ("kLongEnumValueName",
    TryToGetNameFromEnum(EnumMixed::kLongEnumValueName));
}

}  // namespace
}  // namespace test
}  // namespace emboss
