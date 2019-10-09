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

// Tests for fields and structs with dynamic sizes.
#include <stdint.h>

#include <vector>

#include "gtest/gtest.h"
#include "testdata/dynamic_size.emb.h"

namespace emboss {
namespace test {
namespace {

static constexpr ::std::array</**/ ::std::uint8_t, 16> kMessage = {{
    0x02,                                // 0:1   header_length = 2
    0x06,                                // 1:2   message_length = 6
    0x01, 0x02, 0x03, 0x04, 0x05, 0x06,  // 2:8   message
    0x07, 0x08, 0x09, 0x0a,              // 8:12  crc32
    0x00, 0x00, 0x00, 0x00,              // Extra, unused bytes.
}};

// MessageView::SizeInBytes() returns the expected value.
TEST(MessageView, DynamicSizeIsCorrect) {
  auto view = MessageView(&kMessage);
  EXPECT_EQ(12U, view.SizeInBytes());
}

// Fields read the correct values.
TEST(MessageView, FieldsAreCorrect) {
  auto view = MessageView(&kMessage);
  EXPECT_EQ(2U, view.header_length().Read());
  EXPECT_EQ(6U, view.message_length().Read());
  EXPECT_EQ(1U, view.message()[0].Read());
  EXPECT_EQ(2U, view.message()[1].Read());
  EXPECT_EQ(3U, view.message()[2].Read());
  EXPECT_EQ(4U, view.message()[3].Read());
  EXPECT_EQ(5U, view.message()[4].Read());
  EXPECT_EQ(6U, view.message()[5].Read());
  EXPECT_EQ(6U, view.message().SizeInBytes());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(view.message()[6].Read(), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_EQ(0x0a090807U, view.crc32().Read());
}

// The zero-length padding field works as expected.
TEST(MessageView, PaddingFieldWorks) {
  auto view = MessageView(&kMessage);
  EXPECT_EQ(0U, view.padding().SizeInBytes());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(view.padding()[0].Read(), "");
#endif  // EMBOSS_CHECK_ABORTS
}

static constexpr ::std::array</**/ ::std::uint8_t, 16> kPaddedMessage = {{
    0x06,                    // 0:1    header_length = 6
    0x04,                    // 1:2    message_length = 4
    0x01, 0x02, 0x03, 0x04,  // 2:6    padding
    0x05, 0x06, 0x07, 0x08,  // 6:10   message
    0x09, 0x0a, 0x0b, 0x0c,  // 10:14  crc32
    0x00, 0x00,              // Extra, unused bytes.
}};

// Fields read the correct values.
TEST(MessageView, PaddedMessageFieldsAreCorrect) {
  auto view = MessageView(&kPaddedMessage);
  EXPECT_EQ(6U, view.header_length().Read());
  EXPECT_EQ(4U, view.message_length().Read());
  EXPECT_EQ(1U, view.padding()[0].Read());
  EXPECT_EQ(2U, view.padding()[1].Read());
  EXPECT_EQ(3U, view.padding()[2].Read());
  EXPECT_EQ(4U, view.padding()[3].Read());
  EXPECT_EQ(4U, view.padding().SizeInBytes());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(view.padding()[4].Read(), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_EQ(5U, view.message()[0].Read());
  EXPECT_EQ(6U, view.message()[1].Read());
  EXPECT_EQ(7U, view.message()[2].Read());
  EXPECT_EQ(8U, view.message()[3].Read());
  EXPECT_EQ(4U, view.message().SizeInBytes());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(view.message()[4].Read(), "");
#endif  // EMBOSS_CHECK_ABORTS
  EXPECT_EQ(0x0c0b0a09U, view.crc32().Read());
}

// Writes to fields produce the correct byte values.
TEST(MessageView, Writer) {
  ::std::uint8_t buffer[kPaddedMessage.size()] = {0};
  auto writer = MessageWriter(buffer, sizeof buffer);

  // Write values that should match kMessage.
  writer.header_length().Write(2);
  writer.message_length().Write(6);
  EXPECT_EQ(6, writer.message_length().Read());
  for (int i = 0; i < writer.message_length().Read(); ++i) {
    writer.message()[i].Write(i + 1);
  }
  EXPECT_EQ(12U, writer.SizeInBytes());
#if EMBOSS_CHECK_ABORTS
  EXPECT_DEATH(writer.message()[writer.message_length().Read()].Read(), "");
  EXPECT_DEATH(writer.padding()[0].Read(), "");
#endif  // EMBOSS_CHECK_ABORTS
  writer.crc32().Write(0x0a090807);
  EXPECT_EQ(
      ::std::vector</**/ ::std::uint8_t>(kMessage.begin(), kMessage.end()),
      ::std::vector</**/ ::std::uint8_t>(buffer, buffer + kMessage.size()));

  // Update values to match kPaddedMessage.  Only update values that are
  // different.
  auto writer2 = MessageWriter(buffer, sizeof buffer);
  writer2.header_length().Write(6);
  // Writes made through one writer should be immediately visible to the other.
  EXPECT_EQ(6U, writer.header_length().Read());
  EXPECT_EQ(6U, writer2.header_length().Read());
  writer2.message_length().Write(4);
  // The message() field is now pointing to a different place; it should read
  // the data that was already there.
  EXPECT_EQ(5U, writer2.message()[0].Read());
  // The padding bytes are already set to the correct values; do not update
  // them.
  for (int i = 0; i < writer2.message_length().Read(); ++i) {
    writer2.padding()[i].Write(i + 1);
  }
  writer2.crc32().Write(0x0c0b0a09);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kPaddedMessage.begin(),
                                               kPaddedMessage.end()),
            ::std::vector</**/ ::std::uint8_t>(buffer,
                                               buffer + kPaddedMessage.size()));
}

TEST(MessageView, MakeFromPointerArrayIterator) {
  ::std::array<const ::std::array</**/ ::std::uint8_t, 16> *, 2> buffers = {
      {&kMessage, &kPaddedMessage}};
  // Ensure that the weird const-reference-to-pointer type returned by iteration
  // over a std::array of std::arrays actually compiles.
  for (const auto &buffer : buffers) {
    auto view = MakeMessageView(buffer);
    // Message length is 4 or 6, depending on the iteration.
    EXPECT_TRUE(view.message_length().Read() == 4 ||
                view.message_length().Read() == 6);
  }
}

static const ::std::uint8_t kThreeByFiveImage[46] = {
    0x03,              // 0:1  size
    0x01, 0x02, 0x03,  // pixels[0][0]
    0x04, 0x05, 0x06,  // pixels[0][1]
    0x07, 0x08, 0x09,  // pixels[0][2]
    0x0a, 0x0b, 0x0c,  // pixels[0][3]
    0x0d, 0x0e, 0x0f,  // pixels[0][4]
    0x10, 0x11, 0x12,  // pixels[1][0]
    0x13, 0x14, 0x15,  // pixels[1][1]
    0x16, 0x17, 0x18,  // pixels[1][2]
    0x19, 0x1a, 0x1b,  // pixels[1][3]
    0x1c, 0x1d, 0x1e,  // pixels[1][4]
    0x1f, 0x20, 0x21,  // pixels[2][0]
    0x22, 0x23, 0x24,  // pixels[2][1]
    0x25, 0x26, 0x27,  // pixels[2][2]
    0x28, 0x29, 0x2a,  // pixels[2][3]
    0x2b, 0x2c, 0x2d,  // pixels[2][4]
};

// A variable-sized array of fixed-size arrays of fixed-size arrays reads
// correct values.
TEST(ImageView, PixelsAreCorrect) {
  auto view = ImageView(kThreeByFiveImage, sizeof kThreeByFiveImage);
  int counter = 1;
  for (int x = 0; x < view.size().Read(); ++x) {
    for (int y = 0; y < 5; ++y) {
      for (int channel = 0; channel < 3; ++channel) {
        EXPECT_EQ(counter, view.pixels()[x][y][channel].Read())
            << "x: " << x << "; y: " << y << "; channel: " << channel;
        ++counter;
      }
    }
  }
}

TEST(ImageView, WritePixels) {
  ::std::uint8_t buffer[sizeof kThreeByFiveImage];
  auto writer = ImageWriter(buffer, sizeof buffer);
  writer.size().Write(3);
  int counter = 1;
  for (int x = 0; x < writer.size().Read(); ++x) {
    for (int y = 0; y < 5; ++y) {
      for (int channel = 0; channel < 3; ++channel) {
        writer.pixels()[x][y][channel].Write(counter);
        ++counter;
      }
    }
  }
  EXPECT_EQ(
      ::std::vector</**/ ::std::uint8_t>(
          kThreeByFiveImage, kThreeByFiveImage + sizeof kThreeByFiveImage),
      ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

static const ::std::uint8_t kTwoRegionsAFirst[10] = {
    0x04,                    // 0:1   a_start
    0x02,                    // 1:2   a_size
    0x06,                    // 2:3   b_start
    0x0a,                    // 3:4   b_end
    0x11, 0x22,              // 4:6   region_a
    0x33, 0x44, 0x55, 0x66,  // 6:10  region_b
};

// With two dynamically-positioned regions, having the binary locations match
// the order of their declarations works.
TEST(TwoRegionsView, RegionAFirstWorks) {
  auto view = TwoRegionsView(kTwoRegionsAFirst, sizeof kTwoRegionsAFirst);
  EXPECT_EQ(10U, view.SizeInBytes());
  EXPECT_EQ(4U, view.a_start().Read());
  EXPECT_EQ(2U, view.a_size().Read());
  EXPECT_EQ(6U, view.b_start().Read());
  EXPECT_EQ(10U, view.b_end().Read());
  EXPECT_EQ(0x11U, view.region_a()[0].Read());
  EXPECT_EQ(0x22U, view.region_a()[1].Read());
  EXPECT_EQ(0x33U, view.region_b()[0].Read());
  EXPECT_EQ(0x66U, view.region_b()[3].Read());
}

static const ::std::uint8_t kTwoRegionsBFirst[14] = {
    0x0a,                    // 0:1    a_start
    0x04,                    // 1:2    a_size
    0x04,                    // 2:3    b_start
    0x06,                    // 3:4    b_end
    0x11, 0x22,              // 4:6    region_b
    0xff, 0xff, 0xff, 0xff,  // 6:10   unmapped
    0x33, 0x44, 0x55, 0x66,  // 10:14  region_a
};

// With two dynamically-positioned regions, having the binary locations opposite
// of the order of their declarations works.
TEST(TwoRegionsView, RegionBFirstWorks) {
  auto view = TwoRegionsView(kTwoRegionsBFirst, sizeof kTwoRegionsBFirst);
  EXPECT_EQ(14U, view.SizeInBytes());
  EXPECT_EQ(10U, view.a_start().Read());
  EXPECT_EQ(4U, view.a_size().Read());
  EXPECT_EQ(4U, view.b_start().Read());
  EXPECT_EQ(6U, view.b_end().Read());
  EXPECT_EQ(0x33U, view.region_a()[0].Read());
  EXPECT_EQ(0x66U, view.region_a()[3].Read());
  EXPECT_EQ(0x11U, view.region_b()[0].Read());
  EXPECT_EQ(0x22U, view.region_b()[1].Read());
}

static const ::std::uint8_t kTwoRegionsAAndBOverlap[8] = {
    0x05,                    // 0:1  a_start
    0x02,                    // 1:2  a_size
    0x04,                    // 2:3  b_start
    0x08,                    // 3:4  b_end
    0x11, 0x22, 0x33, 0x44,  // 4:8  region_a / region_b
};

// With two dynamically-positioned regions, having the binary locations overlap
// works.
TEST(TwoRegionsView, RegionAAndBOverlappedWorks) {
  auto view =
      TwoRegionsView(kTwoRegionsAAndBOverlap, sizeof kTwoRegionsAAndBOverlap);
  EXPECT_EQ(8U, view.SizeInBytes());
  EXPECT_EQ(5U, view.a_start().Read());
  EXPECT_EQ(2U, view.a_size().Read());
  EXPECT_EQ(4U, view.b_start().Read());
  EXPECT_EQ(8U, view.b_end().Read());
  EXPECT_EQ(0x22U, view.region_a()[0].Read());
  EXPECT_EQ(0x33U, view.region_a()[1].Read());
  EXPECT_EQ(0x11U, view.region_b()[0].Read());
  EXPECT_EQ(0x22U, view.region_b()[1].Read());
  EXPECT_EQ(0x33U, view.region_b()[2].Read());
  EXPECT_EQ(0x44U, view.region_b()[3].Read());
}

TEST(TwoRegionsView, Write) {
  ::std::uint8_t buffer[64];
  auto writer = TwoRegionsWriter(buffer, sizeof buffer);
  writer.a_start().Write(4);
  writer.a_size().Write(2);
  writer.b_start().Write(6);
  writer.b_end().Write(10);
  writer.region_a()[0].Write(0x11);
  writer.region_a()[1].Write(0x22);
  writer.region_b()[0].Write(0x33);
  writer.region_b()[1].Write(0x44);
  writer.region_b()[2].Write(0x55);
  writer.region_b()[3].Write(0x66);
  EXPECT_EQ(
      ::std::vector</**/ ::std::uint8_t>(
          kTwoRegionsAFirst, kTwoRegionsAFirst + sizeof kTwoRegionsAFirst),
      ::std::vector</**/ ::std::uint8_t>(buffer,
                                         buffer + sizeof kTwoRegionsAFirst));

  writer.a_start().Write(10);
  writer.a_size().Write(4);
  writer.b_start().Write(4);
  writer.b_end().Write(6);
  writer.region_a()[0].Write(0x33);
  writer.region_a()[1].Write(0x44);
  writer.region_a()[2].Write(0x55);
  writer.region_a()[3].Write(0x66);
  writer.region_b()[0].Write(0x11);
  writer.region_b()[1].Write(0x22);
  // Set the unmapped region correctly.
  buffer[6] = 0xff;
  buffer[7] = 0xff;
  buffer[8] = 0xff;
  buffer[9] = 0xff;
  EXPECT_EQ(
      ::std::vector</**/ ::std::uint8_t>(
          kTwoRegionsBFirst, kTwoRegionsBFirst + sizeof kTwoRegionsBFirst),
      ::std::vector</**/ ::std::uint8_t>(buffer,
                                         buffer + sizeof kTwoRegionsBFirst));

  writer.a_start().Write(5);
  writer.a_size().Write(2);
  writer.b_start().Write(4);
  writer.b_end().Write(8);
  writer.region_b()[0].Write(0x11);
  writer.region_b()[1].Write(0xff);
  writer.region_b()[2].Write(0xee);
  writer.region_b()[3].Write(0x44);
  EXPECT_EQ(0xffU, writer.region_a()[0].Read());
  EXPECT_EQ(0xeeU, writer.region_a()[1].Read());
  writer.region_a()[0].Write(0x22);
  writer.region_a()[1].Write(0x33);
  EXPECT_EQ(0x22U, writer.region_b()[1].Read());
  EXPECT_EQ(0x33U, writer.region_b()[2].Read());
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(
                kTwoRegionsAAndBOverlap,
                kTwoRegionsAAndBOverlap + sizeof kTwoRegionsAAndBOverlap),
            ::std::vector</**/ ::std::uint8_t>(
                buffer, buffer + sizeof kTwoRegionsAAndBOverlap));
}

static const ::std::uint8_t kMultipliedSize[299] = {
    0x09,  // 0:1    width == 9
    0x21,  // 1:2    height == 33
    // 9 x 33 == 297-byte block for data.
    0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 2:11
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 11:20
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 20:29
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 29:38
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 38:47
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 47:56
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 56:65
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 65:74
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 74:83
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 83:92
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 92:101
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 101:110
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 110:119
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 119:128
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 128:137
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 137:146
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 146:155
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 155:164
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 164:173
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 173:182
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 182:191
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 191:200
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 200:209
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 209:218
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 218:227
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 227:236
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 236:245
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 245:254
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 254:263
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 263:272
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 272:281
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 281:290
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff,  // 290:299
};

// A structure with two 8-bit fields whose values are multiplied to get the
// length of an array works, even when the length of the array is too big to
// fit in 8 bits.
TEST(MultipliedSizeView, MultipliedSizesUseWideEnoughArithmetic) {
  auto view = MultipliedSizeView(kMultipliedSize, sizeof kMultipliedSize);
  EXPECT_EQ(299U, view.SizeInBytes());
  EXPECT_EQ(9U, view.width().Read());
  EXPECT_EQ(33U, view.height().Read());
  EXPECT_EQ(1U, view.data()[0].Read());
  EXPECT_EQ(0xffU, view.data()[296].Read());
}

static const ::std::uint8_t kNegativeTermsInSizesAMinusBIsBiggest[7] = {
    0x07,  // 0:1  a
    0x01,  // 1:2  b
    0x02,  // 2:3  c
    // 3:a-b   == 3:6  a_minus_b
    // 3:a-2*b == 3:5  a_minus_2b
    // 3:a-b-c == 3:4  a_minus_b_minus_c
    // 3:10-a  == 3:3  ten_minus_a
    // 3:a-2*c == 3:3  a_minus_2c
    // 3:a-c   == 3:5  a_minus_c
    0x11,
    0x22,
    0x33,
    0x44,
};

// Given a variety of potential sizes for a structure, the correct one is
// selected.
TEST(NegativeTermsInSizes, AMinusBIsBiggest) {
  auto view =
      NegativeTermsInSizesView(kNegativeTermsInSizesAMinusBIsBiggest,
                               sizeof kNegativeTermsInSizesAMinusBIsBiggest);
  EXPECT_EQ(6U, view.SizeInBytes());
  EXPECT_EQ(7U, view.a().Read());
  EXPECT_EQ(1U, view.b().Read());
  EXPECT_EQ(2U, view.c().Read());
  EXPECT_EQ(0x33U, view.a_minus_b()[2].Read());
}

static const ::std::uint8_t kNegativeTermsInSizesAMinusCIsBiggest[7] = {
    0x07,  // 0:1  a
    0x02,  // 1:2  b
    0x01,  // 2:3  c
    // 3:a-b   == 3:5  a_minus_b
    // 3:a-2*b == 3:3  a_minus_2b
    // 3:a-b-c == 3:4  a_minus_b_minus_c
    // 3:10-a  == 3:3  ten_minus_a
    // 3:a-2*c == 3:5  a_minus_2c
    // 3:a-c   == 3:6  a_minus_c
    0x11,
    0x22,
    0x33,
    0x44,
};

// Given a variety of potential sizes for a structure, the correct one is
// selected.
TEST(NegativeTermsInSizes, AMinusCIsBiggest) {
  auto view =
      NegativeTermsInSizesView(kNegativeTermsInSizesAMinusCIsBiggest,
                               sizeof kNegativeTermsInSizesAMinusCIsBiggest);
  EXPECT_EQ(6U, view.SizeInBytes());
  EXPECT_EQ(7U, view.a().Read());
  EXPECT_EQ(2U, view.b().Read());
  EXPECT_EQ(1U, view.c().Read());
  EXPECT_EQ(0x33U, view.a_minus_c()[2].Read());
  EXPECT_TRUE(view.a_minus_b().IsComplete());
  EXPECT_TRUE(view.a_minus_2b().IsComplete());
}

static const ::std::uint8_t kNegativeTermsInSizesTenMinusAIsBiggest[7] = {
    0x04,  // 0:1  a
    0x00,  // 1:2  b
    0x00,  // 2:3  c
    // 3:a-b   == 3:4  a_minus_b
    // 3:a-2*b == 3:4  a_minus_2b
    // 3:a-b-c == 3:4  a_minus_b_minus_c
    // 3:10-a  == 3:6  ten_minus_a
    // 3:a-2*c == 3:4  a_minus_2c
    // 3:a-c   == 3:4  a_minus_c
    0x11,
    0x22,
    0x33,
    0x44,
};

// Given a variety of potential sizes for a structure, the correct one is
// selected.
TEST(NegativeTermsInSizes, TenMinusAIsBiggest) {
  auto view =
      NegativeTermsInSizesView(kNegativeTermsInSizesTenMinusAIsBiggest,
                               sizeof kNegativeTermsInSizesTenMinusAIsBiggest);
  EXPECT_EQ(6U, view.SizeInBytes());
  EXPECT_EQ(4U, view.a().Read());
  EXPECT_EQ(0U, view.b().Read());
  EXPECT_EQ(0U, view.c().Read());
  EXPECT_EQ(0x33U, view.ten_minus_a()[2].Read());
  EXPECT_TRUE(view.a_minus_b().IsComplete());
  EXPECT_TRUE(view.a_minus_2b().IsComplete());
}

static const ::std::uint8_t kNegativeTermsEndWouldBeNegative[10] = {
    0x00,  // 0:1  a
    0x02,  // 1:2  b
    0x02,  // 2:3  c
    // 3:a-b   == 3:-2  a_minus_b
    // 3:a-2*b == 3:-4  a_minus_2b
    // 3:a-b-c == 3:-4  a_minus_b_minus_c
    // 3:10-a  == 3:10  ten_minus_a
    // 3:a-2*c == 3:-4  a_minus_2c
    // 3:a-c   == 3:-2  a_minus_c
    0x11,
    0x22,
    0x33,
    0x44,
    0x55,
    0x66,
    0x77,
};

// Given a variety of potential sizes for a structure, some of which would be
// negative, the correct one is selected.
TEST(NegativeTermsInSizes, NegativeEnd) {
  auto view = NegativeTermsInSizesView(kNegativeTermsEndWouldBeNegative,
                                       sizeof kNegativeTermsEndWouldBeNegative);
  EXPECT_EQ(10U, view.SizeInBytes());
  EXPECT_TRUE(view.SizeIsKnown());
  EXPECT_EQ(0U, view.a().Read());
  EXPECT_EQ(2U, view.b().Read());
  EXPECT_EQ(2U, view.c().Read());
  EXPECT_EQ(0x77U, view.ten_minus_a()[6].Read());
  EXPECT_FALSE(view.a_minus_b().IsComplete());
  EXPECT_FALSE(view.a_minus_2b().IsComplete());
}

// If a field's offset is negative, the field is not Ok() and !IsComplete().
TEST(NegativeTermInLocation, NegativeLocation) {
  ::std::array<char, 256> bytes = {15};
  auto view = MakeNegativeTermInLocationView(&bytes);
  EXPECT_FALSE(view.Ok());
  EXPECT_TRUE(view.a().Ok());
  EXPECT_TRUE(view.IsComplete());
  EXPECT_FALSE(view.b().IsComplete());
  EXPECT_FALSE(view.b().Ok());
}

static const ::std::uint8_t kChainedSizeInOrder[4] = {
    0x01,  // 0:1  a
    0x02,  // 1:2  b
    0x03,  // 2:3  c
    0x04,  // 3:4  d
};

// Fields are readable, even through multiple levels of indirection.
TEST(ChainedSize, ChainedSizeInOrder) {
  auto view = ChainedSizeView(kChainedSizeInOrder, sizeof kChainedSizeInOrder);
  ASSERT_TRUE(view.SizeIsKnown());
  EXPECT_EQ(4U, view.SizeInBytes());
  ASSERT_TRUE(view.a().IsComplete());
  EXPECT_EQ(1U, view.a().Read());
  ASSERT_TRUE(view.b().IsComplete());
  EXPECT_EQ(2U, view.b().Read());
  ASSERT_TRUE(view.c().IsComplete());
  EXPECT_EQ(3U, view.c().Read());
  ASSERT_TRUE(view.d().IsComplete());
  EXPECT_EQ(4U, view.d().Read());
}

static const ::std::uint8_t kChainedSizeNotInOrder[4] = {
    0x03,  // 0:1  a
    0x04,  // 1:2  d
    0x01,  // 2:3  c
    0x02,  // 3:4  b
};

// Fields are readable, even through multiple levels of indirection, when their
// placement in the binary structure is not in the same order.
TEST(ChainedSize, ChainedSizeNotInOrder) {
  auto view =
      ChainedSizeView(kChainedSizeNotInOrder, sizeof kChainedSizeNotInOrder);
  ASSERT_TRUE(view.Ok());
  ASSERT_TRUE(view.SizeIsKnown());
  EXPECT_EQ(4U, view.SizeInBytes());
  ASSERT_TRUE(view.a().IsComplete());
  EXPECT_EQ(3U, view.a().Read());
  ASSERT_TRUE(view.b().IsComplete());
  EXPECT_EQ(2U, view.b().Read());
  ASSERT_TRUE(view.c().IsComplete());
  EXPECT_EQ(1U, view.c().Read());
  ASSERT_TRUE(view.d().IsComplete());
  EXPECT_EQ(4U, view.d().Read());
}

// Fields are readable, even through multiple levels of indirection.
TEST(ChainedSize, Write) {
  ::std::uint8_t buffer[4] = {0};
  auto writer = ChainedSizeWriter(buffer, sizeof buffer);
  writer.a().Write(1);
  writer.b().Write(2);
  writer.c().Write(3);
  writer.d().Write(4);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(
                kChainedSizeInOrder,
                kChainedSizeInOrder + sizeof kChainedSizeInOrder),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
  writer.a().Write(3);
  writer.b().Write(2);
  writer.c().Write(1);
  writer.d().Write(4);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(
                kChainedSizeNotInOrder,
                kChainedSizeNotInOrder + sizeof kChainedSizeNotInOrder),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

static const ::std::uint8_t kChainedSizeTooShortForD[3] = {
    0x01,  // 0:1  a
    0x02,  // 1:2  b
    0x03,  // 2:3  c
           // d is missing
};

// When a structure is partial, fields whose locations are available are still
// readable, and the SizeInBytes method can be called as long as all of the
// fields required to calculate the size are readable, even if other fields are
// not.
TEST(ChainedSize, ChainedSizeTooShortForD) {
  auto view = ChainedSizeView(kChainedSizeTooShortForD,
                              sizeof kChainedSizeTooShortForD);
  ASSERT_FALSE(view.Ok());
  ASSERT_TRUE(view.SizeIsKnown());
  EXPECT_EQ(4U, view.SizeInBytes());
  ASSERT_TRUE(view.a().IsComplete());
  EXPECT_EQ(1U, view.a().Read());
  ASSERT_TRUE(view.b().IsComplete());
  EXPECT_EQ(2U, view.b().Read());
  ASSERT_TRUE(view.c().IsComplete());
  EXPECT_EQ(3U, view.c().Read());
  ASSERT_FALSE(view.d().IsComplete());
}

static const ::std::uint8_t kChainedSizeTooShortForC[2] = {
    0x01,  // 0:1  a
    0x02,  // 1:2  b
           // c is missing
           // d is missing
};

// When not all fields required to compute SizeInBytes() can be read,
// SizeIsKnown() returns false.
TEST(ChainedSize, ChainedSizeTooShortForC) {
  auto view = ChainedSizeView(kChainedSizeTooShortForC,
                              sizeof kChainedSizeTooShortForC);
  ASSERT_FALSE(view.Ok());
  EXPECT_FALSE(view.SizeIsKnown());
  ASSERT_TRUE(view.a().IsComplete());
  EXPECT_EQ(1U, view.a().Read());
  ASSERT_TRUE(view.b().IsComplete());
  EXPECT_EQ(2U, view.b().Read());
  ASSERT_FALSE(view.c().IsComplete());
  ASSERT_FALSE(view.d().IsComplete());
}

// A structure with static size and two end-aligned fields compiles and returns
// the correct size.
TEST(FinalFieldOverlaps, FinalSizeIsCorrect) {
  ASSERT_EQ(5U, FinalFieldOverlapsView::SizeInBytes());
}

static const ::std::uint8_t kDynamicFinalFieldOverlapsDynamicFieldIsLast[12] = {
    0x0a,                                            // 0:1  a
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 1:9 padding
    0x01,                                            // 9:10  b
    0x02,  // 10:11 (a:a+1)  low byte of c
    0x03,  // 11:12 (a+1:a+2)  d; high byte of c
};

static const ::std::uint8_t kDynamicFinalFieldOverlapsStaticFieldIsLast[10] = {
    0x07,                                // 0:1  a
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 1:7 padding
    0x02,                                // 7:8 (a:a+1)  low byte of c
    0x03,                                // 8:9 (a+1:a+2)  d; high byte of c
    0x01,                                // 9:10  b
};

// A structure with dynamic size and two end-aligned fields compiles and returns
// the correct size.
TEST(DynamicFinalFieldOverlaps, FinalSizeIsCorrect) {
  auto dynamic_last_view = DynamicFinalFieldOverlapsView(
      kDynamicFinalFieldOverlapsDynamicFieldIsLast,
      sizeof kDynamicFinalFieldOverlapsDynamicFieldIsLast);
  ASSERT_EQ(12U, dynamic_last_view.SizeInBytes());
  auto static_last_view = DynamicFinalFieldOverlapsView(
      kDynamicFinalFieldOverlapsStaticFieldIsLast,
      sizeof kDynamicFinalFieldOverlapsStaticFieldIsLast);
  ASSERT_EQ(10U, static_last_view.SizeInBytes());
}

TEST(DynamicFieldDependsOnLaterField, DynamicLocationIsNotKnown) {
  ::std::uint8_t bytes[5] = {0x04, 0x03, 0x02, 0x01, 0x00};
  auto view = MakeDynamicFieldDependsOnLaterFieldView(bytes, 4);
  EXPECT_FALSE(view.b().Ok());
  view = MakeDynamicFieldDependsOnLaterFieldView(bytes, 5);
  EXPECT_TRUE(view.b().Ok());
  EXPECT_EQ(3U, view.b().Read());
}

TEST(DynamicFieldDoesNotAffectSize, DynamicFieldDoesNotAffectSize) {
  EXPECT_EQ(256U, DynamicFieldDoesNotAffectSizeView::SizeInBytes());
}

}  // namespace
}  // namespace test
}  // namespace emboss
