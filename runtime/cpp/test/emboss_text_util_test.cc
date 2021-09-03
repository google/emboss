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

#include "runtime/cpp/emboss_text_util.h"

#include <cmath>
#include <limits>

#include "gtest/gtest.h"

namespace emboss {
namespace support {
namespace test {

TEST(DecodeInteger, DecodeUInt8Decimal) {
  ::std::uint8_t result;
  EXPECT_TRUE(DecodeInteger("123", &result));
  EXPECT_EQ(123, result);
  EXPECT_TRUE(DecodeInteger("0", &result));
  EXPECT_EQ(0, result);
  EXPECT_TRUE(DecodeInteger("0123", &result));
  EXPECT_EQ(123, result);
  EXPECT_TRUE(DecodeInteger("0_123", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("_12", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("1234", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("12a", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("12A", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("12 ", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger(" 12", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("12.", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("12.0", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("256", &result));
  EXPECT_EQ(123, result);
  EXPECT_TRUE(DecodeInteger("128", &result));
  EXPECT_EQ(128, result);
  EXPECT_FALSE(DecodeInteger("-0", &result));
  EXPECT_EQ(128, result);
  EXPECT_TRUE(DecodeInteger("255", &result));
  EXPECT_EQ(255, result);
}

TEST(DecodeInteger, DecodeInt8Decimal) {
  ::std::int8_t result;
  EXPECT_TRUE(DecodeInteger("123", &result));
  EXPECT_EQ(123, result);
  EXPECT_TRUE(DecodeInteger("0", &result));
  EXPECT_EQ(0, result);
  EXPECT_TRUE(DecodeInteger("0123", &result));
  EXPECT_EQ(123, result);
  EXPECT_TRUE(DecodeInteger("0_123", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("_12", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("1234", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("12a", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("12A", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("12 ", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger(" 12", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("12.", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("12.0", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("256", &result));
  EXPECT_EQ(123, result);
  EXPECT_FALSE(DecodeInteger("128", &result));
  EXPECT_EQ(123, result);
  EXPECT_TRUE(DecodeInteger("-0", &result));
  EXPECT_EQ(0, result);
  EXPECT_TRUE(DecodeInteger("127", &result));
  EXPECT_EQ(127, result);
  EXPECT_TRUE(DecodeInteger("-127", &result));
  EXPECT_EQ(-127, result);
  EXPECT_TRUE(DecodeInteger("-128", &result));
  EXPECT_EQ(-128, result);
  EXPECT_FALSE(DecodeInteger("0-127", &result));
  EXPECT_EQ(-128, result);
  EXPECT_FALSE(DecodeInteger("- 127", &result));
  EXPECT_EQ(-128, result);
}

TEST(DecodeInteger, DecodeUInt8Hex) {
  ::std::uint8_t result;
  EXPECT_TRUE(DecodeInteger("0x23", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_TRUE(DecodeInteger("0x0", &result));
  EXPECT_EQ(0x0, result);
  EXPECT_TRUE(DecodeInteger("0xff", &result));
  EXPECT_EQ(0xff, result);
  EXPECT_TRUE(DecodeInteger("0xFE", &result));
  EXPECT_EQ(0xfe, result);
  EXPECT_TRUE(DecodeInteger("0xFd", &result));
  EXPECT_EQ(0xfd, result);
  EXPECT_TRUE(DecodeInteger("0XeC", &result));
  EXPECT_EQ(0xec, result);
  EXPECT_TRUE(DecodeInteger("0x012", &result));
  EXPECT_EQ(0x12, result);
  EXPECT_TRUE(DecodeInteger("0x0_0023", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_TRUE(DecodeInteger("0x_0023", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0x100", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0x", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0x0x0", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0x1g", &result));
  EXPECT_EQ(0x23, result);
}

TEST(DecodeInteger, DecodeUInt8Binary) {
  ::std::uint8_t result;
  EXPECT_TRUE(DecodeInteger("0b10100101", &result));
  EXPECT_EQ(0xa5, result);
  EXPECT_TRUE(DecodeInteger("0b0", &result));
  EXPECT_EQ(0x0, result);
  EXPECT_TRUE(DecodeInteger("0B1", &result));
  EXPECT_EQ(0x1, result);
  EXPECT_TRUE(DecodeInteger("0b11111111", &result));
  EXPECT_EQ(0xff, result);
  EXPECT_TRUE(DecodeInteger("0b011111110", &result));
  EXPECT_EQ(0xfe, result);
  EXPECT_TRUE(DecodeInteger("0b00_0010_0011", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_TRUE(DecodeInteger("0b_0010_0011", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0b100000000", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0b", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0b0b0", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0b12", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("-0b0", &result));
  EXPECT_EQ(0x23, result);
}

TEST(DecodeInteger, DecodeInt8Binary) {
  ::std::int8_t result;
  EXPECT_TRUE(DecodeInteger("0b01011010", &result));
  EXPECT_EQ(0x5a, result);
  EXPECT_TRUE(DecodeInteger("0b0", &result));
  EXPECT_EQ(0x0, result);
  EXPECT_TRUE(DecodeInteger("0B1", &result));
  EXPECT_EQ(0x1, result);
  EXPECT_TRUE(DecodeInteger("0b1111111", &result));
  EXPECT_EQ(0x7f, result);
  EXPECT_TRUE(DecodeInteger("0b01111110", &result));
  EXPECT_EQ(0x7e, result);
  EXPECT_TRUE(DecodeInteger("0b00_0010_0011", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_TRUE(DecodeInteger("0b_0010_0011", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0b100000000", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0b", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("-0b", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0b0b0", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0b12", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_FALSE(DecodeInteger("0b10000000", &result));
  EXPECT_EQ(0x23, result);
  EXPECT_TRUE(DecodeInteger("-0b1111111", &result));
  EXPECT_EQ(-0x7f, result);
  EXPECT_TRUE(DecodeInteger("-0b10000000", &result));
  EXPECT_EQ(-0x80, result);
  EXPECT_FALSE(DecodeInteger("-0b10000001", &result));
  EXPECT_EQ(-0x80, result);
  EXPECT_TRUE(DecodeInteger("-0b0", &result));
  EXPECT_EQ(0x0, result);
}

TEST(DecodeInteger, DecodeUInt16) {
  ::std::uint16_t result;
  EXPECT_TRUE(DecodeInteger("65535", &result));
  EXPECT_EQ(65535, result);
  EXPECT_FALSE(DecodeInteger("65536", &result));
  EXPECT_EQ(65535, result);
}

TEST(DecodeInteger, DecodeInt16) {
  ::std::int16_t result;
  EXPECT_TRUE(DecodeInteger("32767", &result));
  EXPECT_EQ(32767, result);
  EXPECT_FALSE(DecodeInteger("32768", &result));
  EXPECT_EQ(32767, result);
  EXPECT_TRUE(DecodeInteger("-32768", &result));
  EXPECT_EQ(-32768, result);
  EXPECT_FALSE(DecodeInteger("-32769", &result));
  EXPECT_EQ(-32768, result);
}

TEST(DecodeInteger, DecodeUInt32) {
  ::std::uint32_t result;
  EXPECT_TRUE(DecodeInteger("4294967295", &result));
  EXPECT_EQ(4294967295U, result);
  EXPECT_FALSE(DecodeInteger("4294967296", &result));
  EXPECT_EQ(4294967295U, result);
}

TEST(DecodeInteger, DecodeInt32) {
  ::std::int32_t result;
  EXPECT_TRUE(DecodeInteger("2147483647", &result));
  EXPECT_EQ(2147483647, result);
  EXPECT_FALSE(DecodeInteger("2147483648", &result));
  EXPECT_EQ(2147483647, result);
  EXPECT_FALSE(DecodeInteger("4294967295", &result));
  EXPECT_EQ(2147483647, result);
  EXPECT_TRUE(DecodeInteger("-2147483648", &result));
  EXPECT_EQ(-2147483647 - 1, result);
  EXPECT_FALSE(DecodeInteger("-2147483649", &result));
  EXPECT_EQ(-2147483647 - 1, result);
}

TEST(DecodeInteger, DecodeUInt64) {
  ::std::uint64_t result;
  EXPECT_TRUE(DecodeInteger("18446744073709551615", &result));
  EXPECT_EQ(18446744073709551615ULL, result);
  EXPECT_FALSE(DecodeInteger("18446744073709551616", &result));
  EXPECT_EQ(18446744073709551615ULL, result);
}

TEST(DecodeInteger, DecodeInt64) {
  ::std::int64_t result;
  EXPECT_TRUE(DecodeInteger("9223372036854775807", &result));
  EXPECT_EQ(9223372036854775807LL, result);
  EXPECT_FALSE(DecodeInteger("9223372036854775808", &result));
  EXPECT_EQ(9223372036854775807LL, result);
  EXPECT_FALSE(DecodeInteger("18446744073709551615", &result));
  EXPECT_EQ(9223372036854775807LL, result);
  EXPECT_TRUE(DecodeInteger("-9223372036854775808", &result));
  EXPECT_EQ(-9223372036854775807LL - 1LL, result);
  EXPECT_FALSE(DecodeInteger("-9223372036854775809", &result));
  EXPECT_EQ(-9223372036854775807LL - 1LL, result);
}

TEST(TextStream, Construction) {
  ::std::string string_text = "ab";
  auto text_stream = TextStream(string_text);
  char result;
  EXPECT_TRUE(text_stream.Read(&result));
  EXPECT_EQ('a', result);
  EXPECT_TRUE(text_stream.Read(&result));
  EXPECT_EQ('b', result);
  EXPECT_FALSE(text_stream.Read(&result));

  const char *c_string = "cd";
  text_stream = TextStream(c_string);
  EXPECT_TRUE(text_stream.Read(&result));
  EXPECT_EQ('c', result);
  EXPECT_TRUE(text_stream.Read(&result));
  EXPECT_EQ('d', result);
  EXPECT_FALSE(text_stream.Read(&result));

  const char *long_c_string = "efghi";
  text_stream = TextStream(long_c_string, 2);
  EXPECT_TRUE(text_stream.Read(&result));
  EXPECT_EQ('e', result);
  EXPECT_TRUE(text_stream.Read(&result));
  EXPECT_EQ('f', result);
  EXPECT_FALSE(text_stream.Read(&result));
}

TEST(TextStream, Methods) {
  auto text_stream = TextStream{"abc"};

  EXPECT_FALSE(text_stream.Unread('d'));
  char result;
  EXPECT_TRUE(text_stream.Read(&result));
  EXPECT_EQ('a', result);

  EXPECT_FALSE(text_stream.Unread('e'));
  EXPECT_TRUE(text_stream.Read(&result));
  EXPECT_EQ('b', result);

  EXPECT_TRUE(text_stream.Unread('b'));
  result = 'f';
  EXPECT_TRUE(text_stream.Read(&result));
  EXPECT_EQ('b', result);

  EXPECT_TRUE(text_stream.Read(&result));
  EXPECT_EQ('c', result);

  result = 'g';
  EXPECT_FALSE(text_stream.Read(&result));
  EXPECT_EQ('g', result);

  auto empty_text_stream = TextStream{""};
  EXPECT_FALSE(empty_text_stream.Read(&result));
  EXPECT_EQ('g', result);
}

TEST(ReadToken, ReadsToken) {
  auto text_stream = TextStream{"abc"};
  ::std::string result;
  EXPECT_TRUE(ReadToken(&text_stream, &result));
  EXPECT_EQ("abc", result);
  EXPECT_TRUE(ReadToken(&text_stream, &result));
  EXPECT_EQ("", result);
  EXPECT_TRUE(ReadToken(&text_stream, &result));
  EXPECT_EQ("", result);
}

TEST(ReadToken, ReadsTwoTokens) {
  auto text_stream = TextStream{"abc def"};
  ::std::string result;
  EXPECT_TRUE(ReadToken(&text_stream, &result));
  EXPECT_EQ("abc", result);
  EXPECT_TRUE(ReadToken(&text_stream, &result));
  EXPECT_EQ("def", result);
  EXPECT_TRUE(ReadToken(&text_stream, &result));
  EXPECT_EQ("", result);
}

TEST(ReadToken, SkipsInitialWhitespace) {
  auto text_stream = TextStream{"  \t\r\r\n\t\r  abc def"};
  ::std::string result;
  EXPECT_TRUE(ReadToken(&text_stream, &result));
  EXPECT_EQ("abc", result);
  EXPECT_TRUE(ReadToken(&text_stream, &result));
  EXPECT_EQ("def", result);
  EXPECT_TRUE(ReadToken(&text_stream, &result));
  EXPECT_EQ("", result);
}

TEST(ReadToken, SkipsComments) {
  auto text_stream = TextStream{"  #comment##\r#comment\n abc #c\n  def"};
  ::std::string result;
  EXPECT_TRUE(ReadToken(&text_stream, &result));
  EXPECT_EQ("abc", result);
  EXPECT_TRUE(ReadToken(&text_stream, &result));
  EXPECT_EQ("def", result);
  EXPECT_TRUE(ReadToken(&text_stream, &result));
  EXPECT_EQ("", result);
}

TEST(TextOutputOptions, Defaults) {
  TextOutputOptions options;
  EXPECT_EQ("", options.current_indent());
  EXPECT_EQ("", options.indent());
  EXPECT_FALSE(options.multiline());
  EXPECT_FALSE(options.comments());
  EXPECT_FALSE(options.digit_grouping());
  EXPECT_EQ(10, options.numeric_base());
}

TEST(TextOutputOptions, WithIndent) {
  TextOutputOptions options;
  TextOutputOptions new_options = options.WithIndent("xyz");
  EXPECT_EQ("", options.current_indent());
  EXPECT_EQ("", options.indent());
  EXPECT_EQ("", new_options.current_indent());
  EXPECT_EQ("xyz", new_options.indent());
}

TEST(TextOutputOptions, PlusOneIndent) {
  TextOutputOptions options;
  TextOutputOptions new_options = options.WithIndent("xyz").PlusOneIndent();
  EXPECT_EQ("", options.current_indent());
  EXPECT_EQ("", options.indent());
  EXPECT_EQ("xyz", new_options.current_indent());
  EXPECT_EQ("xyz", new_options.indent());
  EXPECT_EQ("xyzxyz", new_options.PlusOneIndent().current_indent());
}

TEST(TextOutputOptions, WithComments) {
  TextOutputOptions options;
  TextOutputOptions new_options = options.WithComments(true);
  EXPECT_FALSE(options.comments());
  EXPECT_TRUE(new_options.comments());
}

TEST(TextOutputOptions, WithDigitGrouping) {
  TextOutputOptions options;
  TextOutputOptions new_options = options.WithDigitGrouping(true);
  EXPECT_FALSE(options.digit_grouping());
  EXPECT_TRUE(new_options.digit_grouping());
}

TEST(TextOutputOptions, Multiline) {
  TextOutputOptions options;
  TextOutputOptions new_options = options.Multiline(true);
  EXPECT_FALSE(options.multiline());
  EXPECT_TRUE(new_options.multiline());
}

TEST(TextOutputOptions, WithNumericBase) {
  TextOutputOptions options;
  TextOutputOptions new_options = options.WithNumericBase(2);
  EXPECT_EQ(10, options.numeric_base());
  EXPECT_EQ(2, new_options.numeric_base());
}

TEST(TextOutputOptions, WithAllowPartialOutput) {
  TextOutputOptions options;
  TextOutputOptions new_options = options.WithAllowPartialOutput(true);
  EXPECT_FALSE(options.allow_partial_output());
  EXPECT_TRUE(new_options.allow_partial_output());
}

// Small helper function for the various WriteIntegerToTextStream tests; just
// sets up a stream, forwards its arguments to WriteIntegerToTextStream, and
// then returns the text from the stream.
template <typename Arg0, typename... Args>
::std::string WriteIntegerToString(Arg0 &&arg0, Args &&... args) {
  TextOutputStream stream;
  WriteIntegerToTextStream(::std::forward<Arg0>(arg0), &stream,
                           ::std::forward<Args>(args)...);
  return stream.Result();
}

TEST(WriteIntegerToTextStream, Decimal) {
  EXPECT_EQ("0", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(0), 10,
                                      false));
  EXPECT_EQ("100", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(100),
                                        10, false));
  EXPECT_EQ("255", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(255),
                                        10, false));
  EXPECT_EQ("-128", WriteIntegerToString(static_cast</**/ ::std::int8_t>(-128),
                                         10, false));
  EXPECT_EQ("-100", WriteIntegerToString(static_cast</**/ ::std::int8_t>(-100),
                                         10, false));
  EXPECT_EQ(
      "0", WriteIntegerToString(static_cast</**/ ::std::int8_t>(0), 10, false));
  EXPECT_EQ("100", WriteIntegerToString(static_cast</**/ ::std::int8_t>(100),
                                        10, false));
  EXPECT_EQ("127", WriteIntegerToString(static_cast</**/ ::std::int8_t>(127),
                                        10, false));

  EXPECT_EQ(
      "0", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(0), 10, true));
  EXPECT_EQ("100", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(100),
                                        10, true));
  EXPECT_EQ("255", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(255),
                                        10, true));
  EXPECT_EQ("-128", WriteIntegerToString(static_cast</**/ ::std::int8_t>(-128),
                                         10, true));
  EXPECT_EQ("-100", WriteIntegerToString(static_cast</**/ ::std::int8_t>(-100),
                                         10, true));
  EXPECT_EQ("0",
            WriteIntegerToString(static_cast</**/ ::std::int8_t>(0), 10, true));
  EXPECT_EQ("100", WriteIntegerToString(static_cast</**/ ::std::int8_t>(100),
                                        10, true));
  EXPECT_EQ("127", WriteIntegerToString(static_cast</**/ ::std::int8_t>(127),
                                        10, true));

  EXPECT_EQ("0", WriteIntegerToString(static_cast</**/ ::std::uint16_t>(0), 10,
                                      false));
  EXPECT_EQ("1000", WriteIntegerToString(
                        static_cast</**/ ::std::uint16_t>(1000), 10, false));
  EXPECT_EQ("65535", WriteIntegerToString(
                         static_cast</**/ ::std::uint16_t>(65535), 10, false));
  EXPECT_EQ("-32768", WriteIntegerToString(
                          static_cast</**/ ::std::int16_t>(-32768), 10, false));
  EXPECT_EQ("-10000", WriteIntegerToString(
                          static_cast</**/ ::std::int16_t>(-10000), 10, false));
  EXPECT_EQ("0", WriteIntegerToString(static_cast</**/ ::std::int16_t>(0), 10,
                                      false));
  EXPECT_EQ("32767", WriteIntegerToString(
                         static_cast</**/ ::std::int16_t>(32767), 10, false));

  EXPECT_EQ("0", WriteIntegerToString(static_cast</**/ ::std::uint16_t>(0), 10,
                                      true));
  EXPECT_EQ("999", WriteIntegerToString(static_cast</**/ ::std::uint16_t>(999),
                                        10, true));
  EXPECT_EQ("1_000", WriteIntegerToString(
                         static_cast</**/ ::std::uint16_t>(1000), 10, true));
  EXPECT_EQ("65_535", WriteIntegerToString(
                          static_cast</**/ ::std::uint16_t>(65535), 10, true));
  EXPECT_EQ("-32_768", WriteIntegerToString(
                           static_cast</**/ ::std::int16_t>(-32768), 10, true));
  EXPECT_EQ("-1_000", WriteIntegerToString(
                          static_cast</**/ ::std::int16_t>(-1000), 10, true));
  EXPECT_EQ("-999", WriteIntegerToString(static_cast</**/ ::std::int16_t>(-999),
                                         10, true));
  EXPECT_EQ(
      "0", WriteIntegerToString(static_cast</**/ ::std::int16_t>(0), 10, true));
  EXPECT_EQ("32_767", WriteIntegerToString(
                          static_cast</**/ ::std::int16_t>(32767), 10, true));

  EXPECT_EQ("0", WriteIntegerToString(static_cast</**/ ::std::uint32_t>(0), 10,
                                      false));
  EXPECT_EQ("1000000",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(1000000), 10,
                                 false));
  EXPECT_EQ("4294967295",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(4294967295),
                                 10, false));
  EXPECT_EQ("-2147483648",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-2147483648),
                                 10, false));
  EXPECT_EQ("-100000",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-100000), 10,
                                 false));
  EXPECT_EQ("0", WriteIntegerToString(static_cast</**/ ::std::int32_t>(0), 10,
                                      false));
  EXPECT_EQ("2147483647",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(2147483647),
                                 10, false));

  EXPECT_EQ("0", WriteIntegerToString(static_cast</**/ ::std::uint32_t>(0), 10,
                                      true));
  EXPECT_EQ("999_999",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(999999), 10,
                                 true));
  EXPECT_EQ("1_000_000",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(1000000), 10,
                                 true));
  EXPECT_EQ("4_294_967_295",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(4294967295U),
                                 10, true));
  EXPECT_EQ("-2_147_483_648",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-2147483648L),
                                 10, true));
  EXPECT_EQ("-999_999",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-999999), 10,
                                 true));
  EXPECT_EQ("-1_000_000",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-1000000), 10,
                                 true));
  EXPECT_EQ(
      "0", WriteIntegerToString(static_cast</**/ ::std::int32_t>(0), 10, true));
  EXPECT_EQ("2_147_483_647",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(2147483647),
                                 10, true));

  EXPECT_EQ("0", WriteIntegerToString(static_cast</**/ ::std::uint64_t>(0), 10,
                                      false));
  EXPECT_EQ("1000000",
            WriteIntegerToString(static_cast</**/ ::std::uint64_t>(1000000), 10,
                                 false));
  EXPECT_EQ("18446744073709551615",
            WriteIntegerToString(
                static_cast</**/ ::std::uint64_t>(18446744073709551615UL), 10,
                false));
  EXPECT_EQ("-9223372036854775808",
            WriteIntegerToString(
                static_cast</**/ ::std::int64_t>(-9223372036854775807L - 1), 10,
                false));
  EXPECT_EQ("-100000",
            WriteIntegerToString(static_cast</**/ ::std::int64_t>(-100000), 10,
                                 false));
  EXPECT_EQ("0", WriteIntegerToString(static_cast</**/ ::std::int64_t>(0), 10,
                                      false));
  EXPECT_EQ(
      "9223372036854775807",
      WriteIntegerToString(
          static_cast</**/ ::std::int64_t>(9223372036854775807L), 10, false));

  EXPECT_EQ("0", WriteIntegerToString(static_cast</**/ ::std::uint64_t>(0), 10,
                                      true));
  EXPECT_EQ("1_000_000",
            WriteIntegerToString(static_cast</**/ ::std::uint64_t>(1000000), 10,
                                 true));
  EXPECT_EQ(
      "18_446_744_073_709_551_615",
      WriteIntegerToString(
          static_cast</**/ ::std::uint64_t>(18446744073709551615UL), 10, true));
  EXPECT_EQ("-9_223_372_036_854_775_808",
            WriteIntegerToString(
                static_cast</**/ ::std::int64_t>(-9223372036854775807L - 1), 10,
                true));
  EXPECT_EQ("-100_000",
            WriteIntegerToString(static_cast</**/ ::std::int64_t>(-100000), 10,
                                 true));
  EXPECT_EQ(
      "0", WriteIntegerToString(static_cast</**/ ::std::int64_t>(0), 10, true));
  EXPECT_EQ(
      "9_223_372_036_854_775_807",
      WriteIntegerToString(
          static_cast</**/ ::std::int64_t>(9223372036854775807L), 10, true));
}

TEST(WriteIntegerToTextStream, Binary) {
  EXPECT_EQ("0b0", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(0), 2,
                                        false));
  EXPECT_EQ("0b1100100", WriteIntegerToString(
                             static_cast</**/ ::std::uint8_t>(100), 2, false));
  EXPECT_EQ("0b11111111", WriteIntegerToString(
                              static_cast</**/ ::std::uint8_t>(255), 2, false));
  EXPECT_EQ(
      "-0b10000000",
      WriteIntegerToString(static_cast</**/ ::std::int8_t>(-128), 2, false));
  EXPECT_EQ("-0b1100100", WriteIntegerToString(
                              static_cast</**/ ::std::int8_t>(-100), 2, false));
  EXPECT_EQ("0b0",
            WriteIntegerToString(static_cast</**/ ::std::int8_t>(0), 2, false));
  EXPECT_EQ("0b1100100", WriteIntegerToString(
                             static_cast</**/ ::std::int8_t>(100), 2, false));
  EXPECT_EQ("0b1111111", WriteIntegerToString(
                             static_cast</**/ ::std::int8_t>(127), 2, false));

  EXPECT_EQ("0b0",
            WriteIntegerToString(static_cast</**/ ::std::uint8_t>(0), 2, true));
  EXPECT_EQ("0b1100100", WriteIntegerToString(
                             static_cast</**/ ::std::uint8_t>(100), 2, true));
  EXPECT_EQ("0b11111111", WriteIntegerToString(
                              static_cast</**/ ::std::uint8_t>(255), 2, true));
  EXPECT_EQ("-0b10000000", WriteIntegerToString(
                               static_cast</**/ ::std::int8_t>(-128), 2, true));
  EXPECT_EQ("-0b1100100", WriteIntegerToString(
                              static_cast</**/ ::std::int8_t>(-100), 2, true));
  EXPECT_EQ("0b0",
            WriteIntegerToString(static_cast</**/ ::std::int8_t>(0), 2, true));
  EXPECT_EQ("0b1100100", WriteIntegerToString(
                             static_cast</**/ ::std::int8_t>(100), 2, true));
  EXPECT_EQ("0b1111111", WriteIntegerToString(
                             static_cast</**/ ::std::int8_t>(127), 2, true));

  EXPECT_EQ("0b0", WriteIntegerToString(static_cast</**/ ::std::uint16_t>(0), 2,
                                        false));
  EXPECT_EQ(
      "0b1111101000",
      WriteIntegerToString(static_cast</**/ ::std::uint16_t>(1000), 2, false));
  EXPECT_EQ(
      "0b1111111111111111",
      WriteIntegerToString(static_cast</**/ ::std::uint16_t>(65535), 2, false));
  EXPECT_EQ(
      "-0b1000000000000000",
      WriteIntegerToString(static_cast</**/ ::std::int16_t>(-32768), 2, false));
  EXPECT_EQ(
      "-0b10011100010000",
      WriteIntegerToString(static_cast</**/ ::std::int16_t>(-10000), 2, false));
  EXPECT_EQ("0b0", WriteIntegerToString(static_cast</**/ ::std::int16_t>(0), 2,
                                        false));
  EXPECT_EQ(
      "0b111111111111111",
      WriteIntegerToString(static_cast</**/ ::std::int16_t>(32767), 2, false));

  EXPECT_EQ("0b0", WriteIntegerToString(static_cast</**/ ::std::uint16_t>(0), 2,
                                        true));
  EXPECT_EQ(
      "0b11_11101000",
      WriteIntegerToString(static_cast</**/ ::std::uint16_t>(1000), 2, true));
  EXPECT_EQ(
      "0b11111111_11111111",
      WriteIntegerToString(static_cast</**/ ::std::uint16_t>(65535), 2, true));
  EXPECT_EQ(
      "-0b10000000_00000000",
      WriteIntegerToString(static_cast</**/ ::std::int16_t>(-32768), 2, true));
  EXPECT_EQ(
      "-0b11_11101000",
      WriteIntegerToString(static_cast</**/ ::std::int16_t>(-1000), 2, true));
  EXPECT_EQ(
      "-0b11_11100111",
      WriteIntegerToString(static_cast</**/ ::std::int16_t>(-999), 2, true));
  EXPECT_EQ("0b0",
            WriteIntegerToString(static_cast</**/ ::std::int16_t>(0), 2, true));
  EXPECT_EQ(
      "0b1111111_11111111",
      WriteIntegerToString(static_cast</**/ ::std::int16_t>(32767), 2, true));

  EXPECT_EQ("0b0", WriteIntegerToString(static_cast</**/ ::std::uint32_t>(0), 2,
                                        false));
  EXPECT_EQ("0b11110100001001000000",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(1000000), 2,
                                 false));
  EXPECT_EQ("0b11111111111111111111111111111111",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(4294967295),
                                 2, false));
  EXPECT_EQ("-0b10000000000000000000000000000000",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-2147483648),
                                 2, false));
  EXPECT_EQ("-0b11000011010100000",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-100000), 2,
                                 false));
  EXPECT_EQ("0b0", WriteIntegerToString(static_cast</**/ ::std::int32_t>(0), 2,
                                        false));
  EXPECT_EQ("0b1111111111111111111111111111111",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(2147483647),
                                 2, false));

