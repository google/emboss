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

// Tests for using types that are imported from imports.

#include <stdint.h>

#include <vector>

#include "gtest/gtest.h"
#include "testdata/importer2.emb.h"

namespace emboss {
namespace test {
namespace {

const ::std::uint8_t kOuter2[16] = {
    0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,  // inner
    0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10,  // inner_gen
};

TEST(Importer, CanAccessInner) {
  auto view = Outer2View(kOuter2, sizeof kOuter2);
  EXPECT_EQ(0x0807060504030201UL, view.outer().inner().value().Read());
  EXPECT_EQ(0x100f0e0d0c0b0a09UL, view.outer().inner_gen().value().Read());
}

}  // namespace
}  // namespace test
}  // namespace emboss
