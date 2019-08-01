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

#include <stdint.h>

#include "testdata/auto_array_size.emb.h"

namespace emboss {
namespace test {
namespace {

void X() {
  static const uint8_t kAutoSize[36] = {0};
  (void)kAutoSize;  // Suppress unused variable warning.

#ifdef TEST_WRITER_IS_NOT_CONSTRUCTIBLE_FROM_CONSTANT
  // A FooWriter should not be constructible from a constant pointer.
  AutoSizeView view = AutoSizeWriter(kAutoSize, sizeof kAutoSize);
#endif  // TEST_WRITER_IS_NOT_CONSTRUCTIBLE_FROM_CONSTANT

#ifdef TEST_CANNOT_CALL_SET_ON_CONSTANT_VIEW
  // A call to FooView::xxx().Write() should not compile.
  AutoSizeView view = AutoSizeView(kAutoSize, sizeof kAutoSize);
  // .Read() should be OK.
  (void)view.array_size().Read();
  view.array_size().Write(1);
#endif  // TEST_CANNOT_CALL_SET_ON_CONSTANT_VIEW

#ifdef TEST_CANNOT_CALL_SET_ON_CONSTANT_VIEW_OF_ARRAY
  // A call to FooView::xxx()[y].Write() should not compile.
  AutoSizeView view = AutoSizeView(kAutoSize, sizeof kAutoSize);
  // .Read() should be OK.
  (void)view.four_byte_array()[1].Read();
  view.four_byte_array()[1].Write(0);
#endif  // TEST_CANNOT_CALL_SET_ON_CONSTANT_VIEW_OF_ARRAY
}

}  // namespace
}  // namespace test
}  // namespace emboss
