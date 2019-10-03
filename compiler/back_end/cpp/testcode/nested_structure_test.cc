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

// Tests for the generated View class for Container and Box from
// nested_structure.emb.
//
// These tests check that nested structures work.
#include <stdint.h>

#include <vector>

#include "gtest/gtest.h"
#include "testdata/nested_structure.emb.h"

namespace emboss {
namespace test {
namespace {

alignas(8) static const ::std::uint8_t kContainer[20] = {
    0x28, 0x00, 0x00, 0x00,  // 0:4    weight == 40
    0x78, 0x56, 0x34, 0x12,  // 4:8    important_box.id == 0x12345678
    0x03, 0x02, 0x01, 0x00,  // 8:12   important_box.count == 0x010203
    0x21, 0x43, 0x65, 0x87,  // 12:16  other_box.id == 0x87654321
    0xcc, 0xbb, 0xaa, 0x00,  // 16:20  other_box.count == 0xaabbcc
};

// ContainerView::SizeInBytes() returns the expected value.
TEST(ContainerView, StaticSizeIsCorrect) {
  EXPECT_EQ(20U, ContainerView::SizeInBytes());
}

// ContainerView::SizeInBytes() returns the expected value.
TEST(ContainerView, SizeFieldIsCorrect) {
  auto view = MakeAlignedContainerView<const ::std::uint8_t, 8>(
      kContainer, sizeof kContainer);
  EXPECT_EQ(40U, view.weight().Read());
}

// ContainerView::important_box() returns a BoxView, and not a different
// template instantiation.
TEST(ContainerView, FieldTypesAreExpected) {
  auto container = MakeAlignedContainerView<const ::std::uint8_t, 8>(
      kContainer, sizeof kContainer);
  auto box = container.important_box();
  EXPECT_EQ(0x12345678U, box.id().Read());
}

// Box::SizeInBytes() returns the expected value, when retrieved from a
// Container.
TEST(ContainerView, BoxSizeFieldIsCorrect) {
  auto view = MakeAlignedContainerView<const ::std::uint8_t, 8>(
      kContainer, sizeof kContainer);
  EXPECT_EQ(8U, view.important_box().SizeInBytes());
}

// Box::id() and Box::count() return correct values when retrieved from
// Container.
TEST(ContainerView, BoxFieldValuesAreCorrect) {
  auto view = MakeAlignedContainerView<const ::std::uint8_t, 8>(
      kContainer, sizeof kContainer);
  EXPECT_EQ(0x12345678U, view.important_box().id().Read());
  EXPECT_EQ(0x010203U, view.important_box().count().Read());
  EXPECT_EQ(0x87654321U, view.other_box().id().Read());
  EXPECT_EQ(0xaabbccU, view.other_box().count().Read());
}

TEST(ContainerView, CanWriteValues) {
  alignas(8)::std::uint8_t buffer[sizeof kContainer];
  auto writer =
      MakeAlignedContainerView</**/ ::std::uint8_t, 8>(buffer, sizeof buffer);
  writer.weight().Write(40);
  writer.important_box().id().Write(0x12345678);
  writer.important_box().count().Write(0x010203);
  writer.other_box().id().Write(0x87654321);
  writer.other_box().count().Write(0xaabbcc);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kContainer,
                                               kContainer + sizeof kContainer),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(ContainerView, CanReadTextFormat) {
  alignas(8)::std::uint8_t buffer[sizeof kContainer];
  auto writer =
      MakeAlignedContainerView</**/ ::std::uint8_t, 8>(buffer, sizeof buffer);
  EXPECT_TRUE(::emboss::UpdateFromText(writer, R"(
    {
      weight: 40
      important_box: {
        id: 0x12345678
        count: 0x010203
      }
      other_box: {
        id: 0x87654321
        count: 0xaabbcc
      }
    }
  )"));
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kContainer,
                                               kContainer + sizeof kContainer),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

alignas(8) static const ::std::uint8_t kTruck[44] = {
    0x88, 0x66, 0x44, 0x22,  // 0:4    id == 0x22446688
    0x64, 0x00, 0x00, 0x00,  // 4:8    cargo[0].weight == 100
    0xff, 0x00, 0x00, 0x00,  // 8:12   cargo[0].important_box.id == 255
    0x0a, 0x00, 0x00, 0x00,  // 12:16  cargo[0].important_box.count == 10
    0x00, 0x94, 0x35, 0x77,  // 16:20  cargo[0].other_box.id == 2000000000
    0xf4, 0x01, 0x00, 0x00,  // 20:24  cargo[0].other_box.count == 500
    0x65, 0x00, 0x00, 0x00,  // 24:28  cargo[1].weight == 101
    0xfe, 0x00, 0x00, 0x00,  // 28:32  cargo[1].important_box.id == 254
    0x09, 0x00, 0x00, 0x00,  // 32:36  cargo[1].important_box.count == 9
    0x01, 0x94, 0x35, 0x77,  // 36:40  cargo[1].other_box.id == 2000000001
    0xf3, 0x01, 0x00, 0x00,  // 40:44  cargo[1].other_box.count == 499
};

TEST(TruckView, ValuesAreCorrect) {
  auto view =
      MakeAlignedTruckView<const ::std::uint8_t, 8>(kTruck, sizeof kTruck);
  EXPECT_EQ(0x22446688U, view.id().Read());
  EXPECT_EQ(100U, view.cargo()[0].weight().Read());
  EXPECT_EQ(255U, view.cargo()[0].important_box().id().Read());
  EXPECT_EQ(10U, view.cargo()[0].important_box().count().Read());
  EXPECT_EQ(2000000000U, view.cargo()[0].other_box().id().Read());
  EXPECT_EQ(500U, view.cargo()[0].other_box().count().Read());
  EXPECT_EQ(101U, view.cargo()[1].weight().Read());
  EXPECT_EQ(254U, view.cargo()[1].important_box().id().Read());
  EXPECT_EQ(9U, view.cargo()[1].important_box().count().Read());
  EXPECT_EQ(2000000001U, view.cargo()[1].other_box().id().Read());
  EXPECT_EQ(499U, view.cargo()[1].other_box().count().Read());
}

TEST(TruckView, WriteValues) {
  ::std::uint8_t buffer[sizeof kTruck];
  auto writer = TruckWriter(buffer, sizeof buffer);
  writer.id().Write(0x22446688);
  writer.cargo()[0].weight().Write(100);
  writer.cargo()[0].important_box().id().Write(255);
  writer.cargo()[0].important_box().count().Write(10);
  writer.cargo()[0].other_box().id().Write(2000000000);
  writer.cargo()[0].other_box().count().Write(500);
  writer.cargo()[1].weight().Write(101);
  writer.cargo()[1].important_box().id().Write(254);
  writer.cargo()[1].important_box().count().Write(9);
  writer.cargo()[1].other_box().id().Write(2000000001);
  writer.cargo()[1].other_box().count().Write(499);
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kTruck, kTruck + sizeof kTruck),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

TEST(TruckView, CanReadTextFormat) {
  ::std::uint8_t buffer[sizeof kTruck];
  auto writer = TruckWriter(buffer, sizeof buffer);
  EXPECT_TRUE(::emboss::UpdateFromText(writer, R"(
    {
      id: 0x22446688
      cargo: {
        {
          weight: 100
          important_box: {
            id: 255
            count: 10
          }
          other_box: {
            id: 2_000_000_000
            count: 500
          }
        },
        {
          weight: 101
          important_box: {
            id: 254
            count: 9
          }
          other_box: {
            id: 2_000_000_001
            count: 499
          }
        },
      }
    }
  )"));
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(kTruck, kTruck + sizeof kTruck),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

}  // namespace
}  // namespace test
}  // namespace emboss
