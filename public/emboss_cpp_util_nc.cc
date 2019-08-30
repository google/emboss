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

#include <string>

#include "public/emboss_cpp_util.h"

namespace emboss {
namespace {

void X() {
#ifdef TEST_CANNOT_CONSTRUCT_READ_WRITE_CONTIGUOUS_BUFFER_FROM_STRING
  ::std::string foo = "::std::string";

  // Read-only ContiguousBuffer should be fine.
  (void)ContiguousBuffer<const char>(foo);

  // Read-write ContiguousBuffer should be fail.
  (void)ContiguousBuffer<char>(foo);
#endif  // TEST_CANNOT_CONSTRUCT_READ_WRITE_CONTIGUOUS_BUFFER_FROM_STRING

#ifdef TEST_CANNOT_CONSTRUCT_NON_BYTE_CONTIGUOUS_BUFFER
  // ContiguousBuffer<char>(nullptr) should be fine...
  (void)ContiguousBuffer<char>(nullptr);

  // ... but ContiguousBuffer<int>(nullptr) should not.
  (void)ContiguousBuffer<int>(nullptr);
#endif  // TEST_CANNOT_CONSTRUCT_NON_BYTE_CONTIGUOUS_BUFFER
}

}  // namespace
}  // namespace emboss
