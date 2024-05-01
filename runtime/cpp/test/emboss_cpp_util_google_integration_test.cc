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

#include "absl/strings/string_view.h"
#include "gtest/gtest.h"
#include "runtime/cpp/emboss_cpp_util.h"
#include "runtime/cpp/emboss_text_util.h"

namespace emboss {
namespace support {
namespace test {

TEST(TextStream, Construction) {
  absl::string_view view_text = "gh";
  auto text_stream = TextStream(view_text);
  char result;
  EXPECT_TRUE(text_stream.Read(&result));
  EXPECT_EQ('g', result);
  EXPECT_TRUE(text_stream.Read(&result));
  EXPECT_EQ('h', result);
  EXPECT_FALSE(text_stream.Read(&result));
}

}  // namespace test
}  // namespace support
}  // namespace emboss
