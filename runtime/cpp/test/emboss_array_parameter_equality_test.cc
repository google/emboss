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

#include "gtest/gtest.h"
#include "runtime/cpp/emboss_array_view.h"
#include "runtime/cpp/emboss_prelude.h"

namespace emboss {
namespace support {
namespace test {
namespace {

// A parameterized view using the real byte-view implementation. The bias
// changes the logical element value without changing its backing bytes.
template <class Storage, class Bias = int>
class BiasedByteView {
 public:
  BiasedByteView(Bias bias, Storage storage) : bias_(bias), value_(storage) {}

  int Read() const { return static_cast<int>(value_.Read()) + bias_; }
  int UncheckedRead() const {
    return static_cast<int>(value_.UncheckedRead()) + bias_;
  }
  template <class OtherStorage, class OtherBias>
  bool Equals(const BiasedByteView<OtherStorage, OtherBias>& other) const {
    return Read() == other.Read();
  }
  template <class OtherStorage, class OtherBias>
  bool UncheckedEquals(
      const BiasedByteView<OtherStorage, OtherBias>& other) const {
    return UncheckedRead() == other.UncheckedRead();
  }

 private:
  Bias bias_;
  ::emboss::prelude::UIntView<FixedSizeViewParameters<8, AllValuesAreOk>,
                              BitBlock<LittleEndianByteOrderer<Storage>, 8>>
      value_;
};

template <class Storage, class Bias = int>
using BiasedByteArray =
    GenericArrayView<BiasedByteView<Storage, Bias>, Storage, 1, 8, Bias>;

TEST(ArrayParameterEquality, ComparesLogicalValues) {
  unsigned char left_bytes[] = {1, 2};
  unsigned char right_bytes[] = {2, 3};
  const BiasedByteArray<ReadWriteContiguousBuffer> left(
      1, ReadWriteContiguousBuffer(left_bytes, sizeof left_bytes));
  const BiasedByteArray<ReadWriteContiguousBuffer> equal(
      0, ReadWriteContiguousBuffer(right_bytes, sizeof right_bytes));
  const BiasedByteArray<ReadWriteContiguousBuffer> different(
      2, ReadWriteContiguousBuffer(left_bytes, sizeof left_bytes));
  EXPECT_TRUE(left.Equals(equal));
  EXPECT_TRUE(left.UncheckedEquals(equal));
  EXPECT_FALSE(left.Equals(different));
  EXPECT_FALSE(left.UncheckedEquals(different));
}

TEST(ArrayParameterEquality, ComparesCompatibleStorageAndParameterTypes) {
  unsigned char left_bytes[] = {1, 2};
  const unsigned char right_bytes[] = {2, 3};
  const BiasedByteArray<ReadWriteContiguousBuffer> left(
      1, ReadWriteContiguousBuffer(left_bytes, sizeof left_bytes));
  const BiasedByteArray<ReadOnlyContiguousBuffer, short> right(
      0, ReadOnlyContiguousBuffer(right_bytes, sizeof right_bytes));
  EXPECT_TRUE(left.Equals(right));
  EXPECT_TRUE(right.Equals(left));
  EXPECT_TRUE(left.UncheckedEquals(right));
  EXPECT_TRUE(right.UncheckedEquals(left));
}

TEST(ArrayParameterEquality, RejectsDifferentLengths) {
  unsigned char bytes[] = {1, 2};
  const BiasedByteArray<ReadWriteContiguousBuffer> left(
      1, ReadWriteContiguousBuffer(bytes, sizeof bytes));
  const BiasedByteArray<ReadWriteContiguousBuffer> right(
      1, ReadWriteContiguousBuffer(bytes, 1));
  EXPECT_FALSE(left.Equals(right));
  EXPECT_FALSE(left.UncheckedEquals(right));
}

TEST(ArrayParameterEquality, EmptyArraysCompareEqual) {
  unsigned char bytes[] = {0};
  const BiasedByteArray<ReadWriteContiguousBuffer> left(
      1, ReadWriteContiguousBuffer(bytes, 0));
  const BiasedByteArray<ReadWriteContiguousBuffer> right(
      2, ReadWriteContiguousBuffer(bytes, 0));
  EXPECT_TRUE(left.Equals(right));
  EXPECT_TRUE(left.UncheckedEquals(right));
}

TEST(ArrayParameterEquality, UnparameterizedArraysStillCompare) {
  unsigned char bytes[] = {1, 2};
  using ByteView = ::emboss::prelude::UIntView<
      FixedSizeViewParameters<8, AllValuesAreOk>,
      BitBlock<LittleEndianByteOrderer<ReadWriteContiguousBuffer>, 8>>;
  using ByteArray = GenericArrayView<ByteView, ReadWriteContiguousBuffer, 1, 8>;
  const ByteArray left(ReadWriteContiguousBuffer(bytes, sizeof bytes));
  const ByteArray right(ReadWriteContiguousBuffer(bytes, sizeof bytes));
  EXPECT_TRUE(left.Equals(right));
  EXPECT_TRUE(left.UncheckedEquals(right));
}

}  // namespace
}  // namespace test
}  // namespace support
}  // namespace emboss