  EXPECT_EQ("0b0", WriteIntegerToString(static_cast</**/ ::std::uint32_t>(0), 2,
                                        true));
  EXPECT_EQ("0b1111_01000010_01000000",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(1000000), 2,
                                 true));
  EXPECT_EQ("0b11111111_11111111_11111111_11111111",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(4294967295U),
                                 2, true));
  EXPECT_EQ("-0b10000000_00000000_00000000_00000000",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-2147483648L),
                                 2, true));
  EXPECT_EQ("-0b1111_01000010_01000000",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-1000000), 2,
                                 true));
  EXPECT_EQ("0b0",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(0), 2, true));
  EXPECT_EQ("0b1111111_11111111_11111111_11111111",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(2147483647),
                                 2, true));

  EXPECT_EQ("0b0", WriteIntegerToString(static_cast</**/ ::std::uint64_t>(0), 2,
                                        false));
  EXPECT_EQ("0b11110100001001000000",
            WriteIntegerToString(static_cast</**/ ::std::uint64_t>(1000000), 2,
                                 false));
  EXPECT_EQ(
      "0b1111111111111111111111111111111111111111111111111111111111111111",
      WriteIntegerToString(
          static_cast</**/ ::std::uint64_t>(18446744073709551615UL), 2, false));
  EXPECT_EQ(
      "-0b1000000000000000000000000000000000000000000000000000000000000000",
      WriteIntegerToString(
          static_cast</**/ ::std::int64_t>(-9223372036854775807L - 1), 2,
          false));
  EXPECT_EQ("-0b11000011010100000",
            WriteIntegerToString(static_cast</**/ ::std::int64_t>(-100000), 2,
                                 false));
  EXPECT_EQ("0b0", WriteIntegerToString(static_cast</**/ ::std::int64_t>(0), 2,
                                        false));
  EXPECT_EQ(
      "0b111111111111111111111111111111111111111111111111111111111111111",
      WriteIntegerToString(
          static_cast</**/ ::std::int64_t>(9223372036854775807L), 2, false));

  EXPECT_EQ("0b0", WriteIntegerToString(static_cast</**/ ::std::uint64_t>(0), 2,
                                        true));
  EXPECT_EQ("0b1111_01000010_01000000",
            WriteIntegerToString(static_cast</**/ ::std::uint64_t>(1000000), 2,
                                 true));
  EXPECT_EQ(
      "0b11111111_11111111_11111111_11111111_11111111_11111111_11111111_"
      "11111111",
      WriteIntegerToString(
          static_cast</**/ ::std::uint64_t>(18446744073709551615UL), 2, true));
  EXPECT_EQ(
      "-0b10000000_00000000_00000000_00000000_00000000_00000000_00000000_"
      "00000000",
      WriteIntegerToString(
          static_cast</**/ ::std::int64_t>(-9223372036854775807L - 1), 2,
          true));
  EXPECT_EQ(
      "-0b1_10000110_10100000",
      WriteIntegerToString(static_cast</**/ ::std::int64_t>(-100000), 2, true));
  EXPECT_EQ("0b0",
            WriteIntegerToString(static_cast</**/ ::std::int64_t>(0), 2, true));
  EXPECT_EQ(
      "0b1111111_11111111_11111111_11111111_11111111_11111111_11111111_"
      "11111111",
      WriteIntegerToString(
          static_cast</**/ ::std::int64_t>(9223372036854775807L), 2, true));
}

