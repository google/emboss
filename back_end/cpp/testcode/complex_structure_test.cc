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
#include "testdata/complex_structure.emb.h"

namespace emboss_test {
namespace {

TEST(InvalidTextInput, PrematureEnd) {
  ::std::array<char, 64> values = {0};
  const auto view = ::emboss_test::MakeComplexView(&values);
  ::emboss::UpdateFromText(view, "{a:");
}

TEST(InvalidTextInput, ReallyPrematureEnd) {
  ::std::array<char, 64> values = {0};
  const auto view = ::emboss_test::MakeComplexView(&values);
  ::emboss::UpdateFromText(view, "\x01");
}

TEST(InvalidTextInput, WeirdInputDoesNotHang) {
  ::std::string text{0x7b, 0x78, 0x32, 0x3a, 0x30, 0x0d, 0x0d, 0x62, 0x32,
                     0x7f, 0x30, 0x0d, 0x0d, 0x62, 0x32, 0x3a, 0x30, 0x0d,
                     0x0d, 0x62, 0x32, 0x3a, 0x30, 0x0d, 0x0c, 0x30, 0x0d,
                     0x0d, 0x63, 0x32, 0x3a, 0x30, 0x0d, 0x0d, 0x62, 0x36,
                     0x3a, 0x30, 0x0d, 0x32, 0x3a, 0x30, 0x0d};
  ::std::array<char, 64> values = {0};
  const auto view = ::emboss_test::MakeComplexView(&values);
  ::emboss::UpdateFromText(view, text);
}

}  // namespace
}  // namespace emboss_test
