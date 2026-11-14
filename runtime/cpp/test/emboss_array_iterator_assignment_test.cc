// Copyright 2026 Google LLC
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

#include <type_traits>
#include <utility>

#include "gtest/gtest.h"
#include "runtime/cpp/emboss_array_view.h"
#include "runtime/cpp/emboss_prelude.h"

namespace emboss {
namespace support {
namespace test {
namespace {

using ByteView = ::emboss::prelude::UIntView<
    FixedSizeViewParameters<8, AllValuesAreOk>,
    BitBlock<LittleEndianByteOrderer<ReadWriteContiguousBuffer>, 8>>;
using ByteArray = GenericArrayView<ByteView, ReadWriteContiguousBuffer, 1, 8>;

static_assert(std::is_copy_assignable<ByteArray::ForwardIterator>::value,
              "Forward iterators must be copy-assignable");
static_assert(std::is_move_assignable<ByteArray::ForwardIterator>::value,
              "Forward iterators must be move-assignable");
static_assert(std::is_copy_assignable<ByteArray::ReverseIterator>::value,
              "Reverse iterators must be copy-assignable");
static_assert(std::is_move_assignable<ByteArray::ReverseIterator>::value,
              "Reverse iterators must be move-assignable");

TEST(ArrayIteratorAssignment, ForwardCopyAssignmentRebindsPositionAndArray) {
  unsigned char left_bytes[] = {1, 2, 3};
  unsigned char right_bytes[] = {10, 20, 30};
  const ByteArray left(
      ReadWriteContiguousBuffer(left_bytes, sizeof left_bytes));
  const ByteArray right(
      ReadWriteContiguousBuffer(right_bytes, sizeof right_bytes));
  auto iterator = left.begin();
  const auto replacement = right.begin() + 1;

  iterator = replacement;
  EXPECT_EQ(replacement, iterator);
  EXPECT_EQ(20, iterator->Read());
  ++iterator;
  EXPECT_EQ(30, iterator->Read());
  iterator->Write(99);
  EXPECT_EQ(99, right_bytes[2]);
  EXPECT_EQ(3, left_bytes[2]);
}

TEST(ArrayIteratorAssignment, ReverseCopyAssignmentRebindsPositionAndArray) {
  unsigned char left_bytes[] = {1, 2, 3};
  unsigned char right_bytes[] = {10, 20, 30};
  const ByteArray left(
      ReadWriteContiguousBuffer(left_bytes, sizeof left_bytes));
  const ByteArray right(
      ReadWriteContiguousBuffer(right_bytes, sizeof right_bytes));
  auto iterator = left.rbegin();
  const auto replacement = right.rbegin() + 1;

  iterator = replacement;
  EXPECT_EQ(replacement, iterator);
  EXPECT_EQ(20, iterator->Read());
  ++iterator;
  EXPECT_EQ(10, iterator->Read());
  iterator->Write(99);
  EXPECT_EQ(99, right_bytes[0]);
  EXPECT_EQ(1, left_bytes[0]);
}

TEST(ArrayIteratorAssignment, ForwardMoveAssignmentInitializesDefaultIterator) {
  unsigned char bytes[] = {1, 2, 3};
  const ByteArray array(ReadWriteContiguousBuffer(bytes, sizeof bytes));
  ByteArray::ForwardIterator iterator;
  auto replacement = array.begin() + 1;
  iterator = std::move(replacement);
  EXPECT_EQ(2, iterator->Read());
  ++iterator;
  EXPECT_EQ(3, iterator->Read());
}

TEST(ArrayIteratorAssignment, ReverseMoveAssignmentInitializesDefaultIterator) {
  unsigned char bytes[] = {1, 2, 3};
  const ByteArray array(ReadWriteContiguousBuffer(bytes, sizeof bytes));
  ByteArray::ReverseIterator iterator;
  auto replacement = array.rbegin() + 1;
  iterator = std::move(replacement);
  EXPECT_EQ(2, iterator->Read());
  ++iterator;
  EXPECT_EQ(1, iterator->Read());
}

}  // namespace
}  // namespace test
}  // namespace support
}  // namespace emboss
