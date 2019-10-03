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

// Tests for generated code for anonymous "bits" types, using
// anonymous_bits.emb.
#include <stdint.h>

#include <vector>

#include "gtest/gtest.h"
#include "runtime/cpp/emboss_cpp_util.h"
#include "testdata/anonymous_bits.emb.h"

namespace emboss {
namespace test {
namespace bits {
namespace {

TEST(AnonymousBits, InnerEnumIsVisibleAtOuterScope) {
  EXPECT_EQ(static_cast<Foo::Bar>(0), Foo::Bar::BAR);
}

TEST(AnonymousBits, BitsAreReadable) {
  alignas(8)::std::uint8_t data[] = {0x01, 0x00, 0x00, 0x80,
                                     0x01, 0x00, 0x80, 0x00};
  EXPECT_FALSE((FooWriter{data, sizeof data - 1}.Ok()));

  auto foo = MakeAlignedFooView</**/ ::std::uint8_t, 8>(data, sizeof data);
  ASSERT_TRUE(foo.Ok());
  EXPECT_TRUE(foo.high_bit().Read());
  EXPECT_TRUE(foo.first_bit().Read());
  EXPECT_TRUE(foo.bit_23().Read());
  EXPECT_TRUE(foo.low_bit().Read());
  foo.first_bit().Write(false);
  EXPECT_EQ(0, data[0]);
  foo.bit_23().Write(false);
  EXPECT_EQ(0, data[6]);
}

TEST(AnonymousBits, Equals) {
  alignas(8)::std::uint8_t buf_x[] = {0x01, 0x00, 0x00, 0x80,
                                      0x01, 0x00, 0x80, 0x00};
  alignas(8)::std::uint8_t buf_y[] = {0x01, 0x00, 0x00, 0x80,
                                      0x01, 0x00, 0x80, 0x00};

  auto x = MakeAlignedFooView</**/ ::std::uint8_t, 8>(buf_x, sizeof buf_x);
  auto x_const =
      MakeFooView(static_cast<const ::std::uint8_t *>(buf_x), sizeof buf_x);
  auto y = MakeAlignedFooView</**/ ::std::uint8_t, 8>(buf_y, sizeof buf_y);

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

  // Changing the second byte of buf_y should have no effect on equality.
  ++buf_y[1];
  EXPECT_NE(buf_x, buf_y);
  EXPECT_TRUE(x.Equals(y));
  EXPECT_TRUE(x.UncheckedEquals(y));
  EXPECT_TRUE(y.Equals(x));
  EXPECT_TRUE(y.UncheckedEquals(x));

  ++buf_y[0];
  EXPECT_FALSE(x.Equals(y));
  EXPECT_FALSE(x.UncheckedEquals(y));
  EXPECT_FALSE(y.Equals(x));
  EXPECT_FALSE(y.UncheckedEquals(x));
}

TEST(AnonymousBits, WriteToString) {
  const ::std::uint8_t data[] = {0x01, 0x00, 0x00, 0x80,
                                 0x01, 0x00, 0x80, 0x00};
  auto foo = MakeFooView(data, sizeof data);
  ASSERT_TRUE(foo.Ok());
  EXPECT_EQ(
      "{ high_bit: true, bar: BAR, first_bit: true, bit_23: true, low_bit: "
      "true }",
      ::emboss::WriteToString(foo));
}

TEST(AnonymousBits, ReadFromString) {
  const ::std::uint8_t data[] = {0x01, 0x00, 0x00, 0x80,
                                 0x01, 0x00, 0x80, 0x00};
  ::std::uint8_t data2[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
  auto foo = MakeFooView(data, sizeof data);
  auto foo_writer = MakeFooView(data2, sizeof data2);
  ASSERT_TRUE(foo.Ok());
  ASSERT_TRUE(foo_writer.Ok());
  ::emboss::UpdateFromText(foo_writer, ::emboss::WriteToString(foo));
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(data, data + sizeof data),
            ::std::vector</**/ ::std::uint8_t>(data2, data2 + sizeof data2));
}

}  // namespace
}  // namespace bits
}  // namespace test
}  // namespace emboss
