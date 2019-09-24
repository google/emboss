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

// Tests for the generated View class for a LogFileStatus from
// span_se_log_file_status.emb.
#include <stdint.h>

#include <vector>

#include "gtest/gtest.h"
#include "testdata/golden/span_se_log_file_status.emb.h"

namespace emboss {
namespace test {
namespace {

// A simple, static LogFileStatus.  There are technically no invalid
// LogFileStatuses as long as there are at least 24 bytes to read.
static const ::std::uint8_t kLogFileStatus[24] = {
    0x01, 0x02, 0x03, 0x04,  // 0:4    UInt        file_state
    'A',  'B',  'C',  'D',   // 4:16   UInt:8[12]  file_name
    'E',  'F',  'G',  'H',   // 4:16   UInt:8[12]  file_name
    'I',  'J',  'K',  'L',   // 4:16   UInt:8[12]  file_name
    0x05, 0x06, 0x07, 0x08,  // 16:20  UInt        file_size_kb
    0x09, 0x0a, 0x0b, 0x0c,  // 20:24  UInt        media
};

// LogFileStatusView constructor compiles and runs without crashing.
TEST(LogFileStatusView, ConstructorRuns) {
  LogFileStatusView(kLogFileStatus, sizeof kLogFileStatus);
}

// LogFileStatusView::SizeInBytes() returns the expected value.
TEST(LogFileStatusView, SizeIsCorrect) {
  EXPECT_EQ(24U, LogFileStatusView::SizeInBytes());
}

// LogFileStatusView's atomic field accessors work.
TEST(LogFileStatusView, AtomicFieldAccessorsWork) {
  auto view = LogFileStatusView(kLogFileStatus, sizeof kLogFileStatus);
  EXPECT_EQ(0x04030201U, view.file_state().Read());
  EXPECT_EQ(0x08070605U, view.file_size_kb().Read());
  EXPECT_EQ(0x0c0b0a09U, view.media().Read());
}

// LogFileStatusView's array field accessor works.
TEST(LogFileStatusView, ArrayFieldAccessor) {
  auto view = LogFileStatusView(kLogFileStatus, sizeof kLogFileStatus);
  EXPECT_EQ('A', view.file_name()[0].Read());
  EXPECT_EQ('L', view.file_name()[11].Read());
}

// The "Ok()" method works.
TEST(LogFileStatusView, Ok) {
  auto view = LogFileStatusView(kLogFileStatus, sizeof kLogFileStatus);
  EXPECT_TRUE(view.Ok());
  view = LogFileStatusView(kLogFileStatus, sizeof kLogFileStatus - 1);
  EXPECT_FALSE(view.Ok());
  ::std::vector</**/ ::std::uint8_t> bigger_than_necessary(
      sizeof kLogFileStatus + 1);
  view = LogFileStatusView(&bigger_than_necessary[0],
                           bigger_than_necessary.size());
  EXPECT_TRUE(view.Ok());
}

TEST(LogFileStatusView, Writing) {
  ::std::uint8_t buffer[sizeof kLogFileStatus] = {0};
  auto writer = LogFileStatusWriter(buffer, sizeof buffer);
  writer.file_state().Write(0x04030201);
  writer.file_size_kb().Write(0x08070605);
  writer.media().Write(0x0c0b0a09);
  // TODO(bolms): Add a Count method, that returns the element count instead of
  // the byte count.  (Not a problem here, since file_name's elements are each
  // one byte anyway.)
  for (::std::size_t i = 0; i < writer.file_name().SizeInBytes(); ++i) {
    writer.file_name()[i].Write('A' + i);
  }
  EXPECT_EQ(::std::vector</**/ ::std::uint8_t>(
                kLogFileStatus, kLogFileStatus + sizeof kLogFileStatus),
            ::std::vector</**/ ::std::uint8_t>(buffer, buffer + sizeof buffer));
}

}  // namespace
}  // namespace test
}  // namespace emboss
