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

#include "runtime/cpp/emboss_constant_view.h"

#include "gtest/gtest.h"

namespace emboss {
namespace support {
namespace test {

TEST(MaybeConstantViewTest, Read) {
  EXPECT_EQ(7, MaybeConstantView</**/ ::std::uint8_t>(7).Read());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(MaybeConstantView</**/ ::std::uint8_t>().Read(), "Known\\(\\)");
#endif  // EMBOSS_CHECK_ABORTS
}

TEST(MaybeConstantViewTest, UncheckedRead) {
  EXPECT_EQ(7, MaybeConstantView</**/ ::std::uint8_t>(7).UncheckedRead());
  EXPECT_EQ(0, MaybeConstantView</**/ ::std::uint8_t>().UncheckedRead());
}

TEST(MaybeConstantViewTest, Ok) {
  EXPECT_TRUE(MaybeConstantView</**/ ::std::uint8_t>(7).Ok());
  EXPECT_FALSE(MaybeConstantView</**/ ::std::uint8_t>().Ok());
}

TEST(MaybeConstantViewTest, CopyConstruction) {
  auto with_value = MaybeConstantView</**/ ::std::uint8_t>(7);
  auto copied_with_value = with_value;
  EXPECT_EQ(7, copied_with_value.Read());

  auto without_value = MaybeConstantView</**/ ::std::uint8_t>();
  auto copied_without_value = without_value;
  EXPECT_FALSE(copied_without_value.Ok());
}

TEST(MaybeConstantViewTest, Assignment) {
  auto with_value = MaybeConstantView</**/ ::std::uint8_t>(7);
  MaybeConstantView</**/ ::std::uint8_t> copied_with_value;
  copied_with_value = with_value;
  EXPECT_EQ(7, copied_with_value.Read());

  auto without_value = MaybeConstantView</**/ ::std::uint8_t>();
  MaybeConstantView</**/ ::std::uint8_t> copied_without_value;
  copied_without_value = without_value;
  EXPECT_FALSE(copied_without_value.Ok());
}

}  // namespace test
}  // namespace support
}  // namespace emboss