TEST(WriteIntegerToTextStream, Hexadecimal) {
  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(0), 16,
                                        false));
  EXPECT_EQ("0x64", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(100),
                                         16, false));
  EXPECT_EQ("0xff", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(255),
                                         16, false));
  EXPECT_EQ("-0x80", WriteIntegerToString(static_cast</**/ ::std::int8_t>(-128),
                                          16, false));
  EXPECT_EQ("-0x64", WriteIntegerToString(static_cast</**/ ::std::int8_t>(-100),
                                          16, false));
  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::int8_t>(0), 16,
                                        false));
  EXPECT_EQ("0x64", WriteIntegerToString(static_cast</**/ ::std::int8_t>(100),
                                         16, false));
  EXPECT_EQ("0x7f", WriteIntegerToString(static_cast</**/ ::std::int8_t>(127),
                                         16, false));

  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(0), 16,
                                        true));
  EXPECT_EQ("0x64", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(100),
                                         16, true));
  EXPECT_EQ("0xff", WriteIntegerToString(static_cast</**/ ::std::uint8_t>(255),
                                         16, true));
  EXPECT_EQ("-0x80", WriteIntegerToString(static_cast</**/ ::std::int8_t>(-128),
                                          16, true));
  EXPECT_EQ("-0x64", WriteIntegerToString(static_cast</**/ ::std::int8_t>(-100),
                                          16, true));
  EXPECT_EQ("0x0",
            WriteIntegerToString(static_cast</**/ ::std::int8_t>(0), 16, true));
  EXPECT_EQ("0x64", WriteIntegerToString(static_cast</**/ ::std::int8_t>(100),
                                         16, true));
  EXPECT_EQ("0x7f", WriteIntegerToString(static_cast</**/ ::std::int8_t>(127),
                                         16, true));

  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::uint16_t>(0),
                                        16, false));
  EXPECT_EQ("0x3e8", WriteIntegerToString(
                         static_cast</**/ ::std::uint16_t>(1000), 16, false));
  EXPECT_EQ("0xffff", WriteIntegerToString(
                          static_cast</**/ ::std::uint16_t>(65535), 16, false));
  EXPECT_EQ("-0x8000",
            WriteIntegerToString(static_cast</**/ ::std::int16_t>(-32768), 16,
                                 false));
  EXPECT_EQ("-0x2710",
            WriteIntegerToString(static_cast</**/ ::std::int16_t>(-10000), 16,
                                 false));
  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::int16_t>(0), 16,
                                        false));
  EXPECT_EQ("0x7fff", WriteIntegerToString(
                          static_cast</**/ ::std::int16_t>(32767), 16, false));

  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::uint16_t>(0),
                                        16, true));
  EXPECT_EQ("0x3e8", WriteIntegerToString(
                         static_cast</**/ ::std::uint16_t>(1000), 16, true));
  EXPECT_EQ("0xffff", WriteIntegerToString(
                          static_cast</**/ ::std::uint16_t>(65535), 16, true));
  EXPECT_EQ("-0x8000", WriteIntegerToString(
                           static_cast</**/ ::std::int16_t>(-32768), 16, true));
  EXPECT_EQ("-0x3e8", WriteIntegerToString(
                          static_cast</**/ ::std::int16_t>(-1000), 16, true));
  EXPECT_EQ("-0x3e7", WriteIntegerToString(
                          static_cast</**/ ::std::int16_t>(-999), 16, true));
  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::int16_t>(0), 16,
                                        true));
  EXPECT_EQ("0x7fff", WriteIntegerToString(
                          static_cast</**/ ::std::int16_t>(32767), 16, true));

  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::uint32_t>(0),
                                        16, false));
  EXPECT_EQ("0xf4240",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(1000000), 16,
                                 false));
  EXPECT_EQ("0xffffffff",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(4294967295),
                                 16, false));
  EXPECT_EQ("-0x80000000",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-2147483648),
                                 16, false));
  EXPECT_EQ("-0x186a0",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-100000), 16,
                                 false));
  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::int32_t>(0), 16,
                                        false));
  EXPECT_EQ("0x7fffffff",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(2147483647),
                                 16, false));

  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::uint32_t>(0),
                                        16, true));
  EXPECT_EQ("0xf_4240",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(1000000), 16,
                                 true));
  EXPECT_EQ("0xffff_ffff",
            WriteIntegerToString(static_cast</**/ ::std::uint32_t>(4294967295U),
                                 16, true));
  EXPECT_EQ("-0x8000_0000",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-2147483648L),
                                 16, true));
  EXPECT_EQ("-0xf_4240",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(-1000000), 16,
                                 true));
  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::int32_t>(0), 16,
                                        true));
  EXPECT_EQ("0x7fff_ffff",
            WriteIntegerToString(static_cast</**/ ::std::int32_t>(2147483647),
                                 16, true));

  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::uint64_t>(0),
                                        16, false));
  EXPECT_EQ("0xf4240",
            WriteIntegerToString(static_cast</**/ ::std::uint64_t>(1000000), 16,
                                 false));
  EXPECT_EQ("0xffffffffffffffff",
            WriteIntegerToString(
                static_cast</**/ ::std::uint64_t>(18446744073709551615UL), 16,
                false));
  EXPECT_EQ("-0x8000000000000000",
            WriteIntegerToString(
                static_cast</**/ ::std::int64_t>(-9223372036854775807L - 1), 16,
                false));
  EXPECT_EQ("-0x186a0",
            WriteIntegerToString(static_cast</**/ ::std::int64_t>(-100000), 16,
                                 false));
  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::int64_t>(0), 16,
                                        false));
  EXPECT_EQ(
      "0x7fffffffffffffff",
      WriteIntegerToString(
          static_cast</**/ ::std::int64_t>(9223372036854775807L), 16, false));

  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::uint64_t>(0),
                                        16, true));
  EXPECT_EQ("0xf_4240",
            WriteIntegerToString(static_cast</**/ ::std::uint64_t>(1000000), 16,
                                 true));
  EXPECT_EQ(
      "0xffff_ffff_ffff_ffff",
      WriteIntegerToString(
          static_cast</**/ ::std::uint64_t>(18446744073709551615UL), 16, true));
  EXPECT_EQ("-0x8000_0000_0000_0000",
            WriteIntegerToString(
                static_cast</**/ ::std::int64_t>(-9223372036854775807L - 1), 16,
                true));
  EXPECT_EQ("-0x1_86a0",
            WriteIntegerToString(static_cast</**/ ::std::int64_t>(-100000), 16,
                                 true));
  EXPECT_EQ("0x0", WriteIntegerToString(static_cast</**/ ::std::int64_t>(0), 16,
                                        true));
  EXPECT_EQ(
      "0x7fff_ffff_ffff_ffff",
      WriteIntegerToString(
          static_cast</**/ ::std::int64_t>(9223372036854775807L), 16, true));
}

