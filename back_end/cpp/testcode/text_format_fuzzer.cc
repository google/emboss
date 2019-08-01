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

// Fuzz test for reading Emboss text format of the `Complex` struct in
// `complex_structure.emb`.
//
// This fuzz target verifies that ::emboss::UpdateFromText does not crash on any
// input.  It does not verify that UpdateFromText does the right thing.

#include "testdata/complex_structure.emb.h"

// Entry point for fuzz tester: this must have this exact signature, including
// the name `LLVMFuzzerTestOneInput`, or it will not work.
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  ::std::array<char, 64> values = {0};
  const auto view = ::emboss_test::MakeComplexView(&values);
  ::emboss::UpdateFromText(
      view, ::std::string(reinterpret_cast<const char *>(data), size));
  return 0;
}
