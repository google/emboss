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

// Tests for Emboss floating-point support.

#include <stdint.h>

#include <cmath>
#include <vector>

#include "gtest/gtest.h"
#include "testdata/float.emb.h"

namespace emboss {
namespace test {
namespace {

::std::array<char, 8> MakeFloats(::std::uint32_t bits) {
  return ::std::array<char, 8>({{
      // Little endian version
      static_cast<char>(bits & 0xff),          //
      static_cast<char>((bits >> 8) & 0xff),   //
      static_cast<char>((bits >> 16) & 0xff),  //
      static_cast<char>((bits >> 24) & 0xff),  //

      // Big endian version
      static_cast<char>((bits >> 24) & 0xff),  //
      static_cast<char>((bits >> 16) & 0xff),  //
      static_cast<char>((bits >> 8) & 0xff),   //
      static_cast<char>(bits & 0xff),          //
  }});
}

::std::array<char, 16> MakeDoubles(::std::uint64_t bits) {
  return ::std::array<char, 16>({{
      // Little endian version
      static_cast<char>(bits & 0xff),          //
      static_cast<char>((bits >> 8) & 0xff),   //
      static_cast<char>((bits >> 16) & 0xff),  //
      static_cast<char>((bits >> 24) & 0xff),  //
      static_cast<char>((bits >> 32) & 0xff),  //
      static_cast<char>((bits >> 40) & 0xff),  //
      static_cast<char>((bits >> 48) & 0xff),  //
      static_cast<char>((bits >> 56) & 0xff),  //

      // Big endian version
      static_cast<char>((bits >> 56) & 0xff),  //
      static_cast<char>((bits >> 48) & 0xff),  //
      static_cast<char>((bits >> 40) & 0xff),  //
      static_cast<char>((bits >> 32) & 0xff),  //
      static_cast<char>((bits >> 24) & 0xff),  //
      static_cast<char>((bits >> 16) & 0xff),  //
      static_cast<char>((bits >> 8) & 0xff),   //
      static_cast<char>(bits & 0xff),          //
  }});
}

// This is used separately for tests where !(a == a).
void TestFloatWrite(float value, ::std::uint32_t bits) {
  const auto floats = MakeFloats(bits);

  ::std::array<char, 8> buffer = {};
  auto writer = MakeFloatsView(&buffer);
  EXPECT_TRUE(writer.float_little_endian().CouldWriteValue(value));
  EXPECT_TRUE(writer.float_big_endian().CouldWriteValue(value));
  writer.float_little_endian().Write(value);
  writer.float_big_endian().Write(value);
  EXPECT_EQ(floats, buffer);
}

::std::array<char, 8> TestFloatValue(float value, ::std::uint32_t bits) {
  const auto floats = MakeFloats(bits);

  auto view = MakeFloatsView(&floats);
  EXPECT_EQ(value, view.float_little_endian().Read());
  EXPECT_EQ(value, view.float_big_endian().Read());

  TestFloatWrite(value, bits);

  return floats;
}

// This is used separately for tests where !(a == a).
void TestDoubleWrite(double value, ::std::uint64_t bits) {
  const auto doubles = MakeDoubles(bits);

  ::std::array<char, 16> buffer = {};
  auto writer = MakeDoublesView(&buffer);
  EXPECT_TRUE(writer.double_little_endian().CouldWriteValue(value));
  EXPECT_TRUE(writer.double_big_endian().CouldWriteValue(value));
  writer.double_little_endian().Write(value);
  writer.double_big_endian().Write(value);
  EXPECT_EQ(doubles, buffer);
}

::std::array<char, 16> TestDoubleValue(double value, ::std::uint64_t bits) {
  const auto doubles = MakeDoubles(bits);

  auto view = MakeDoublesView(&doubles);
  EXPECT_EQ(value, view.double_little_endian().Read());
  EXPECT_EQ(value, view.double_big_endian().Read());

  TestDoubleWrite(value, bits);

  return doubles;
}

TEST(Floats, One) { TestFloatValue(+1.0f, 0x3f800000); }
TEST(Floats, Fraction) { TestFloatValue(-0.375f, 0xbec00000); }
TEST(Floats, MinimumDenorm) {
  TestFloatValue(::std::exp2(-149.0f), 0x00000001);
}

TEST(Floats, PlusZero) {
  auto floats = TestFloatValue(+0.0f, 0x00000000);
  auto view = MakeFloatsView(&floats);
  EXPECT_FALSE(::std::signbit(view.float_little_endian().Read()));
  EXPECT_FALSE(::std::signbit(view.float_big_endian().Read()));
}

TEST(Floats, MinusZero) {
  auto floats = TestFloatValue(-0.0f, 0x80000000);
  auto view = MakeFloatsView(&floats);
  EXPECT_TRUE(::std::signbit(view.float_little_endian().Read()));
  EXPECT_TRUE(::std::signbit(view.float_big_endian().Read()));
}

TEST(Floats, PlusInfinity) {
  auto floats = MakeFloats(0x7f800000);
  auto view = MakeFloatsView(&floats);
  EXPECT_TRUE(::std::isinf(view.float_little_endian().Read()));
  EXPECT_TRUE(::std::isinf(view.float_big_endian().Read()));
  EXPECT_FALSE(::std::signbit(view.float_little_endian().Read()));
  EXPECT_FALSE(::std::signbit(view.float_big_endian().Read()));
  TestFloatWrite(view.float_little_endian().Read(), 0x7f800000);
}

TEST(Floats, MinusInfinity) {
  auto floats = MakeFloats(0xff800000);
  auto view = MakeFloatsView(&floats);
  EXPECT_TRUE(::std::isinf(view.float_little_endian().Read()));
  EXPECT_TRUE(::std::isinf(view.float_big_endian().Read()));
  EXPECT_TRUE(::std::signbit(view.float_little_endian().Read()));
  EXPECT_TRUE(::std::signbit(view.float_big_endian().Read()));
  TestFloatWrite(view.float_little_endian().Read(), 0xff800000);
}

TEST(Floats, Nan) {
  // TODO(bolms): IEEE 754 does not specify the difference between quiet and
  // signalling NaN, and there are two completely incompatible definitions in
  // use by modern processors.  Ideally, Emboss should provide some way to
  // specify which convention is in use, but in practice it probably doesn't
  // matter when dealing with hardware devices.
  //
  // Note that the above bit patterns are signalling NaNs on some processors,
  // and thus any operation on them other than 'std::isnan' should be avoided.

  auto floats = MakeFloats(0x7f800001);
  auto view = MakeFloatsView(&floats);
  EXPECT_TRUE(::std::isnan(view.float_little_endian().Read()));
  EXPECT_TRUE(::std::isnan(view.float_big_endian().Read()));
  TestFloatWrite(view.float_little_endian().Read(), 0x7f800001);
}

TEST(FloatView, Equals) {
  auto buf_x = MakeFloats(64);
  auto buf_y = MakeFloats(64);
  EXPECT_EQ(buf_x, buf_y);

  auto x = MakeFloatsView(&buf_x);
  auto x_const =
      MakeFloatsView(static_cast</**/ ::std::array<char, 8>*>(&buf_x));
  auto y = MakeFloatsView(&buf_y);

  EXPECT_TRUE(x.Equals(x));
  EXPECT_TRUE(x.UncheckedEquals(x));
  EXPECT_TRUE(y.Equals(y));
  EXPECT_TRUE(y.UncheckedEquals(y));

  EXPECT_TRUE(x.Equals(y));
  EXPECT_TRUE(x.UncheckedEquals(y));
  EXPECT_TRUE(y.Equals(x));
  EXPECT_TRUE(y.UncheckedEquals(x));

  EXPECT_TRUE(x_const.Equals(y));
  EXPECT_TRUE(x_const.UncheckedEquals(y));
  EXPECT_TRUE(y.Equals(x_const));
  EXPECT_TRUE(y.UncheckedEquals(x_const));

  ++buf_y[1];
  EXPECT_FALSE(x.Equals(y));
  EXPECT_FALSE(x.UncheckedEquals(y));
  EXPECT_FALSE(y.Equals(x));
  EXPECT_FALSE(y.UncheckedEquals(x));
}

TEST(FloatView, EqualsNaN) {
  auto buf_x = MakeFloats(0x7f800001);
  auto buf_y = MakeFloats(0x7f800001);
  EXPECT_EQ(buf_x, buf_y);

  auto x = MakeFloatsView(&buf_x);
  auto y = MakeFloatsView(&buf_y);

  EXPECT_TRUE(::std::isnan(x.float_little_endian().Read()));
  EXPECT_TRUE(::std::isnan(x.float_big_endian().Read()));
  EXPECT_TRUE(::std::isnan(y.float_little_endian().Read()));
  EXPECT_TRUE(::std::isnan(y.float_big_endian().Read()));

  EXPECT_FALSE(x.Equals(x));
  EXPECT_FALSE(y.Equals(y));
  EXPECT_FALSE(x.Equals(y));
  EXPECT_FALSE(y.Equals(x));
}

TEST(Doubles, One) { TestDoubleValue(+1.0, 0x3ff0000000000000UL); }
TEST(Doubles, Fraction) { TestDoubleValue(-0.375, 0xbfd8000000000000UL); }
TEST(Doubles, MinimumDenorm) {
  TestDoubleValue(::std::exp2(-1074.0), 0x0000000000000001UL);
}

TEST(Doubles, PlusZero) {
  auto doubles = TestDoubleValue(+0.0, 0x0000000000000000UL);
  auto view = MakeDoublesView(&doubles);
  EXPECT_FALSE(::std::signbit(view.double_little_endian().Read()));
  EXPECT_FALSE(::std::signbit(view.double_big_endian().Read()));
}

TEST(Doubles, MinusZero) {
  auto doubles = TestDoubleValue(-0.0, 0x8000000000000000UL);
  auto view = MakeDoublesView(&doubles);
  EXPECT_TRUE(::std::signbit(view.double_little_endian().Read()));
  EXPECT_TRUE(::std::signbit(view.double_big_endian().Read()));
}

TEST(Doubles, PlusInfinity) {
  auto doubles = MakeDoubles(0x7ff0000000000000UL);
  auto view = MakeDoublesView(&doubles);
  EXPECT_TRUE(::std::isinf(view.double_little_endian().Read()));
  EXPECT_TRUE(::std::isinf(view.double_big_endian().Read()));
  EXPECT_FALSE(::std::signbit(view.double_little_endian().Read()));
  EXPECT_FALSE(::std::signbit(view.double_big_endian().Read()));
  TestDoubleWrite(view.double_little_endian().Read(), 0x7ff0000000000000UL);
}

TEST(Doubles, MinusInfinity) {
  auto doubles = MakeDoubles(0xfff0000000000000UL);
  auto view = MakeDoublesView(&doubles);
  EXPECT_TRUE(::std::isinf(view.double_little_endian().Read()));
  EXPECT_TRUE(::std::isinf(view.double_big_endian().Read()));
  EXPECT_TRUE(::std::signbit(view.double_little_endian().Read()));
  EXPECT_TRUE(::std::signbit(view.double_big_endian().Read()));
  TestDoubleWrite(view.double_little_endian().Read(), 0xfff0000000000000UL);
}

TEST(Doubles, Nan) {
  auto doubles = MakeDoubles(0x7ff0000000000001UL);
  auto view = MakeDoublesView(&doubles);
  EXPECT_TRUE(::std::isnan(view.double_little_endian().Read()));
  EXPECT_TRUE(::std::isnan(view.double_big_endian().Read()));
  TestDoubleWrite(view.double_little_endian().Read(), 0x7ff0000000000001UL);
}

TEST(Doubles, CopyFrom) {
  auto doubles_x = MakeDoubles(0x7ff0000000000001UL);
  auto doubles_y = MakeDoubles(0x0000000000000000UL);

  auto x = MakeDoublesView(&doubles_x);
  auto y = MakeDoublesView(&doubles_y);

  EXPECT_NE(x.double_little_endian().Read(), y.double_little_endian().Read());
  EXPECT_NE(x.double_big_endian().Read(), y.double_big_endian().Read());
  x.double_little_endian().CopyFrom(y.double_little_endian());
  x.double_big_endian().CopyFrom(y.double_big_endian());
  EXPECT_EQ(x.double_little_endian().Read(), y.double_little_endian().Read());
  EXPECT_EQ(x.double_big_endian().Read(), y.double_big_endian().Read());
}

TEST(Doubles, TryToCopyFrom) {
  auto doubles_x = MakeDoubles(0x7ff0000000000001UL);
  auto doubles_y = MakeDoubles(0x0000000000000000UL);

  auto x = MakeDoublesView(&doubles_x);
  auto y = MakeDoublesView(&doubles_y);

  EXPECT_NE(x.double_little_endian().Read(), y.double_little_endian().Read());
  EXPECT_NE(x.double_big_endian().Read(), y.double_big_endian().Read());
  EXPECT_TRUE(x.double_little_endian().TryToCopyFrom(y.double_little_endian()));
  EXPECT_TRUE(x.double_big_endian().TryToCopyFrom(y.double_big_endian()));
  EXPECT_EQ(x.double_little_endian().Read(), y.double_little_endian().Read());
  EXPECT_EQ(x.double_big_endian().Read(), y.double_big_endian().Read());
}

TEST(DoubleView, Equals) {
  auto buf_x = MakeDoubles(64);
  auto buf_y = MakeDoubles(64);
  EXPECT_EQ(buf_x, buf_y);

  auto x = MakeDoublesView(&buf_x);
  auto y = MakeDoublesView(&buf_y);

  EXPECT_TRUE(x.Equals(x));
  EXPECT_TRUE(y.Equals(y));

  EXPECT_TRUE(x.Equals(y));
  EXPECT_TRUE(y.Equals(x));

  ++buf_y[1];
  EXPECT_FALSE(x.Equals(y));
  EXPECT_FALSE(y.Equals(x));
}

TEST(DoubleView, EqualsNaN) {
  auto buf_x = MakeDoubles(0x7ff0000000000001UL);
  auto buf_y = MakeDoubles(0x7ff0000000000001UL);
  EXPECT_EQ(buf_x, buf_y);

  auto x = MakeDoublesView(&buf_x);
  auto y = MakeDoublesView(&buf_y);

  EXPECT_TRUE(::std::isnan(x.double_little_endian().Read()));
  EXPECT_TRUE(::std::isnan(x.double_big_endian().Read()));
  EXPECT_TRUE(::std::isnan(y.double_little_endian().Read()));
  EXPECT_TRUE(::std::isnan(y.double_big_endian().Read()));

  EXPECT_FALSE(x.Equals(x));
  EXPECT_FALSE(y.Equals(y));

  EXPECT_FALSE(x.Equals(y));
  EXPECT_FALSE(y.Equals(x));
}

TEST(DoubleView, WriteTextFormat) {
  auto buf_x = MakeDoubles(0x4050000000000000UL);
  auto x = MakeDoublesView(&buf_x);
  EXPECT_EQ("{ double_little_endian: 64, double_big_endian: 64 }",
            ::emboss::WriteToString(x));
  EXPECT_EQ(
      "{\n"
      "  double_little_endian: 64\n"
      "  double_big_endian: 64\n"
      "}",
      ::emboss::WriteToString(x, ::emboss::MultilineText()));
}

TEST(DoubleView, ReadTextFormat) {
  auto buf_x = MakeDoubles(0UL);
  auto x = MakeDoublesView(&buf_x);
  EXPECT_TRUE(::emboss::UpdateFromText(x,
                                       "{\n"
                                       "  double_little_endian: 64\n"
                                       "  double_big_endian: 64\n"
                                       "}"));
  EXPECT_EQ(64, x.double_little_endian().Read());
  EXPECT_EQ(64, x.double_big_endian().Read());
}

}  // namespace
}  // namespace test
}  // namespace emboss