// Small helper function for the various WriteFloatToTextStream tests; just sets
// up a stream, forwards its arguments to WriteFloatToTextStream, and then
// returns the text from the stream.
template <typename Arg0, typename... Args>
::std::string WriteFloatToString(Arg0 &&arg0, Args &&... args) {
  TextOutputStream stream;
  WriteFloatToTextStream(::std::forward<Arg0>(arg0), &stream,
                         ::std::forward<Args>(args)...);
  return stream.Result();
}

TEST(WriteFloatToTextStream, RegularNumbers) {
  EXPECT_EQ("0", WriteFloatToString(0.0, TextOutputOptions()));
  EXPECT_EQ("1", WriteFloatToString(1.0, TextOutputOptions()));
  EXPECT_EQ("1.5", WriteFloatToString(1.5, TextOutputOptions()));
  // TODO(bolms): Figure out how to get minimal-length output.
  EXPECT_EQ("1.6000000000000001", WriteFloatToString(1.6, TextOutputOptions()));
  EXPECT_EQ("123456789", WriteFloatToString(123456789.0, TextOutputOptions()));
  EXPECT_EQ("12345678901234568",
            WriteFloatToString(12345678901234567.0, TextOutputOptions()));
  EXPECT_EQ("-12345678901234568",
            WriteFloatToString(-12345678901234567.0, TextOutputOptions()));
  EXPECT_EQ("-1.2345678901234568e+17",
            WriteFloatToString(-123456789012345678.0, TextOutputOptions()));
  EXPECT_EQ("4.9406564584124654e-324",
            WriteFloatToString(::std::numeric_limits<double>::denorm_min(),
                               TextOutputOptions()));
  EXPECT_EQ("1.7976931348623157e+308",
            WriteFloatToString(::std::numeric_limits<double>::max(),
                               TextOutputOptions()));

  EXPECT_EQ("0", WriteFloatToString(0.0f, TextOutputOptions()));
  EXPECT_EQ("1", WriteFloatToString(1.0f, TextOutputOptions()));
  EXPECT_EQ("1.5", WriteFloatToString(1.5f, TextOutputOptions()));
  EXPECT_EQ("1.60000002", WriteFloatToString(1.6f, TextOutputOptions()));
  EXPECT_EQ("123456792", WriteFloatToString(123456789.0f, TextOutputOptions()));
  EXPECT_EQ("1.23456784e+16",
            WriteFloatToString(12345678901234567.0f, TextOutputOptions()));
  EXPECT_EQ("-1.23456784e+16",
            WriteFloatToString(-12345678901234567.0f, TextOutputOptions()));
  EXPECT_EQ("-1.00000003e+16",
            WriteFloatToString(-10000000000000000.0f, TextOutputOptions()));
  EXPECT_EQ("1.40129846e-45",
            WriteFloatToString(::std::numeric_limits<float>::denorm_min(),
                               TextOutputOptions()));
  EXPECT_EQ("3.40282347e+38",
            WriteFloatToString(::std::numeric_limits<float>::max(),
                               TextOutputOptions()));
}

