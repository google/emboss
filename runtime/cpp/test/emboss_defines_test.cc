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

#include "runtime/cpp/emboss_defines.h"

#include <cstdint>

#include "gtest/gtest.h"

namespace emboss {
namespace support {
namespace test {

#if EMBOSS_CHECK_ABORTS
TEST(CheckPointerAlignment, Aligned) {
  ::std::uint32_t t;
  EMBOSS_CHECK_POINTER_ALIGNMENT(&t, sizeof t, 0);
  EMBOSS_CHECK_POINTER_ALIGNMENT(&t, 1, 0);
  EMBOSS_CHECK_POINTER_ALIGNMENT(reinterpret_cast<char *>(&t) + 1, sizeof t, 1);
  EMBOSS_CHECK_POINTER_ALIGNMENT(reinterpret_cast<char *>(&t) + 1, 1, 0);
}

TEST(CheckPointerAlignment, Misaligned) {
  ::std::uint32_t t;
  EXPECT_DEATH(EMBOSS_CHECK_POINTER_ALIGNMENT(&t, sizeof t, 1), "");
  EXPECT_DEATH(EMBOSS_CHECK_POINTER_ALIGNMENT(reinterpret_cast<char *>(&t) + 1,
                                              sizeof t, 0),
               "");
  (void)t;
}
#endif  // EMBOSS_CHECK_ABORTS

#if EMBOSS_SYSTEM_IS_TWOS_COMPLEMENT
TEST(SystemIsTwosComplement, CastToSigned) {
  EXPECT_EQ(-static_cast</**/ ::std::int64_t>(0x80000000),
            static_cast</**/ ::std::int32_t>(0x80000000));
}
#endif  // EMBOSS_SYSTEM_IS_TWOS_COMPLEMENT

// Note: I (bolms@) can't think of a way to truly test
// EMBOSS_ALIAS_SAFE_POINTER_CAST, since the compiler might let it work even if
// it's not "supposed" to.  (E.g., even with -fstrict-aliasing, GCC doesn't
// always take advantage of strict aliasing to do any optimizations.)

// The native <=> fixed endian macros are tested in emboss_bit_util_test.cc,
// since their expansions rely on emboss_bit_util.h.

}  // namespace test
}  // namespace support
}  // namespace emboss
