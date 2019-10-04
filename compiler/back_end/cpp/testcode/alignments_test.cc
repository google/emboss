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

// Tests that generated code properly preserves and propagates alignment
// information.
#include <stdint.h>

#include <vector>

#include "gtest/gtest.h"
#include "runtime/cpp/emboss_cpp_util.h"
#include "testdata/alignments.emb.h"

namespace emboss {
namespace test {
namespace {

using ::emboss::support::ContiguousBuffer;

TEST(AlignmentsTest, DirectFieldAlignments) {
  auto unaligned_view = MakeAlignmentsView<char>(nullptr, 0);
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.zero_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.four_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.twelve_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.three_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.eleven_offset())>::value));

  auto four_aligned_view = MakeAlignedAlignmentsView<char, 4>(nullptr, 0);
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 4, 0>>,
                      decltype(four_aligned_view.zero_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 4, 0>>,
                      decltype(four_aligned_view.four_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 4, 0>>,
                      decltype(four_aligned_view.twelve_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 4, 3>>,
                      decltype(four_aligned_view.three_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 4, 3>>,
                      decltype(four_aligned_view.eleven_offset())>::value));

  auto eight_aligned_view = MakeAlignedAlignmentsView<char, 8>(nullptr, 0);
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 8, 0>>,
                      decltype(eight_aligned_view.zero_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 8, 4>>,
                      decltype(eight_aligned_view.four_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 8, 4>>,
                      decltype(eight_aligned_view.twelve_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 8, 3>>,
                      decltype(eight_aligned_view.three_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 8, 3>>,
                      decltype(eight_aligned_view.eleven_offset())>::value));
}

TEST(AlignmentsTest, AlignmentReductionAssignment) {
  alignas(4) unsigned char data[4];
  auto four_aligned_view = MakeAlignedAlignmentsView<unsigned char, 4>(data, 4);
  {
    // Implicit construction.
    AlignmentsView unaligned_view{four_aligned_view};
    EXPECT_EQ(data, unaligned_view.BackingStorage().data());
  }
  {
    // Implicit conversion during assignment.
    AlignmentsView unaligned_view;
    unaligned_view = four_aligned_view;
    EXPECT_EQ(data, unaligned_view.BackingStorage().data());
  }
}

TEST(AlignmentsTest, ArrayFieldAlignments) {
  auto unaligned_view = MakeAlignmentsView<char>(nullptr, 0);
  EXPECT_TRUE(
      (::std::is_same<
          GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
          decltype(unaligned_view.zero_offset_four_stride_array()[0])>::value));
  EXPECT_TRUE(
      (::std::is_same<
          GenericPlaceholder6View<ContiguousBuffer<char, 1, 0>>,
          decltype(unaligned_view.zero_offset_six_stride_array()[0])>::value));
  EXPECT_TRUE(
      (::std::is_same<
          GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
          decltype(
              unaligned_view.three_offset_four_stride_array()[0])>::value));
  EXPECT_TRUE(
      (::std::is_same<
          GenericPlaceholder6View<ContiguousBuffer<char, 1, 0>>,
          decltype(unaligned_view.four_offset_six_stride_array()[0])>::value));

  auto four_aligned_view = MakeAlignedAlignmentsView<char, 4>(nullptr, 0);
  EXPECT_TRUE(
      (::std::is_same<
          GenericPlaceholder4View<ContiguousBuffer<char, 4, 0>>,
          decltype(
              four_aligned_view.zero_offset_four_stride_array()[0])>::value));
  EXPECT_TRUE((
      ::std::is_same<GenericPlaceholder6View<ContiguousBuffer<char, 2, 0>>,
                     decltype(four_aligned_view
                                  .zero_offset_six_stride_array()[0])>::value));
  EXPECT_TRUE(
      (::std::is_same<
          GenericPlaceholder4View<ContiguousBuffer<char, 4, 3>>,
          decltype(
              four_aligned_view.three_offset_four_stride_array()[0])>::value));
  EXPECT_TRUE((
      ::std::is_same<GenericPlaceholder6View<ContiguousBuffer<char, 2, 0>>,
                     decltype(four_aligned_view
                                  .four_offset_six_stride_array()[0])>::value));

  auto eight_aligned_view = MakeAlignedAlignmentsView<char, 8>(nullptr, 0);
  EXPECT_TRUE(
      (::std::is_same<
          GenericPlaceholder4View<ContiguousBuffer<char, 4, 0>>,
          decltype(
              eight_aligned_view.zero_offset_four_stride_array()[0])>::value));
  EXPECT_TRUE((
      ::std::is_same<GenericPlaceholder6View<ContiguousBuffer<char, 2, 0>>,
                     decltype(eight_aligned_view
                                  .zero_offset_six_stride_array()[0])>::value));
  EXPECT_TRUE(
      (::std::is_same<
          GenericPlaceholder4View<ContiguousBuffer<char, 4, 3>>,
          decltype(
              eight_aligned_view.three_offset_four_stride_array()[0])>::value));
  EXPECT_TRUE((
      ::std::is_same<GenericPlaceholder6View<ContiguousBuffer<char, 2, 0>>,
                     decltype(eight_aligned_view
                                  .four_offset_six_stride_array()[0])>::value));
}

TEST(AlignmentsTest, SubFieldAlignments) {
  auto unaligned_view = MakeAlignmentsView<char>(nullptr, 0);
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.zero_offset_substructure()
                                   .zero_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.zero_offset_substructure()
                                   .two_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.two_offset_substructure()
                                   .zero_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.two_offset_substructure()
                                   .two_offset())>::value));

  auto four_aligned_view = MakeAlignedAlignmentsView<char, 4>(nullptr, 0);
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 4, 0>>,
                      decltype(four_aligned_view.zero_offset_substructure()
                                   .zero_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 4, 2>>,
                      decltype(four_aligned_view.zero_offset_substructure()
                                   .two_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 4, 2>>,
                      decltype(four_aligned_view.two_offset_substructure()
                                   .zero_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 4, 0>>,
                      decltype(four_aligned_view.two_offset_substructure()
                                   .two_offset())>::value));

  auto eight_aligned_view = MakeAlignedAlignmentsView<char, 8>(nullptr, 0);
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 8, 0>>,
                      decltype(eight_aligned_view.zero_offset_substructure()
                                   .zero_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 8, 2>>,
                      decltype(eight_aligned_view.zero_offset_substructure()
                                   .two_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 8, 2>>,
                      decltype(eight_aligned_view.two_offset_substructure()
                                   .zero_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 8, 4>>,
                      decltype(eight_aligned_view.two_offset_substructure()
                                   .two_offset())>::value));
}

TEST(AlignmentsTest, ArraySubFieldAlignments) {
  auto unaligned_view = MakeAlignmentsView<char>(nullptr, 0);
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.zero_offset_six_stride_array()[0]
                                   .zero_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.zero_offset_six_stride_array()[0]
                                   .two_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.four_offset_six_stride_array()[0]
                                   .zero_offset())>::value));
  EXPECT_TRUE(
      (::std::is_same<GenericPlaceholder4View<ContiguousBuffer<char, 1, 0>>,
                      decltype(unaligned_view.four_offset_six_stride_array()[0]
                                   .two_offset())>::value));