TEST(WriteFloatToTextStream, Infinities) {
  EXPECT_EQ("Inf", WriteFloatToString(2 * ::std::numeric_limits<double>::max(),
                                      TextOutputOptions()));
  EXPECT_EQ("Inf", WriteFloatToString(2 * ::std::numeric_limits<float>::max(),
                                      TextOutputOptions()));
  EXPECT_EQ("-Inf",
            WriteFloatToString(-2 * ::std::numeric_limits<double>::max(),
                               TextOutputOptions()));
  EXPECT_EQ("-Inf", WriteFloatToString(-2 * ::std::numeric_limits<float>::max(),
                                       TextOutputOptions()));
}

// C++ does not provide great low-level manipulation for NaNs, so we resort to
// this mess.
double MakeNanDouble(::std::uint64_t payload, int sign) {
  payload |= 0x7ff0000000000000UL;
  if (sign < 0) {
    payload |= 0x8000000000000000UL;
  }
  double result;
  ::std::memcpy(&result, &payload, sizeof result);
  return result;
}

float MakeNanFloat(::std::uint32_t payload, int sign) {
  payload |= 0x7f800000U;
  if (sign < 0) {
    payload |= 0x80000000U;
  }
  float result;
  ::std::memcpy(&result, &payload, sizeof result);
  return result;
}

