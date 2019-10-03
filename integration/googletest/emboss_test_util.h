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

#ifndef EMBOSS_PUBLIC_EMBOSS_TEST_UTIL_H_
#define EMBOSS_PUBLIC_EMBOSS_TEST_UTIL_H_

#include <cctype>
#include <iterator>
#include <ostream>
#include <string>

#include "absl/memory/memory.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "runtime/cpp/emboss_text_util.h"

namespace emboss {

class EmbMatcher {
 public:
  template <typename ViewType>
  explicit EmbMatcher(ViewType compare_to)
      : compare_to_ok_(compare_to.Ok()),
        compare_to_lines_(SplitToLines(
            compare_to_ok_ ? WriteToString(compare_to, MultilineText()) : "")) {
  }

  template <typename ViewType>
  bool MatchAndExplain(ViewType compare_from,
                       ::testing::MatchResultListener* listener) const {
    if (!compare_to_ok_) {
      *listener << "View for comparison to is not OK.";
      return false;
    }

    if (!compare_from.Ok()) {
      *listener << "View for comparison from is not OK.";
      return false;
    }

    const auto compare_from_lines =
        SplitToLines(WriteToString(compare_from, MultilineText()));
    if (compare_from_lines != compare_to_lines_) {
      *listener << "\n"
                << ::testing::internal::edit_distance::CreateUnifiedDiff(
                       compare_to_lines_, compare_from_lines);
      return false;
    }

    return true;
  }

  // Describes the property of a value matching this matcher.
  void DescribeTo(::std::ostream* os) const { *os << "are equal"; }

  // Describes the property of a value NOT matching this matcher.
  void DescribeNegationTo(::std::ostream* os) const { *os << "are NOT equal"; }

 private:
  // Splits the given string on '\n' boundaries and returns a vector of those
  // strings.
  ::std::vector</**/ ::std::string> SplitToLines(
      const ::std::string& input) const {
    constexpr char kNewLine = '\n';

    ::std::stringstream ss(input);
    ss.ignore(::std::numeric_limits</**/ ::std::streamsize>::max(), kNewLine);

    ::std::vector</**/ ::std::string> lines;
    for (::std::string line; ::std::getline(ss, line, kNewLine);) {
      lines.push_back(::std::move(line));
    }
    return lines;
  }

  const bool compare_to_ok_;
  const ::std::vector</**/ ::std::string> compare_to_lines_;
};

template <typename ViewType>
::testing::PolymorphicMatcher<EmbMatcher> EqualsEmb(ViewType view) {
  return ::testing::MakePolymorphicMatcher(EmbMatcher(view));
}

}  // namespace emboss

#endif  // EMBOSS_PUBLIC_EMBOSS_TEST_UTIL_H_
