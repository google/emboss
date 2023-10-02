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

// Tests for automatically-sized arrays from auto_array_size.emb.

#include <stdint.h>

#include <iterator>
#include <random>
#include <vector>

#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "runtime/cpp/emboss_text_util.h"
#include "testdata/auto_array_size.emb.h"

namespace emboss {
namespace test {
namespace {

alignas(8) static const ::std::uint8_t kAutoSize[22] = {
    0x03,                                // 0:1    array_size == 3
    0x10, 0x20, 0x30, 0x40,              // 1:5    four_byte_array
    0x11, 0x12, 0x21, 0x22,              // 5:9    four_struct_array[0, 1]
    0x31, 0x32, 0x41, 0x42,              // 9:13   four_struct_array[2, 3]
    0x50, 0x60, 0x70,                    // 13:16  dynamic_byte_array
    0x51, 0x52, 0x61, 0x62, 0x71, 0x72,  // 16:22  dynamic_struct_array
};

TEST(AutoSizeView, IteratorIncrement) {
  auto src_buf = ::std::vector</**/ ::std::uint8_t>(
      kAutoSize, kAutoSize + sizeof kAutoSize);
  auto src = MakeAutoSizeView(&src_buf).four_struct_array();
  auto dst_buf = ::std::vector</**/ ::std::uint8_t>(
      kAutoSize, kAutoSize + sizeof kAutoSize);
  auto dst = MakeAutoSizeView(&dst_buf).four_struct_array();
  EXPECT_TRUE(src.Equals(dst));

  ::std::fill(dst.BackingStorage().begin(), dst.BackingStorage().end(), 0);
  EXPECT_FALSE(src.Equals(dst));
  for (auto src_it = src.begin(), dst_it = dst.begin();
       src_it != src.end() && dst_it != dst.end(); ++src_it, ++dst_it) {
    dst_it->CopyFrom(*src_it);
  }
  EXPECT_TRUE(src.Equals(dst));

  ::std::fill(dst.BackingStorage().begin(), dst.BackingStorage().end(), 0);
  EXPECT_FALSE(src.Equals(dst));
  for (auto src_it = src.begin(), dst_it = dst.begin();
       src_it != src.end() && dst_it != dst.end(); src_it++, dst_it++) {
    dst_it->CopyFrom(*src_it);
  }
  EXPECT_TRUE(src.Equals(dst));

  ::std::fill(dst.BackingStorage().begin(), dst.BackingStorage().end(), 0);
  EXPECT_FALSE(src.Equals(dst));
  for (auto src_it = src.rbegin(), dst_it = dst.rbegin();
       src_it != src.rend() && dst_it != dst.rend(); ++src_it, ++dst_it) {
    dst_it->CopyFrom(*src_it);
  }
  EXPECT_TRUE(src.Equals(dst));

  ::std::fill(dst.BackingStorage().begin(), dst.BackingStorage().end(), 0);
  EXPECT_FALSE(src.Equals(dst));
  for (auto src_it = src.rbegin(), dst_it = dst.rbegin();
       src_it != src.rend() && dst_it != dst.rend(); src_it++, dst_it++) {
    dst_it->CopyFrom(*src_it);
  }
  EXPECT_TRUE(src.Equals(dst));

  EXPECT_EQ(src.begin(), src.begin()++);
  EXPECT_EQ(src.rbegin(), src.rbegin()++);
  EXPECT_EQ(src.end(), (src.end())--);
  EXPECT_EQ(src.rend(), src.rend()--);
}

TEST(AutoSizeView, PreviousNext) {
  auto view = MakeAutoSizeView(kAutoSize, sizeof kAutoSize).four_struct_array();
  EXPECT_TRUE(::std::next(view.begin(), 0)->Equals(view[0]));
  EXPECT_TRUE(::std::next(view.begin(), 1)->Equals(view[1]));
  EXPECT_TRUE(::std::next(view.begin(), 2)->Equals(view[2]));
  EXPECT_TRUE(::std::next(view.begin(), 3)->Equals(view[3]));

  EXPECT_TRUE(::std::next(view.rbegin(), 0)->Equals(view[3]));
  EXPECT_TRUE(::std::next(view.rbegin(), 1)->Equals(view[2]));
  EXPECT_TRUE(::std::next(view.rbegin(), 2)->Equals(view[1]));
  EXPECT_TRUE(::std::next(view.rbegin(), 3)->Equals(view[0]));

  EXPECT_TRUE(::std::prev(view.end(), 1)->Equals(view[3]));
  EXPECT_TRUE(::std::prev(view.end(), 2)->Equals(view[2]));
  EXPECT_TRUE(::std::prev(view.end(), 3)->Equals(view[1]));
  EXPECT_TRUE(::std::prev(view.end(), 4)->Equals(view[0]));

  EXPECT_TRUE(::std::prev(view.rend(), 1)->Equals(view[0]));
  EXPECT_TRUE(::std::prev(view.rend(), 2)->Equals(view[1]));
  EXPECT_TRUE(::std::prev(view.rend(), 3)->Equals(view[2]));
  EXPECT_TRUE(::std::prev(view.rend(), 4)->Equals(view[3]));
}

TEST(AutoSizeView, ForEach) {
  auto view = MakeAutoSizeView(kAutoSize, sizeof kAutoSize).four_struct_array();

  int i = 0;
  ::std::for_each(view.begin(), view.end(), [&](ElementView element) {
    ASSERT_TRUE(element.Equals(view[i++]));
  });

  i = view.ElementCount() - 1;
  ::std::for_each(view.rbegin(), view.rend(), [&](ElementView element) {
    ASSERT_TRUE(element.Equals(view[i--]));
  });
}

TEST(AutoSizeView, ForEachWithTemporaries) {
  auto view = MakeAutoSizeView(kAutoSize, sizeof kAutoSize);

  int i = 0;
  ::std::for_each(view.four_struct_array().begin(),
                  view.four_struct_array().end(), [&](ElementView element) {
                    ASSERT_TRUE(element.Equals(view.four_struct_array()[i++]));
                  });

  i = view.four_struct_array().ElementCount() - 1;
  ::std::for_each(view.four_struct_array().rbegin(),
                  view.four_struct_array().rend(), [&](ElementView element) {
                    ASSERT_TRUE(element.Equals(view.four_struct_array()[i--]));
                  });
}

TEST(AutoSizeView, Find) {
  auto view = MakeAutoSizeView(kAutoSize, sizeof kAutoSize).four_struct_array();

  EXPECT_TRUE(
      ::std::find_if(view.begin(), view.end(), [view](ElementView element) {
        return element.Equals(view[0]);
      })->Equals(view[0]));
  EXPECT_TRUE(
      ::std::find_if(view.begin(), view.end(), [view](ElementView element) {
        return element.Equals(view[1]);
      })->Equals(view[1]));
  EXPECT_TRUE(
      ::std::find_if(view.begin(), view.end(), [view](ElementView element) {
        return element.Equals(view[2]);
      })->Equals(view[2]));
  EXPECT_TRUE(
      ::std::find_if(view.begin(), view.end(), [view](ElementView element) {
        return element.Equals(view[3]);
      })->Equals(view[3]));

  EXPECT_TRUE(
      ::std::find_if(view.rbegin(), view.rend(), [view](ElementView element) {
        return element.Equals(view[0]);
      })->Equals(view[0]));
  EXPECT_TRUE(
      ::std::find_if(view.rbegin(), view.rend(), [view](ElementView element) {
        return element.Equals(view[1]);
      })->Equals(view[1]));
  EXPECT_TRUE(
      ::std::find_if(view.rbegin(), view.rend(), [view](ElementView element) {
        return element.Equals(view[2]);
      })->Equals(view[2]));
  EXPECT_TRUE(
      ::std::find_if(view.rbegin(), view.rend(), [view](ElementView element) {
        return element.Equals(view[3]);
      })->Equals(view[3]));
}

TEST(AutoSizeView, Comparison) {
  auto view = MakeAutoSizeView(kAutoSize, sizeof kAutoSize).four_struct_array();

  EXPECT_EQ(view.begin() + view.ElementCount(), view.end());
  EXPECT_EQ(view.end() - view.ElementCount(), view.begin());

  EXPECT_EQ(view.rbegin() + view.ElementCount(), view.rend());
  EXPECT_EQ(view.rend() - view.ElementCount(), view.rbegin());

  EXPECT_LT(view.begin(), view.end());
  EXPECT_LT(view.rbegin(), view.rend());

  EXPECT_LE(view.begin() - 1, view.end());
  EXPECT_LE(view.rbegin() - 1, view.rend());
  EXPECT_LE(view.begin() - 1, view.end());
  EXPECT_LE(view.rbegin() - 1, view.rend());

  EXPECT_GT(view.end(), view.begin());
  EXPECT_GT(view.rend(), view.rbegin());

  EXPECT_GE(view.end() + 1, view.begin());
  EXPECT_GE(view.end() + 1, view.begin());
  EXPECT_GE(view.rend() + 1, view.rbegin());
  EXPECT_GE(view.rend() + 1, view.rbegin());
}

TEST(AutoSizeView, RangeBasedFor) {
  auto view = MakeAutoSizeView(kAutoSize, sizeof kAutoSize).four_struct_array();

  int i = 0;
  for (auto element : view) {
    ASSERT_TRUE(element.Equals(view[i++]));
  }
}

TEST(AutoSizeView, CanReadAutoArrays) {
  auto view = MakeAlignedAutoSizeView<const ::std::uint8_t, 8>(
      kAutoSize, sizeof kAutoSize);
  EXPECT_EQ(22U, view.SizeInBytes());
  EXPECT_EQ(3U, view.array_size().Read());
  EXPECT_EQ(0x10U, view.four_byte_array()[0].Read());
  EXPECT_EQ(0x20U, view.four_byte_array()[1].Read());
  EXPECT_EQ(0x30U, view.four_byte_array()[2].Read());
  EXPECT_EQ(0x40U, view.four_byte_array()[3].Read());
  EXPECT_EQ(4U, view.four_byte_array().SizeInBytes());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(view.four_byte_array()[4].Read(), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_EQ(0x11U, view.four_struct_array()[0].a().Read());
  EXPECT_EQ(0x12U, view.four_struct_array()[0].b().Read());
  EXPECT_EQ(0x21U, view.four_struct_array()[1].a().Read());
  EXPECT_EQ(0x22U, view.four_struct_array()[1].b().Read());
  EXPECT_EQ(0x31U, view.four_struct_array()[2].a().Read());
  EXPECT_EQ(0x32U, view.four_struct_array()[2].b().Read());
  EXPECT_EQ(0x41U, view.four_struct_array()[3].a().Read());
  EXPECT_EQ(0x42U, view.four_struct_array()[3].b().Read());
  EXPECT_EQ(8U, view.four_struct_array().SizeInBytes());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(view.four_struct_array()[4].a().Read(), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_EQ(0x50U, view.dynamic_byte_array()[0].Read());
  EXPECT_EQ(0x60U, view.dynamic_byte_array()[1].Read());
  EXPECT_EQ(0x70U, view.dynamic_byte_array()[2].Read());
  EXPECT_EQ(3U, view.dynamic_byte_array().SizeInBytes());
  EXPECT_FALSE(view.dynamic_byte_array()[3].IsComplete());
  EXPECT_EQ(0x51U, view.dynamic_struct_array()[0].a().Read());
  EXPECT_EQ(0x52U, view.dynamic_struct_array()[0].b().Read());
  EXPECT_EQ(0x61U, view.dynamic_struct_array()[1].a().Read());
  EXPECT_EQ(0x62U, view.dynamic_struct_array()[1].b().Read());
  EXPECT_EQ(0x71U, view.dynamic_struct_array()[2].a().Read());
  EXPECT_EQ(0x72U, view.dynamic_struct_array()[2].b().Read());
  EXPECT_EQ(6U, view.dynamic_struct_array().SizeInBytes());
  EXPECT_FALSE(view.dynamic_struct_array()[3].IsComplete());
}

TEST(AutoSizeWriter, CanWriteAutoArrays) {
  ::std::vector<char> buffer(sizeof kAutoSize, 0);
  auto writer = MakeAutoSizeView(&buffer);
  writer.array_size().Write(0);
  EXPECT_EQ(13U, writer.SizeInBytes());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(writer.dynamic_byte_array()[0].Read(), "");
#endif  // EMBOSS_CHECK_ABORTS
  writer.array_size().Write(3);
  EXPECT_EQ(22U, writer.SizeInBytes());
  writer.four_byte_array()[0].Write(0x10);
  writer.four_byte_array()[1].Write(0x20);
  writer.four_byte_array()[2].Write(0x30);
  writer.four_byte_array()[3].Write(0x40);
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(writer.four_byte_array()[4].Write(0), "");
#endif  // EMBOSS_CHECK_ABORTS
  writer.four_struct_array()[0].a().Write(0x11);
  writer.four_struct_array()[0].b().Write(0x12);
  writer.four_struct_array()[1].a().Write(0x21);
  writer.four_struct_array()[1].b().Write(0x22);
  writer.four_struct_array()[2].a().Write(0x31);
  writer.four_struct_array()[2].b().Write(0x32);
  writer.four_struct_array()[3].a().Write(0x41);
  writer.four_struct_array()[3].b().Write(0x42);
  EXPECT_FALSE(writer.four_struct_array()[4].IsComplete());
  writer.dynamic_byte_array()[0].Write(0x50);
  writer.dynamic_byte_array()[1].Write(0x60);
  writer.dynamic_byte_array()[2].Write(0x70);
  EXPECT_FALSE(writer.dynamic_byte_array()[3].IsComplete());
  writer.dynamic_struct_array()[0].a().Write(0x51);
  writer.dynamic_struct_array()[0].b().Write(0x52);
  writer.dynamic_struct_array()[1].a().Write(0x61);
  writer.dynamic_struct_array()[1].b().Write(0x62);
  writer.dynamic_struct_array()[2].a().Write(0x71);
  writer.dynamic_struct_array()[2].b().Write(0x72);
  EXPECT_FALSE(writer.dynamic_struct_array()[3].IsComplete());
  EXPECT_EQ(::std::vector<char>(kAutoSize, kAutoSize + sizeof kAutoSize),
            buffer);
}

TEST(AutoSizeView, CanUseDataMethod) {
  auto view = MakeAlignedAutoSizeView<const ::std::uint8_t, 8>(
      kAutoSize, sizeof kAutoSize);

  for (unsigned i = 0; i < view.SizeInBytes(); ++i) {
    EXPECT_EQ(*(view.BackingStorage().data() + i), kAutoSize[i])
        << " at element " << i;
  }
}

TEST(AutoSizeView, CanCopyFrom) {
  auto source = MakeAlignedAutoSizeView<const ::std::uint8_t, 8>(
      kAutoSize, sizeof kAutoSize);

  ::std::array</**/ ::std::uint8_t, sizeof kAutoSize> buf = {0};
  auto dest =
      MakeAlignedAutoSizeView</**/ ::std::uint8_t, 8>(buf.data(), buf.size());

  // Copy one element.
  EXPECT_NE(source.four_struct_array()[0].a().Read(),
            dest.four_struct_array()[0].a().Read());
  EXPECT_NE(source.four_struct_array()[0].b().Read(),
            dest.four_struct_array()[0].b().Read());
  dest.four_struct_array()[0].CopyFrom(source.four_struct_array()[0]);
  EXPECT_EQ(source.four_struct_array()[0].a().Read(),
            dest.four_struct_array()[0].a().Read());
  EXPECT_EQ(source.four_struct_array()[0].b().Read(),
            dest.four_struct_array()[0].b().Read());

  // Copy entire view.
  dest.CopyFrom(source);
  for (unsigned i = 0; i < source.four_struct_array().ElementCount(); ++i) {
    EXPECT_EQ(source.four_struct_array()[i].a().Read(),
              dest.four_struct_array()[i].a().Read());
    EXPECT_EQ(source.four_struct_array()[i].b().Read(),
              dest.four_struct_array()[i].b().Read());
  }
}

TEST(AutoSizeView, CanCopyFromDifferentSizes) {
  constexpr int padding = 10;
  ::std::array</**/ ::std::uint8_t, sizeof kAutoSize + padding> source_buffer;
  memset(source_buffer.data(), 0, source_buffer.size());
  memcpy(source_buffer.data(), kAutoSize, sizeof kAutoSize);
  auto source = MakeAutoSizeView(&source_buffer);

  ::std::array</**/ ::std::uint8_t, sizeof kAutoSize + padding> buf;
  memset(buf.data(), 0xff, buf.size());
  auto dest = MakeAutoSizeView(buf.data(), sizeof kAutoSize);

  dest.CopyFrom(source);
  for (unsigned i = 0; i < sizeof kAutoSize; ++i) {
    EXPECT_EQ(buf[i], source_buffer[i]) << i;
  }
  for (unsigned i = sizeof kAutoSize; i < sizeof kAutoSize + padding; ++i) {
    EXPECT_EQ(buf[i], 0xff) << i;
  }
}

TEST(AutoSizeView, CanCopyFromOverlapping) {
  constexpr int kElementSizeBytes = ElementView::SizeInBytes();
  ::std::vector</**/ ::std::uint8_t> buf = {1, 2, 3};

  auto source = MakeElementView(buf.data(), kElementSizeBytes);
  auto dest = MakeElementView(buf.data() + 1, kElementSizeBytes);
  EXPECT_EQ(source.a().Read(), buf[0]);
  EXPECT_EQ(source.b().Read(), dest.a().Read());
  EXPECT_EQ(dest.b().Read(), buf[2]);

  dest.CopyFrom(source);  // Forward overlap.
  EXPECT_EQ(buf, ::std::vector</**/ ::std::uint8_t>({1, 1, 2}));
  source.CopyFrom(dest);  // Reverse overlap.
  EXPECT_EQ(buf, ::std::vector</**/ ::std::uint8_t>({1, 2, 2}));
}

TEST(AutoSizeView, Equals) {
  ::std::vector</**/ ::std::uint8_t> buf_x = {1, 2};
  ::std::vector</**/ ::std::uint8_t> buf_y = {1, 2, 3};
  auto x = MakeElementView(&buf_x);
  auto x_const = MakeElementView(
      static_cast<const ::std::vector</**/ ::std::uint8_t>*>(&buf_x));
  auto y = MakeElementView(&buf_y);

  EXPECT_TRUE(x.Equals(x));
  EXPECT_TRUE(x.UncheckedEquals(x));
  EXPECT_TRUE(y.Equals(y));
  EXPECT_TRUE(y.UncheckedEquals(y));

  EXPECT_TRUE(x.Equals(y));
  EXPECT_TRUE(x.UncheckedEquals(y));
  EXPECT_TRUE(y.Equals(x));
  EXPECT_TRUE(y.UncheckedEquals(x));

  EXPECT_TRUE(y.Equals(x_const));
  EXPECT_TRUE(y.UncheckedEquals(x_const));
  EXPECT_TRUE(x_const.Equals(y));
  EXPECT_TRUE(x_const.UncheckedEquals(y));

  ++buf_y[1];
  EXPECT_FALSE(x.Equals(y));
  EXPECT_FALSE(x.UncheckedEquals(y));
  EXPECT_FALSE(y.Equals(x));
  EXPECT_FALSE(y.UncheckedEquals(x));
}

}  // namespace
}  // namespace test
}  // namespace emboss