TEST(WriteFloatToTextStream, Nans) {
  EXPECT_EQ("NaN(0x1)",
            WriteFloatToString(MakeNanDouble(1, 0), TextOutputOptions()));
  EXPECT_EQ("NaN(0x1)",
            WriteFloatToString(MakeNanFloat(1, 0), TextOutputOptions()));
  EXPECT_EQ("NaN(0x10000)",
            WriteFloatToString(MakeNanDouble(0x10000, 0), TextOutputOptions()));
  EXPECT_EQ("NaN(0x7fffff)", WriteFloatToString(MakeNanFloat(0x7fffffU, 0),
                                                TextOutputOptions()));
  EXPECT_EQ("NaN(0xfffffffffffff)",
            WriteFloatToString(MakeNanDouble(0xfffffffffffffUL, 0),
                               TextOutputOptions()));
  EXPECT_EQ("-NaN(0x7fffff)", WriteFloatToString(MakeNanFloat(0x7fffffU, -1),
                                                 TextOutputOptions()));
  EXPECT_EQ("-NaN(0xfffffffffffff)",
            WriteFloatToString(MakeNanDouble(0xfffffffffffffUL, -1),
                               TextOutputOptions()));
  EXPECT_EQ("NaN(0x10000)",
            WriteFloatToString(MakeNanFloat(0x10000, 0), TextOutputOptions()));
  EXPECT_EQ("-NaN(0x1)",
            WriteFloatToString(MakeNanDouble(1, -1), TextOutputOptions()));
  EXPECT_EQ("-NaN(0x1)",
            WriteFloatToString(MakeNanFloat(1, -1), TextOutputOptions()));
  EXPECT_EQ("-NaN(0x10000)", WriteFloatToString(MakeNanDouble(0x10000, -1),
                                                TextOutputOptions()));
  EXPECT_EQ("-NaN(0x10000)",
            WriteFloatToString(MakeNanFloat(0x10000, -1), TextOutputOptions()));
  EXPECT_EQ("-NaN(0x1_0000)",
            WriteFloatToString(MakeNanDouble(0x10000, -1),
                               TextOutputOptions().WithDigitGrouping(true)));
  EXPECT_EQ("-NaN(0x1_0000)",
            WriteFloatToString(MakeNanFloat(0x10000, -1),
                               TextOutputOptions().WithDigitGrouping(true)));
}