  auto four_aligned_view = MakeAlignedAlignmentsView<char, 4>(nullptr, 0);
  EXPECT_TRUE((::std::is_same<
               GenericPlaceholder4View<ContiguousBuffer<char, 2, 0>>,
               decltype(four_aligned_view.zero_offset_six_stride_array()[0]
                            .zero_offset())>::value));
  EXPECT_TRUE((::std::is_same<
               GenericPlaceholder4View<ContiguousBuffer<char, 2, 0>>,
               decltype(four_aligned_view.zero_offset_six_stride_array()[0]
                            .two_offset())>::value));
  EXPECT_TRUE((::std::is_same<
               GenericPlaceholder4View<ContiguousBuffer<char, 2, 0>>,
               decltype(four_aligned_view.four_offset_six_stride_array()[0]
                            .zero_offset())>::value));
  EXPECT_TRUE((::std::is_same<
               GenericPlaceholder4View<ContiguousBuffer<char, 2, 0>>,
               decltype(four_aligned_view.four_offset_six_stride_array()[0]
                            .two_offset())>::value));

  auto eight_aligned_view = MakeAlignedAlignmentsView<char, 8>(nullptr, 0);
  EXPECT_TRUE((::std::is_same<
               GenericPlaceholder4View<ContiguousBuffer<char, 2, 0>>,
               decltype(eight_aligned_view.zero_offset_six_stride_array()[0]
                            .zero_offset())>::value));
  EXPECT_TRUE((::std::is_same<
               GenericPlaceholder4View<ContiguousBuffer<char, 2, 0>>,
               decltype(eight_aligned_view.zero_offset_six_stride_array()[0]
                            .two_offset())>::value));
  EXPECT_TRUE((::std::is_same<
               GenericPlaceholder4View<ContiguousBuffer<char, 2, 0>>,
               decltype(eight_aligned_view.four_offset_six_stride_array()[0]
                            .zero_offset())>::value));
  EXPECT_TRUE((::std::is_same<
               GenericPlaceholder4View<ContiguousBuffer<char, 2, 0>>,
               decltype(eight_aligned_view.four_offset_six_stride_array()[0]
                            .two_offset())>::value));
}

}  // namespace
}  // namespace test
}  // namespace emboss
