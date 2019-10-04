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

// Test for the generated View class for StartSize from start_size_range.emb.

#include <stdint.h>

#include "gtest/gtest.h"
#include "testdata/start_size_range.emb.h"

namespace emboss {
namespace test {
namespace {

static const ::std::uint8_t kStartSizeRange[9] = {
    0x02,                    // 0:1   0:1       size == 4
    0xe8, 0x03,              // 1:3   1   [+2]  start_size_constants == 1000
    0x11, 0x22,              // 3:5   3   [+s]  payload
    0x21, 0x43, 0x65, 0x87,  // 5:9   3+s [+4]  counter == 0x87654321
};

TEST(StartSizeView, EverythingInPlace) {
  auto view = StartSizeView(kStartSizeRange, sizeof kStartSizeRange);
  EXPECT_EQ(9U, view.SizeInBytes());
  EXPECT_EQ(2, view.size().Read());
  EXPECT_EQ(1000, view.start_size_constants().Read());
  EXPECT_EQ(0x11, view.payload()[0].Read());
  EXPECT_EQ(0x22, view.payload()[1].Read());
  EXPECT_EQ(0x87654321, view.counter().Read());
}

}  // namespace
}  // namespace test
}  // namespace emboss