TEST(DecodeFloat, RegularNumbers) {
  double double_result;
  EXPECT_TRUE(DecodeFloat("0", &double_result));
  EXPECT_EQ(0.0, double_result);
  EXPECT_FALSE(::std::signbit(double_result));
  EXPECT_TRUE(DecodeFloat("-0", &double_result));
  EXPECT_EQ(0.0, double_result);
  EXPECT_TRUE(::std::signbit(double_result));
  EXPECT_TRUE(DecodeFloat("0.0", &double_result));
  EXPECT_EQ(0.0, double_result);
  EXPECT_TRUE(DecodeFloat("0.0e100", &double_result));
  EXPECT_EQ(0.0, double_result);
  EXPECT_TRUE(DecodeFloat("0x0.0p100", &double_result));
  EXPECT_EQ(0.0, double_result);
  EXPECT_TRUE(DecodeFloat("1", &double_result));
  EXPECT_EQ(1.0, double_result);
  EXPECT_TRUE(DecodeFloat("1.5", &double_result));
  EXPECT_EQ(1.5, double_result);
  EXPECT_TRUE(DecodeFloat("1.6", &double_result));
  EXPECT_EQ(1.6, double_result);
  EXPECT_TRUE(DecodeFloat("1.6000000000000001", &double_result));
  EXPECT_EQ(1.6, double_result);
  EXPECT_TRUE(DecodeFloat("123456789", &double_result));
  EXPECT_EQ(123456789.0, double_result);
  EXPECT_TRUE(DecodeFloat("-1.234567890123458e+17", &double_result));
  EXPECT_EQ(-1.234567890123458e+17, double_result);
  EXPECT_TRUE(DecodeFloat("4.9406564584124654e-324", &double_result));
  EXPECT_EQ(4.9406564584124654e-324, double_result);
  EXPECT_TRUE(DecodeFloat("1.7976931348623157e+308", &double_result));
  EXPECT_EQ(1.7976931348623157e+308, double_result);
  EXPECT_TRUE(DecodeFloat(
      "000000000000000000000000000004.9406564584124654e-324", &double_result));
  EXPECT_EQ(4.9406564584124654e-324, double_result);

  float float_result;
  EXPECT_TRUE(DecodeFloat("0", &float_result));
  EXPECT_EQ(0.0f, float_result);
  EXPECT_FALSE(::std::signbit(float_result));
  EXPECT_TRUE(DecodeFloat("-0", &float_result));
  EXPECT_EQ(0.0f, float_result);
  EXPECT_TRUE(::std::signbit(float_result));
  EXPECT_TRUE(DecodeFloat("0.0", &float_result));
  EXPECT_EQ(0.0f, float_result);
  EXPECT_TRUE(DecodeFloat("0.0e100", &float_result));
  EXPECT_EQ(0.0f, float_result);
  EXPECT_TRUE(DecodeFloat("0x0.0p100", &float_result));
  EXPECT_EQ(0.0f, float_result);
  EXPECT_TRUE(DecodeFloat("1", &float_result));
  EXPECT_EQ(1.0f, float_result);
  EXPECT_TRUE(DecodeFloat("1.5", &float_result));
  EXPECT_EQ(1.5f, float_result);
  EXPECT_TRUE(DecodeFloat("1.6", &float_result));
  EXPECT_EQ(1.6f, float_result);
  EXPECT_TRUE(DecodeFloat("1.6000000000000001", &float_result));
  EXPECT_EQ(1.6f, float_result);
  EXPECT_TRUE(DecodeFloat("123456789", &float_result));
  EXPECT_EQ(123456789.0f, float_result);
  EXPECT_TRUE(DecodeFloat("-1.23456784e+16", &float_result));
  EXPECT_EQ(-1.23456784e+16f, float_result);
  EXPECT_TRUE(DecodeFloat("1.40129846e-45", &float_result));
  EXPECT_EQ(1.40129846e-45f, float_result);
  EXPECT_TRUE(DecodeFloat("3.40282347e+38", &float_result));
  EXPECT_EQ(3.40282347e+38f, float_result);

  // TODO(bolms): "_"-grouped numbers, like "123_456.789", should probably be
  // allowed.
}

