// Copyright 2024 Google LLC
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

// Tests that an emb compiled with enable_enum_traits = False actually compiles.

#include <stdint.h>

#include <vector>

#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "testdata/no_enum_traits.emb.h"

namespace emboss {
namespace test {
namespace {

TEST(NoEnumTraits, Compiles) {
  ::std::vector<uint8_t> backing_store(1);
  auto view = MakeBarView(&backing_store);
  view.foo().Write(Foo::VALUE);
  EXPECT_TRUE(view.Ok());

  // Check that we don't accidentally include `emboss_text_util.h` via our
  // generated header.
#ifdef EMBOSS_RUNTIME_CPP_EMBOSS_TEXT_UTIL_H_
  const bool emboss_text_util_is_present = true;
#else
  const bool emboss_text_util_is_present = false;
#endif

  EXPECT_FALSE(emboss_text_util_is_present);
}

}  // namespace
}  // namespace test
}  // namespace emboss