TEST(DecodeFloat, BadValues) {
  double result;
  float float_result;

  // No text is not a value.
  EXPECT_FALSE(DecodeFloat("", &result));

  // Trailing characters after "Inf" are not allowed.
  EXPECT_FALSE(DecodeFloat("INF+", &result));
  EXPECT_FALSE(DecodeFloat("Infinity", &result));

  // Trailing characters after "NaN" are not allowed.
  EXPECT_FALSE(DecodeFloat("NaN(", &result));
  EXPECT_FALSE(DecodeFloat("NaN(0]", &result));
  EXPECT_FALSE(DecodeFloat("NaNaNaNa", &result));

  // Non-number NaN payloads are not allowed.
  EXPECT_FALSE(DecodeFloat("NaN()", &result));
  EXPECT_FALSE(DecodeFloat("NaN(x)", &result));
  EXPECT_FALSE(DecodeFloat("NaN(0x)", &result));

  // Negative NaN payloads are not allowed.
  EXPECT_FALSE(DecodeFloat("NaN(-1)", &result));
  EXPECT_FALSE(DecodeFloat("NaN(-0)", &result));

  // NaN with zero payload is infinity, and is thus not allowed.
  EXPECT_FALSE(DecodeFloat("NaN(0)", &result));
  EXPECT_FALSE(DecodeFloat("-NaN(0)", &result));

  // NaN double payloads must be no more than 52 bits.
  EXPECT_FALSE(DecodeFloat("NaN(0x10_0000_0000_0000)", &result));
  EXPECT_FALSE(DecodeFloat("NaN(0x8000_0000_0000_0000)", &result));
  EXPECT_FALSE(DecodeFloat("NaN(0x1_0000_0000_0000_0000)", &result));

  // NaN float payloads must be no more than 23 bits.
  EXPECT_FALSE(DecodeFloat("NaN(0x80_0000)", &float_result));
  EXPECT_FALSE(DecodeFloat("NaN(0x8000_0000)", &float_result));
  EXPECT_FALSE(DecodeFloat("NaN(0x1_0000_0000)", &float_result));

  // Trailing characters after regular values are not allowed.
  EXPECT_FALSE(DecodeFloat("0x", &result));
  EXPECT_FALSE(DecodeFloat("0e0a", &result));
  EXPECT_FALSE(DecodeFloat("0b0", &result));
  EXPECT_FALSE(DecodeFloat("0a", &result));
  EXPECT_FALSE(DecodeFloat("1..", &result));

  // Grouping characters like "," should not be allowed.
  EXPECT_FALSE(DecodeFloat("123,456", &result));
  EXPECT_FALSE(DecodeFloat("123'456", &result));
}

TEST(DecodeFloat, Infinities) {
  double double_result;
  EXPECT_TRUE(DecodeFloat("Inf", &double_result));
  EXPECT_TRUE(::std::isinf(double_result));
  EXPECT_FALSE(::std::signbit(double_result));
  EXPECT_TRUE(DecodeFloat("-Inf", &double_result));
  EXPECT_TRUE(::std::isinf(double_result));
  EXPECT_TRUE(::std::signbit(double_result));
  EXPECT_TRUE(DecodeFloat("+Inf", &double_result));
  EXPECT_TRUE(::std::isinf(double_result));
  EXPECT_FALSE(::std::signbit(double_result));
  EXPECT_TRUE(DecodeFloat("iNF", &double_result));
  EXPECT_TRUE(::std::isinf(double_result));
  EXPECT_FALSE(::std::signbit(double_result));
  EXPECT_TRUE(DecodeFloat("-iNF", &double_result));
  EXPECT_TRUE(::std::isinf(double_result));
  EXPECT_TRUE(::std::signbit(double_result));
  EXPECT_TRUE(DecodeFloat("+iNF", &double_result));
  EXPECT_TRUE(::std::isinf(double_result));
  EXPECT_FALSE(::std::signbit(double_result));
}

// Helper functions for converting NaNs to bit patterns, so that the exact bit
// pattern result can be tested.
::std::uint64_t DoubleBitPattern(double n) {
  ::std::uint64_t result;
  memcpy(&result, &n, sizeof(result));
  return result;
}

::std::uint32_t FloatBitPattern(float n) {
  ::std::uint32_t result;
  memcpy(&result, &n, sizeof(result));
  return result;
}

TEST(DecodeFloat, Nans) {
  double double_result;
  EXPECT_TRUE(DecodeFloat("nan", &double_result));
  EXPECT_TRUE(::std::isnan(double_result));
  EXPECT_FALSE(::std::signbit(double_result));
  EXPECT_TRUE(DecodeFloat("-NAN", &double_result));
  EXPECT_TRUE(::std::isnan(double_result));
  EXPECT_TRUE(::std::signbit(double_result));
  EXPECT_TRUE(DecodeFloat("NaN(1)", &double_result));
  EXPECT_TRUE(::std::isnan(double_result));
  EXPECT_EQ(0x7ff0000000000001UL, DoubleBitPattern(double_result));
  EXPECT_TRUE(DecodeFloat("nAn(0x1000)", &double_result));
  EXPECT_TRUE(::std::isnan(double_result));
  EXPECT_EQ(0x7ff0000000001000UL, DoubleBitPattern(double_result));
  EXPECT_TRUE(DecodeFloat("NaN(0b11000011)", &double_result));
  EXPECT_TRUE(::std::isnan(double_result));
  EXPECT_EQ(0x7ff00000000000c3UL, DoubleBitPattern(double_result));
  EXPECT_TRUE(DecodeFloat("-NaN(0b11000011)", &double_result));
  EXPECT_TRUE(::std::isnan(double_result));
  EXPECT_EQ(0xfff00000000000c3UL, DoubleBitPattern(double_result));
  EXPECT_TRUE(DecodeFloat("+NaN(0b11000011)", &double_result));
  EXPECT_TRUE(::std::isnan(double_result));
  EXPECT_EQ(0x7ff00000000000c3UL, DoubleBitPattern(double_result));
  EXPECT_TRUE(DecodeFloat("NaN(0xf_ffff_ffff_ffff)", &double_result));
  EXPECT_TRUE(::std::isnan(double_result));
  EXPECT_EQ(0x7fffffffffffffffUL, DoubleBitPattern(double_result));
  EXPECT_TRUE(DecodeFloat("-NaN(0xf_ffff_ffff_ffff)", &double_result));
  EXPECT_TRUE(::std::isnan(double_result));
  EXPECT_EQ(0xffffffffffffffffUL, DoubleBitPattern(double_result));

  float float_result;
  EXPECT_TRUE(DecodeFloat("nan", &float_result));
  EXPECT_TRUE(::std::isnan(float_result));
  EXPECT_FALSE(::std::signbit(float_result));
  EXPECT_TRUE(DecodeFloat("-NAN", &float_result));
  EXPECT_TRUE(::std::isnan(float_result));
  EXPECT_TRUE(::std::signbit(float_result));
  EXPECT_TRUE(DecodeFloat("NaN(1)", &float_result));
  EXPECT_TRUE(::std::isnan(float_result));
  EXPECT_EQ(0x7f800001U, FloatBitPattern(float_result));
  EXPECT_TRUE(DecodeFloat("nAn(0x1000)", &float_result));
  EXPECT_TRUE(::std::isnan(float_result));
  EXPECT_EQ(0x7f801000U, FloatBitPattern(float_result));
  EXPECT_TRUE(DecodeFloat("NaN(0b11000011)", &float_result));
  EXPECT_TRUE(::std::isnan(float_result));
  EXPECT_EQ(0x7f8000c3U, FloatBitPattern(float_result));
  EXPECT_TRUE(DecodeFloat("-NaN(0b11000011)", &float_result));
  EXPECT_TRUE(::std::isnan(float_result));
  EXPECT_EQ(0xff8000c3U, FloatBitPattern(float_result));
  EXPECT_TRUE(DecodeFloat("+NaN(0b11000011)", &float_result));
  EXPECT_TRUE(::std::isnan(float_result));
  EXPECT_EQ(0x7f8000c3U, FloatBitPattern(float_result));
  EXPECT_TRUE(DecodeFloat("NaN(0x7f_ffff)", &float_result));
  EXPECT_TRUE(::std::isnan(float_result));
  EXPECT_EQ(0x7fffffffU, FloatBitPattern(float_result));
  EXPECT_TRUE(DecodeFloat("-NaN(0x7f_ffff)", &float_result));
  EXPECT_TRUE(::std::isnan(float_result));
  EXPECT_EQ(0xffffffffU, FloatBitPattern(float_result));
}

}  // namespace test
}  // namespace support
}  // namespace emboss
